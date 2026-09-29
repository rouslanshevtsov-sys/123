#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Единая точка правды управляющего навыка vk-competitor-orchestrator.

Здесь живут ТОЛЬКО служебные данные маршрутизации и примитивы:
  - реестр навыков, этапов, артефактов и порогов (gate) цепочки;
  - детерминированный разбор запроса пользователя на намерение (intent);
  - расчёт хэшей, уникальные каталоги запусков, поиск переиспользуемых результатов;
  - schemaVersion контракта цепочки.

ПРЕДМЕТНАЯ логика этапов (интервью, поиск VK, сбор постов, ER, медиа, отчёт)
принадлежит навыкам из .agents/skills и сюда НЕ дублируется:
для проверки результата этапа orchestrator вызывает нативные валидаторы навыка
(см. STAGES[stage]["gate"]), а не пересчитывает их правила.

Абсолютных путей запуска и секретов в файлах навыка нет (см. detect_secrets.py).
"""

import hashlib
import json
import os
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

SCHEMA_VERSION = "1.0"
CHAIN_CONTRACT_VERSION = "1.2"  # см. ../business-context-interview/references/chain-contract.md

MSK = timezone(timedelta(hours=3))  # Europe/Moscow — единый часовой пояс цепочки

SKILLS_DIRNAME = ".agents/skills"
RUNS_DIRNAME = "runs"
ROUTING_POLICY_RELPATH = "references/routing-policy.json"

# ------------------- Этапы и навыки -------------------

STAGES = {
    "interview": {
        "skill": "business-context-interview",
        "inputs": [],
        "outputs": ["business_context.json", "business_card.md", "provenance.json"],
        # gate: относительный путь скрипта ВНУТРИ навыка + шаблон аргументов.
        # Пустой args — вызов без аргументов из корня запуска (cwd=run_dir).
        "gate": {"script": "scripts/final_validation.py", "args": []},
        "trigger": "auto_when_gate_fails",   # отсутствует/бит/draft -> интервью
        "explicit_only": False,
    },
    "competitors": {
        "skill": "search-vk-competitors",
        "inputs": ["business_context.json"],
        "outputs": ["competitor_set.json", "competitor_analysis.xlsx", "run_manifest.json"],
        "gate": {"script": "scripts/verify_results.py",
                 "args": ["--context", "{run}/business_context.json",
                          "--competitor-set", "{set}", "--excel", "{excel}",
                          "--posts", "{run}/posts_er.json"]},
        "trigger": "explicit_request_only",  # только прямая просьба пользователя
        "explicit_only": True,
    },
    "posts": {
        "skill": "analyze-vk-best-posts",
        "inputs": ["competitor_set.json"],
        "outputs": ["vk_posts_dataset.json", "comments_replies.json",
                    "competitors_vk_report.xlsx", "media_summary_anonymized.json"],
        "gate": {"script": "scripts/media_gate.py", "args": ["--workdir", "{run}"]},
        "trigger": "auto_for_weekly_report",
        "explicit_only": False,
    },
    "report": {
        "skill": "vk-content-report",
        "inputs": ["vk_posts_dataset.json", "comments.json",
                   "competitors_vk_report.xlsx", "provenance.json"],
        "outputs": ["report.html"],
        "gate": {"script": "scripts/validate_report.py", "args": ["--workdir", "{run}"]},
        "trigger": "auto_after_posts",
        "explicit_only": False,
    },
}

STAGE_ORDER = ["interview", "competitors", "posts", "report"]

# Навыки, которым разрешено существовать в .agents/skills (белый список цепочки).
ALLOWED_SKILLS = [STAGES[s]["skill"] for s in STAGE_ORDER] + ["vk-competitor-orchestrator"]

# Компактные служебные JSON управляющего агента (не предметные артефакты этапов).
HANDOFF_NAME = "handoff.json"            # что передаём следующему этапу: пути+хэши+статусы
STAGE_STATUS_NAME = "stage_status.json"  # результаты gate-проверок по этапам

# Имена артефактов, которые orchestrator ожидает в root/run-директории этапа.
ARTIFACT_BY_KEY = {
    "context": "business_context.json",
    "card": "business_card.md",
    "provenance": "provenance.json",
    "competitors": "competitor_set.json",
    "competitors_excel": "competitor_analysis.xlsx",
    "posts_dataset": "vk_posts_dataset.json",
    "posts_comments_raw": "comments_replies.json",
    "posts_comments": "comments.json",      # канон для этапа report
    "posts_xlsx": "competitors_vk_report.xlsx",
    "report_html": "report.html",
}


class OrchestratorError(Exception):
    """Остановка цепочки с конкретной причиной (условие выхода)."""


def norm_token(s):
    return str(s or "").lower().replace("ё", "е")


# ------------------- Хэши -------------------

def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return "sha256:" + h.hexdigest()


def input_hashes(paths):
    """{имя_файла: sha256} для списка путей; отсутствующий файл — 'missing'."""
    out = {}
    for p in paths:
        p = Path(p)
        out[p.name] = sha256_file(p) if p.exists() and p.is_file() else "missing"
    return out


# ------------------- Намерение пользователя (детерминированно) -------------------

_INTENT_PATTERNS = [
    ("weekly_report", r"недел\w+.{0,12}(отчет|отchet|report)|отчет.{0,12}за\s*недел|weekly"),
    ("update_competitors", r"(обновить|переискать|пересобрать)[^.]?(конкурент)|"
                           r"(конкурент\w*)[^.]?(обновить|переискать)"),
    ("search_competitors", r"(найти|искать|ищи|проверить|подобрать)[^.]{0,30}конкурент|"
                           r"конкурент\w*[^.]{0,30}(найти|искать|проверить)|competitor"),
    ("analyze_posts", r"(лучшие|топ\w*)[^.]{0,20}(пост|публич)|"
                      r"(пост\w*|публич)[^.]{0,20}(\ber\b|анализ)|анализ[^.]{0,20}публич"),
    ("market_reactions", r"(реакци|комментарии|выводы)[^.]{0,25}(рынк|пост|аудитор)|"
                         r"отчет[^.]{0,20}(по публикациям|реакци)|market"),
    ("refresh_context", r"(обновить|пересобрать|переписать)[^.]{0,20}(бизнес[- ]?контекст|карточк|контекст)|"
                        r"(контекст|карточк)\w*[^.]{0,20}обновить"),
]


def classify_intent(text):
    """Возвращает намерение по первому совпадению; default — unknown."""
    t = norm_token(text)
    for name, pat in _INTENT_PATTERNS:
        if re.search(pat, t):
            return name
    return "unknown"


# ------------------- Маршрутизация (чистая функция) -------------------

def workspace_root(start=None):
    d = Path(start or Path(__file__).resolve()).parent
    while True:
        if (d / SKILLS_DIRNAME).is_dir():
            return d
        if d.parent == d:
            return Path(start or Path.cwd()).resolve()
        d = d.parent


def context_gate(root):
    """Проверяет бизнес-контекст. Возвращает (ok, reason). Порог — как у downstream-этапов:
    файл есть, читается, status=confirmed. Интервью не проводится повторно, если ok=True."""
    ctx_path = Path(root) / ARTIFACT_BY_KEY["context"]
    if not ctx_path.exists():
        return False, "business_context.json отсутствует"
    try:
        data = json.loads(ctx_path.read_text(encoding="utf-8"))
    except (ValueError, OSError) as e:
        return False, "business_context.json повреждён: %s" % type(e).__name__
    if data.get("status") != "confirmed":
        return False, 'business_context.json имеет статус "%s", требуется confirmed' % data.get("status")
    return True, "подтверждённый контекст готов"


def find_latest_valid(root, stage, current_inputs_hash):
    """Ищет последний валидный результат этапа с теми же хэшами входов.
    Валидность = запись runs/index.json со status=pass + артефакты существуют и непусты +
    сохранённые хэши входов совпали с текущими. Возвращает run_id или None."""
    idx = Path(root) / RUNS_DIRNAME / "index.json"
    if not idx.exists():
        return None
    try:
        entries = json.loads(idx.read_text(encoding="utf-8")).get("runs", [])
    except (ValueError, OSError):
        return None
    for e in sorted(entries, key=lambda x: x.get("createdAt", ""), reverse=True):
        if e.get("stage") != stage or e.get("status") != "pass":
            continue
        rd = Path(root) / RUNS_DIRNAME / e["date"] / e["runId"]
        if not rd.is_dir():
            continue
        if e.get("inputHashes") != current_inputs_hash:
            continue
        for a in e.get("artifacts", []):
            ap = rd / a
            if not ap.exists() or ap.stat().st_size == 0:
                break
        else:
            return e["runId"]
    return None


def route(intent, root, period_hours=7 * 24):
    """Главное решение управляющего агента: какие этапы нужны и можно ли стартовать.
    Возвращает dict-план (compact JSON для handoff). Никаких сетевых действий здесь нет."""
    root = Path(root)
    ctx_ok, ctx_reason = context_gate(root)
    plan = {
        "schemaVersion": SCHEMA_VERSION,
        "intent": intent,
        "periodHours": period_hours,
        "contextReady": ctx_ok,
        "contextReason": ctx_reason,
        "stages": [],          # [{stage, skill, action, reason}]
        "stop": None,          # причина остановки или None
        "reuse": {},           # stage -> run_id переиспользованного результата
    }

    def add(stage, action, reason):
        plan["stages"].append({"stage": stage, "skill": STAGES[stage]["skill"],
                               "action": action, "reason": reason})

    if intent == "unknown":
        plan["stop"] = "Намерение не распознано; уточните запрос (интервью/поиск/анализ/отчёт)."
        return plan

    if intent == "refresh_context":
        add("interview", "run", "прямая просьба обновить бизнес-контекст")
        return plan

    if intent in ("search_competitors", "update_competitors"):
        if not ctx_ok:
            add("interview", "run", ctx_reason)
        add("competitors", "run", "прямая просьба пользователя о конкурентах")
        return plan

    if intent == "analyze_posts":
        comp = root / ARTIFACT_BY_KEY["competitors"]
        if not ctx_ok:
            add("interview", "run", ctx_reason)
        if comp.exists():
            add("posts", "run", "анализ публикаций по существующему competitor_set.json")
        else:
            plan["stop"] = ("Отсутствует competitor_set.json. Поиск конкурентов запускается "
                            "только по отдельному разрешению пользователя.")
            add("competitors", "blocked-needs-explicit-permission",
                "нет валидного competitor_set.json")
        return plan

    if intent == "weekly_report":
        comp = root / ARTIFACT_BY_KEY["competitors"]
        if not ctx_ok:
            add("interview", "run", ctx_reason)
        if not comp.exists():
            plan["stop"] = ("Для недельного отчёта нет competitor_set.json. Поиск конкурентов "
                            "НЕ запускается автоматически — требуется отдельное разрешение.")
            add("competitors", "blocked-needs-explicit-permission",
                "просьба о недельном отчёте не является разрешением на поиск")
            return plan
        ih = input_hashes([comp])
        reuse = find_latest_valid(root, "posts", ih)
        if reuse:
            plan["reuse"]["posts"] = reuse
            add("posts", "reuse", "входы не изменились, найден валидный результат %s" % reuse)
        else:
            add("posts", "run", "новый анализ публикаций за %d ч" % period_hours)
        add("report", "run", "итоговый отчёт после успешного медиашлюза этапа posts")
        return plan

    if intent == "market_reactions":
        ds = root / ARTIFACT_BY_KEY["posts_dataset"]
        if ds.exists():
            add("report", "run", "отчёт по готовым результатам анализа")
        else:
            plan["stop"] = "Нет результатов analyze-vk-best-posts; сначала выполните этот этап."
            add("posts", "blocked-missing-input", "отсутствует vk_posts_dataset.json")
        return plan

    plan["stop"] = "Неизвестное намерение '%s'" % intent
    return plan


# ------------------- Каталоги запусков -------------------

def new_run_dir(root, stage, now=None):
    """Создаёт уникальный каталог runs/YYYY-MM-DD/<run-id>/; никогда не перезаписывает."""
    root = Path(root)
    now = now or datetime.now(MSK)
    date = now.strftime("%Y-%m-%d")
    stamp = now.strftime("%H%M%S")
    base = root / RUNS_DIRNAME / date
    base.mkdir(parents=True, exist_ok=True)
    run_id = "%s-%s-%s" % (stamp, stage, os.urandom(3).hex())
    rd = base / run_id
    if rd.exists():
        raise OrchestratorError("Каталог запуска уже существует: %s" % rd)
    rd.mkdir()
    return rd, run_id, date


def write_index_entry(root, entry):
    """Добавляет запись о запуске в runs/index.json (append-only, без перезаписи чужих)."""
    root = Path(root)
    idx = root / RUNS_DIRNAME / "index.json"
    data = {"schemaVersion": SCHEMA_VERSION, "runs": []}
    if idx.exists():
        try:
            old = json.loads(idx.read_text(encoding="utf-8"))
            if isinstance(old, dict) and isinstance(old.get("runs"), list):
                data["runs"] = old["runs"]
        except (ValueError, OSError):
            pass  # повреждённый индекс не блокирует новый запуск, но пересоздаётся
    if any(r.get("runId") == entry.get("runId") for r in data["runs"]):
        raise OrchestratorError("Запуск %s уже зарегистрирован" % entry["runId"])
    data["runs"].append(entry)
    tmp = idx.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    os.replace(tmp, idx)
    return idx


# ------------------- Политика моделей -------------------

def load_policy(skill_root):
    p = Path(skill_root) / ROUTING_POLICY_RELPATH
    if not p.exists():
        raise OrchestratorError("Отсутствует политика маршрутизации: %s" % p)
    policy = json.loads(p.read_text(encoding="utf-8"))
    errors = validate_policy(policy)
    if errors:
        raise OrchestratorError("Невалидная политика: " + "; ".join(errors))
    return policy


def validate_policy(policy):
    errors = []
    if policy.get("schemaVersion") != SCHEMA_VERSION:
        errors.append("routing-policy: schemaVersion %r != %r"
                      % (policy.get("schemaVersion"), SCHEMA_VERSION))
    models = policy.get("models") or {}
    need = ["interview", "competitors_search", "posts_regular",
            "analysis_first_complex", "analysis_regular"]
    for k in need:
        m = models.get(k)
        if not isinstance(m, dict):
            errors.append("routing-policy: нет записи models.%s" % k)
            continue
        if not m.get("model"):
            errors.append("routing-policy: models.%s пустая модель" % k)
        if m.get("effort") not in ("low", "medium", "high"):
            errors.append("routing-policy: models.%s effort=%r" % (k, m.get("effort")))
    for st, sk in (policy.get("stageSkillMap") or {}).items():
        if st not in STAGES:
            errors.append("routing-policy: неизвестный этап %s" % st)
        elif sk != STAGES[st]["skill"]:
            errors.append("routing-policy: этап %s указывает на навык %s, ожидается %s"
                          % (st, sk, STAGES[st]["skill"]))
    for sk in (policy.get("allowedSkills") or []):
        if sk not in ALLOWED_SKILLS:
            errors.append("routing-policy: навык вне белого списка: %s" % sk)
    return errors


def policy_key_for_stage(stage, first_complex=False):
    if stage == "interview":
        return "interview"
    if stage == "competitors":
        return "competitors_search"
    if stage == "posts":
        return "posts_regular"
    if stage == "report":
        return "analysis_first_complex" if first_complex else "analysis_regular"
    raise OrchestratorError("Неизвестный этап: %s" % stage)


def model_for_stage(policy, stage, first_complex=False):
    key = policy_key_for_stage(stage, first_complex)
    m = policy["models"][key]
    return {"model": m["model"], "effort": m["effort"], "policyKey": key}


# ------------------- Проверка структуры workspace -------------------

def check_workspace(root):
    """Структура + наличие обязательных навыков. Возвращает список ошибок (пусто = OK)."""
    root = Path(root)
    errors = []
    skills = root / SKILLS_DIRNAME
    if not skills.is_dir():
        return ["Отсутствует каталог %s" % SKILLS_DIRNAME]
    for name in ALLOWED_SKILLS:
        d = skills / name
        if not d.is_dir():
            errors.append("В .agents/skills отсутствует навык: %s" % name)
            continue
        if not (d / "SKILL.md").exists():
            errors.append("У навыка %s нет SKILL.md" % name)
    stray = [p.name for p in skills.iterdir()
             if p.is_dir() and p.name not in ALLOWED_SKILLS]
    if stray:
        errors.append("Навыки вне белого списка цепочки: %s" % ", ".join(sorted(stray)))
    return errors


def check_required_inputs(root, stage):
    """Наличие и непустота обязательных входов этапа."""
    root = Path(root)
    missing = []
    for name in STAGES[stage]["inputs"]:
        p = root / name
        if not p.exists() or p.stat().st_size == 0:
            missing.append(name)
    return missing

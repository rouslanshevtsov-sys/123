#!/usr/bin/env python3
"""
Общий модуль навыка business-context-interview.

Единая точка правды для:
- схемы бизнес-контекста (SCHEMA) и списка обязательных полей;
- загрузки/сохранения JSON (одно чтение за запуск);
- канонического хэша sha256 (sha256:<64 hex>), used for data provenance;
- детекции секретов (используется всеми валидаторами, включая self-scan);
- извлечения данных из Markdown карточки;
- проверки синхронности MD/JSON;
- сборки компактного summary (provenance.json / chain_manifest.json) —
  downstream-навыки читают только его и сам business_context.json,
  не перечитывая крупные артефакты целиком.

Никаких сетевых запросов и чтения секретов отсюда не происходит:
токен VK API живёт только в vk_token.txt (вне git) и сюда не попадает.
"""

import hashlib
import json
import re
from pathlib import Path

# ---------------- Схема и обязательные поля ----------------

STATUS_ENUM = ["draft", "confirmed"]

SCHEMA = {
    "type": "object",
    "required": ["status", "business", "products", "audience", "geography",
                 "channels", "competitors", "gaps"],
    "properties": {
        "status": {"type": "string", "enum": STATUS_ENUM},
        "confirmationDate": {"type": ["string", "null"]},
        "generatedAt": {"type": ["string", "null"]},
        "source": {
            "type": "object",
            "required": ["url", "accessible"],
            "properties": {
                "url": {"type": "string"},
                "accessible": {"type": "boolean"},
                "parseError": {"type": ["string", "null"]},
            },
        },
        "business": {
            "type": "object",
            "required": ["name", "niche", "description"],
            "properties": {
                "name": {"type": ["string", "null"]},
                "niche": {"type": ["string", "null"]},
                "positioning": {"type": ["string", "null"]},
                "description": {"type": ["string", "null"]},
            },
        },
        "products": {
            "type": "object",
            "required": ["main", "producer"],
            "properties": {
                "main": {"type": "array", "items": {"type": "string"}},
                "secondary": {"type": "array", "items": {"type": "string"}},
                "assortmentWidth": {"type": ["string", "null"]},
                "producer": {"type": ["string", "null"]},
                "productionType": {"type": ["string", "null"]},
            },
        },
        "audience": {
            "type": "object",
            "required": ["targetSegments"],
            "properties": {
                "targetSegments": {"type": "array", "items": {"type": "string"}},
                "tasks": {"type": "array", "items": {"type": "string"}},
                "painPoints": {"type": "array", "items": {"type": "string"}},
            },
        },
        "geography": {
            "type": "object",
            "required": ["regions"],
            "properties": {
                "regions": {"type": "array", "items": {"type": "string"}},
                "format": {"type": ["string", "null"]},
            },
        },
        "pricing": {
            "type": "object",
            "properties": {
                "model": {"type": ["string", "null"]},
                "range": {"type": ["string", "null"]},
            },
        },
        "salesProcess": {
            "type": "object",
            "properties": {
                "orderProcess": {"type": ["string", "null"]},
                "paymentMethods": {"type": "array", "items": {"type": "string"}},
                "deliveryOrAccess": {"type": ["string", "null"]},
                "salesFormat": {"type": ["string", "null"]},
            },
        },
        "channels": {
            "type": "object",
            "required": ["acquisition", "onlinePresence"],
            "properties": {
                "acquisition": {"type": "array", "items": {"type": "string"}},
                "onlinePresence": {"type": "array", "items": {"type": "string"}},
            },
        },
        "advantages": {"type": "array", "items": {"type": "string"}},
        "limitations": {"type": "array", "items": {"type": "string"}},
        "keyFeatures": {"type": "array", "items": {"type": "string"}},
        "competitors": {
            "type": "object",
            "required": ["known", "classification"],
            "properties": {
                "known": {"type": "array", "items": {"type": "string"}},
                "classification": {"type": "object"},
            },
        },
        "searchCriteria": {
            "type": "object",
            "properties": {
                "mustHaveFeatures": {"type": "array", "items": {"type": "string"}},
                "searchPlatforms": {"type": "array", "items": {"type": "string"}},
                "count": {"type": ["string", "number", "null"]},
                "geography": {"type": ["string", "null"]},
                "vkAudienceLimit": {"type": ["string", "number", "null"]},
                "publicationFreshness": {"type": ["string", "null"]},
                "include": {"type": "array", "items": {"type": "string"}},
                "exclude": {"type": "array", "items": {"type": "string"}},
                "searchQueries": {"type": "array", "items": {"type": "string"}},
            },
        },
        "gaps": {"type": "array", "items": {"type": "string"}},
        # Поля происхождения данных (добавлены в v1.1, необязательны — обратная совместимость)
        "schemaVersion": {"type": "string"},
        "hashes": {"type": "object"},
        "validation": {
            "type": "object",
            "properties": {
                "jsonSyntaxValid": {"type": "boolean"},
                "syncedWithMarkdown": {"type": "boolean"},
                "noSecretsExposed": {"type": "boolean"},
                "noFabricatedData": {"type": "boolean"},
            },
        },
    },
}

REQUIRED_FIELDS = [
    ("business", "name"),
    ("business", "niche"),
    ("business", "description"),
    ("products", "main"),
    ("audience", "targetSegments"),
    ("geography", "regions"),
    ("channels", "acquisition"),
]

# ---------------- Хэши и происхождение ----------------


def canonical_hash(obj) -> str:
    """Канонический sha256: сортировка ключей, compact separators, ensure_ascii=False."""
    payload = json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(payload.encode("utf-8")).hexdigest()


def hash_of(context: dict) -> str:
    """Единое правило хэша контекста (см. references/chain-contract.md §4):
    канонический sha256 документа БЕЗ поля hashes (иначе самоцитата)."""
    return canonical_hash({k: v for k, v in context.items() if k != "hashes"})


def file_sha256(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return "sha256:" + h.hexdigest()


# ---------------- Загрузка / сохранение ----------------


def load_json(path):
    """Читает JSON одним проходом. Бросает ValueError с понятным сообщением."""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(str(p))
    try:
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(f"Ошибка парсинга JSON: {e}") from e


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


# ---------------- Секреты ----------------

SECRET_PATTERNS = [
    (r"vk1\.a\.[A-Za-z0-9_-]{10,}", "VK API токен"),
    (r"vk[0-9]\.[A-Za-z0-9_-]{10,}", "VK API токен"),
    (r"token[\"\s:=]+[\"\']?[A-Za-z0-9_-]{20,}", "Токен"),
    (r"access_token[\"\s:=]+[\"\']?[A-Za-z0-9_-]{20,}", "Access token"),
    (r"api[_-]?key[\"\s:=]+[\"\']?[A-Za-z0-9_-]{20,}", "API ключ"),
    (r"password[\"\s:=]+[\"\']?[^\s\"\']{8,}", "Пароль"),
    (r"passwd[\"\s:=]+[\"\']?[^\s\"\']{8,}", "Пароль"),
    (r"secret[\"\s:=]+[\"\']?[A-Za-z0-9_-]{20,}", "Секретный ключ"),
    (r"private[_-]?key[\"\s:=]+[\"\']?[A-Za-z0-9_-]{20,}", "Приватный ключ"),
    # JWT (VK service tokens and many others)
    (r"eyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}", "JWT токен"),
]

_COMPILED = [(re.compile(p, re.IGNORECASE), t) for p, t in SECRET_PATTERNS]


def detect_secrets_in_text(text: str, filename: str = "") -> list:
    found = []
    for rx, secret_type in _COMPILED:
        for m in rx.finditer(text):
            snippet = m.group(0)
            found.append({
                "file": filename,
                "type": secret_type,
                "match": snippet[:50] + "..." if len(snippet) > 50 else snippet,
            })
    return found


# ---------------- Markdown-карточка ----------------

MD_FIELD_PATTERNS = {
    "business_name": r"# Карточка бизнеса:\s*(.+)",
    "status_line": r"\*\*Статус:\*\*\s*(.+)",
    "confirmationDate": r"\*\*Дата подтверждения:\*\*\s*(.+)",
    "source_url": r"\*\*Источник:\*\*\s*(.+)",
    "niche": r"\*\*Ниша:\*\*\s*(.+)",
    "description": r"\*\*Описание:\*\*\s*(.+)",
}


def extract_data_from_markdown(md_content: str) -> dict:
    data = {}
    for key, pattern in MD_FIELD_PATTERNS.items():
        m = re.search(pattern, md_content)
        if not m:
            continue
        val = m.group(1).strip()
        if key == "status_line":
            data["status"] = "confirmed" if ("Подтверждено" in val or "confirmed" in val) else "draft"
        elif key == "confirmationDate":
            if val not in ("—", "-", ""):
                data["confirmationDate"] = val
        else:
            data[key] = val
    return data


SYNC_IGNORED_MD_KEYS = {"business_name"}


def _brackets_prefix_equal(a: str, b: str) -> bool:
    """Совпадают ли строки с точностью до скобочного уточнения в конце одной из них.
    Пример: «Школа Маркетинга (SHPM)» vs «Школа Маркетинга (SHPM Course)» — не расхождение."""
    import re as _re
    base = lambda s: _re.sub(r"\s*\([^)]*\)\s*$", "", s).strip()
    return base(a) == base(b)


def check_sync_errors(md_data: dict, json_data: dict) -> list:
    """Расхождения между MD и JSON. Название сверяется префиксно/по скобочному правилу
    (см. references/chain-contract.md §2 и card-structure.md «Правила синхронизации»)."""
    diffs = []

    md_name = md_data.get("business_name")
    json_name = json_data.get("business", {}).get("name")
    if md_name is not None and json_name is not None:
        md_n, json_n = md_name.strip(), json_name.strip()
        ok = (md_n == json_n or json_n.startswith(md_n) or md_n.startswith(json_n)
              or _brackets_prefix_equal(md_n, json_n))
        if not ok:
            diffs.append(f'business.name: MD="{md_name}", JSON="{json_name}"')

    pairs = [
        ("status", md_data.get("status"), json_data.get("status")),
        ("confirmationDate", md_data.get("confirmationDate"), json_data.get("confirmationDate")),
        ("source.url", md_data.get("source_url"), json_data.get("source", {}).get("url")),
        ("business.niche", md_data.get("niche"), json_data.get("business", {}).get("niche")),
        ("business.description", md_data.get("description"), json_data.get("business", {}).get("description")),
    ]
    for name, a, b in pairs:
        if a == b:
            continue
        # «пусто с обеих сторон» — не расхождение
        if not a and not b:
            continue
        diffs.append(f'{name}: MD="{a}", JSON="{b}"')
    return diffs


# ---------------- Валидация схемы ----------------

_TYPE_MAP = {
    "object": dict, "array": list, "string": str,
    "boolean": bool, "number": (int, float), "integer": int, "null": type(None),
}


def _py_type(names):
    names = names if isinstance(names, list) else [names]
    types = tuple(_TYPE_MAP[n] for n in names)
    # bool — подкласс int; number не должен принимать bool
    if bool in types and (int in types or float in types):
        types = tuple(t for t in types if t is not bool)
    return types


def validate_schema(data, schema, path=""):
    errors = []
    if "type" in schema:
        expected = _py_type(schema["type"])
        ok = isinstance(data, expected)
        if ok and "boolean" in (schema["type"] if isinstance(schema["type"], list) else [schema["type"]]):
            ok = isinstance(data, bool)
        if not ok:
            errors.append(f"{path or 'root'}: ожидался тип {schema['type']}, получен {type(data).__name__}")
            return errors
    if "enum" in schema and data not in schema["enum"]:
        errors.append(f"{path or 'root'}: значение должно быть одним из {schema['enum']}")
    if "required" in schema and isinstance(data, dict):
        for field in schema["required"]:
            if field not in data:
                errors.append(f"{path or 'root'}: отсутствует обязательное поле '{field}'")
    if "properties" in schema and isinstance(data, dict):
        for prop, sub in schema["properties"].items():
            if prop in data:
                errors.extend(validate_schema(data[prop], sub, f"{path}.{prop}" if path else prop))
    if schema.get("type") in ("array", ["array"]) and isinstance(data, list) and "items" in schema:
        for i, item in enumerate(data):
            errors.extend(validate_schema(item, schema["items"], f"{path}[{i}]"))
    return errors


def check_required_values(data: dict) -> list:
    missing = []
    for fp in REQUIRED_FIELDS:
        v = data
        ok = True
        for key in fp:
            if not isinstance(v, dict) or key not in v:
                ok = False
                break
            v = v[key]
        if not ok or v is None or (isinstance(v, str) and not v.strip()) or (isinstance(v, list) and not v):
            missing.append(".".join(fp))
    return missing


# ---------------- Компактный summary (кэш для downstream) ----------------

SUMMARY_CONTRACT_VERSION = "1.1"


def build_summary(context: dict, run_dir=None) -> dict:
    """Компактный provenance/manifest (~1 КБ). Пересобирается из business_context.json за O(1) чтение."""
    src = context.get("source", {})
    biz = context.get("business", {})
    comp = context.get("competitors", {})
    sc = context.get("searchCriteria", {})
    hashes = context.get("hashes", {}) or {}
    files = {}
    if run_dir is not None:
        for fname in ("business_context.json", "business_card.md"):
            p = Path(run_dir) / fname
            if p.exists():
                files[fname] = file_sha256(p)
    return {
        "contractVersion": SUMMARY_CONTRACT_VERSION,
        "skill": "business-context-interview",
        "status": context.get("status"),
        "confirmationDate": context.get("confirmationDate"),
        "generatedAt": context.get("generatedAt"),
        "businessName": biz.get("name"),
        "niche": biz.get("niche"),
        "sourceUrl": src.get("url"),
        "sourceAccessible": src.get("accessible"),
        "contextHash": hashes.get("business_context.json") or hash_of(context),
        "counts": {
            "knownCompetitors": len(comp.get("known", [])),
            "searchQueries": len(sc.get("searchQueries", [])),
            "gaps": len(context.get("gaps", [])),
        },
        "files": files,
    }


# ---------------- Контракт цепочки навыков (v1.2) ----------------
# Интервью -> Конкуренты -> Лучшие посты -> Анализ реакции рынка.
# Единые правила для всех навыков: имена артефактов, кэш summary, порог входа.

# Имена ниже сверены с реальными навыками цепочки (ветки origin:
# search-vk-competitors, analyze-vk-best-posts, vk-content-report; см. chain-contract.md §2).
ARTIFACT_NAMES = {
    "context": "business_context.json",          # результат этапа 1 (полный контекст)
    "card": "business_card.md",                  # человекочитаемая карточка этапа 1
    "provenance": "provenance.json",             # компактный summary этапа 1 (кэш)
    "competitors": "competitor_set.json",        # результат этапа 2 (реальное имя навыка поиска)
    "competitors_summary": "competitors_summary.json",  # компактный summary этапа 2 (необязательный)
    "posts": "vk_posts_dataset.json",            # результат этапа 3 (реальное имя collect/analyze)
    "posts_comments": "comments.json",           # комментарии этапа 3, обязательный вход этапа 4
    "posts_xlsx": "competitors_vk_report.xlsx",  # XLSX этапа 3, обязательный вход этапа 4
    "posts_summary": "posts_summary.json",       # компактный summary этапа 3 (необязательный)
    "reactions": "report.html",                  # результат этапа 4 (HTML-отчёт)
    "reactions_data": "market_reactions.json",   # машиночитаемые реакции этапа 4
    "input_provenance": "provenance.json",       # происхождение входа этапа 4 (совпадает с provenance)
    "manifest": "chain_manifest.json",           # итоговый манифест цепочки
}

# Устаревшие имена из черновика контракта v1.1 → канон v1.2 (обратная совместимость
# описаний; скрипты всегда берут каноническое имя из ARTIFACT_NAMES).
LEGACY_ARTIFACT_ALIASES = {
    "competitors.json": "competitor_set.json",
    "best_posts.json": "vk_posts_dataset.json",
}

# Единый порядок имён токена VK API для всех навыков цепочки.
# Альтернативные переменные окружения поддерживаются, но устарели.
TOKEN_FILE_NAME = "vk_token.txt"      # токен живёт только здесь, вне git и вне результатов этапов
TOKEN_ENV_PRIMARY = "VK_API_TOKEN"
TOKEN_ENV_LEGACY = ("VK_TOKEN", ".token")  # env VK_TOKEN / файл .token — legacy, не добавлять в новых навыках


def load_cached_summary(run_dir, context_path=None):
    """Кэш compact summary: перечитывает business_context.json ТОЛЬКО если
    provenance.json отсутствует или его contextHash не совпал с пересчитанным.
    Возвращает dict summary."""
    run_dir = Path(run_dir)
    prov_path = run_dir / ARTIFACT_NAMES["provenance"]
    ctx_path = Path(context_path) if context_path else run_dir / ARTIFACT_NAMES["context"]
    cached = None
    if prov_path.exists():
        try:
            cached = load_json(prov_path)
        except ValueError:
            cached = None
    ctx = load_json(ctx_path)
    current_hash = (ctx.get("hashes") or {}).get(ARTIFACT_NAMES["context"]) or hash_of(ctx)
    if cached and cached.get("contextHash") == current_hash:
        return cached  # HIT — крупный файл использован только для канонического хэша
    summary = build_summary(ctx, run_dir=run_dir)
    save_json(prov_path, summary)
    return summary  # MISS — кэш пересобран


def require_confirmed_context(context_path):
    """Порог входа для downstream-навыков (конкуренты/посты/реакции).
    Бросает SystemExit(1) с понятным сообщением, если вход не готов."""
    try:
        ctx = load_json(context_path)
    except FileNotFoundError:
        raise SystemExit(f"✗ Вход не найден: {context_path}. Сначала выполните навык интервью.")
    except ValueError as e:
        raise SystemExit(f"✗ {e}")
    if ctx.get("status") != "confirmed":
        raise SystemExit('✗ business_context.json имеет статус "%s", требуется "confirmed".'
                         % ctx.get("status"))
    missing = check_required_values(ctx)
    if missing:
        raise SystemExit("✗ Пустые обязательные поля: %s. Вернитесь к интервью." % ", ".join(missing))
    secrets = detect_secrets_in_text(json.dumps(ctx, ensure_ascii=False), str(context_path))
    if secrets:
        raise SystemExit("✗ В контексте обнаружены секреты (%s). Удалите их до передачи дальше."
                         % {s["type"] for s in secrets})
    return ctx

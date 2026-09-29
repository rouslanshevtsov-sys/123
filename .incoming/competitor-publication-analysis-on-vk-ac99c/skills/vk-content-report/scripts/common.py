#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Общие правила навыка vk-content-report.

Содержит только правила: контракт входа, формулы ER и бенчмарков, правило сегментов,
словари ER-/CTA-/содержательных сигналов, классификацию комментариев, словари запретов.
Данных конкретного бизнеса, конкурентов или запуска здесь нет.
"""
import hashlib
import json
import os
import re
from datetime import datetime, timedelta, timezone

MSK = timezone(timedelta(hours=3))

# ------------------------------------------------------------- контракт входа
REQUIRED_INPUTS = {
    "dataset": "vk_posts_dataset.json",
    "comments": "comments.json",
    "excel": "competitors_vk_report.xlsx",
    "provenance": "provenance.json",
}
OPTIONAL_INPUTS = {
    "media_dir": "media",
    "transcripts_dir": "media/transcripts",
    "benchmarks": "benchmarks.json",
    "run_meta": "run_meta.json",
    "unavailable": "unavailable.json",
}

DATASET_REQUIRED_FIELDS = [
    "post_id", "url", "group_name", "date_msk", "main_type",
    "likes", "comments", "reposts", "views", "er", "benchmark",
]
COMMENT_REQUIRED_FIELDS = ["post_id", "text"]
PROVENANCE_REQUIRED_FIELDS = ["produced_by", "generated_at_msk", "files"]

COMPETITOR_TYPE_ORDER = ["direct", "indirect", "attention"]
COMPETITOR_TYPE_LABEL = {"direct": "прямые", "indirect": "косвенные", "attention": "за внимание"}

TOP_SHARE = 0.25
BOTTOM_SHARE = 0.25
ER_RATIO_THRESHOLD = 2.0        # числовые сравнения ER только при rel >= 2x либо <= 0.5x
ER_TOLERANCE_PP = 0.005          # допуск пересчёта ER, абсолютные доли
BENCHMARK_TOLERANCE_REL = 0.02   # допуск пересчёта бенчмарка, относительный

# --------------------------------------------------------- типы публикаций
CLIP_TYPES = {"VK Клип", "Клип", "clip", "short_video"}
NON_CLIP_TYPES = {"Текстовый пост", "Картинка", "Карусель", "Видео", "Опрос", "Страница"}

# ------------------------------------------------------- CTA / хуки / триггеры
CTA_PATTERNS = [
    ("опрос или выбор варианта в комментариях",
     r"(голосуй|проголосуй|опрос|выбери|напиши цифру|напиши номер|1\)|2\))"),
    ("вопрос к аудитории за мнением",
     r"(что думаете|как вам|спрошу|задай вопрос|задайте вопрос|мнение в комментах)"),
    ("сохранить или поделиться",
     r"(сохраняй|сохрани|перешли|поделись|отправь другу|в закладки)"),
    ("обсудить в комментариях",
     r"(обсуди|делись опытом|ждём тво|напиши в комментариях|комментах ниже)"),
    ("переход по ссылке или заявка",
     r"(по ссылке|переходи|записывайся|регистрация|заявка|узнай больше|жми)"),
    ("продолжение в следующем посте",
     r"(продолжение завтра|во второй части|в следующем посте|не переключайся)"),
]

TRIGGER_LEXICON = {
    "финансовое давление и желание больше зарабатывать":
        r"(зарплат|доход|деньги|заработ|прибыл|окуп|бюджет|дешев|дорог|бесплатно)",
    "страх отстать от рынка и коллег":
        r"(устарел|отстаю|не успеваю|все уже|пока другие|пора менять|новое поколение|остался позади)",
    "профессиональная гордость и узнавание себя":
        r"(узнал себя|узнала себя|это про нас|мы так и делаем|наш случай|коллеги подтвердят)",
    "безопасность людей и ответственность за них":
        r"(безопасн|не защищены|травм|жизнь людей|ответственн|риски для людей)",
    "экономия времени и готовое решение":
        r"(шаблон|чек-?лист|готовый|за \d+ минут|конструктор|инструкц|по полочкам)",
    "недоверие к обещаниям и «экспертности»":
        r"(пирамида|развод|очередн|слишком красиво|не верю|фейк|лохотрон)",
    "усталость от работы и выгорание":
        r"(выгор|устал|нет сил|работ(а|ю) на износ|смен(а|ы) без выходных)",
}

POSITIVE_LEX = (r"(спасибо|классно|круто|супер|отлично|здорово|полезно|согласен|согласна|"
                r"люблю|огонь|\U0001f525|❤)")
NEGATIVE_LEX = (r"(бред|ужас|отписка|листаем дальше|не интересно|скучно|развод|пирамида|"
                r"обман|не верю|мусор|лохотрон)")
QUESTION_MARKS = ("?",)
OBJECTION_MARKS = (r"\bно\b", "однако", "не соглас", "проблема в том", "а вот у нас")
PRODUCT_INTEREST = (r"(сколько стоит|цена|как записаться|курс|обучени|наставник|консультаци|"
                    r"где купить|скачать|подскажите|помогите выбрать|есть ли у вас)")
PERSONAL_STORY = (r"(у меня так же|у нас также|я так делал|сталкивался|было также|"
                  r"моя история|год назад я)")
PROBLEM_STATEMENT = (r"(не могу|не понимаю|нет времени|не хватает|застрял|выгор|сложно|"
                     r"тяжело|не получается)")
DESIRES = r"(хочу|мечтаю|надо бы|пора начать|жду продолжения|хотелось бы)"
PURCHASE_MOTIVE = (r"(куплю|беру|пойду|запишусь|хочу на курс|готов платить|оплачу|"
                   r"пришлите прайс|нужен наставник|сколько стоит)")

SPAM_MIN_REPEATS = 5   # один текст на N+ постах — шаблонный спам, исключается из сигналов

# --------------------------------------------------- запреты в тексте отчёта
CAUSAL_WORDS = [
    "потому что", "благодаря", "поэтому сработало", "поэтому выстрелило", "из-за этого",
    "именно это и привело", "секрет успеха", "причина в том", "за счёт этого",
    "аудитория отреагировала так, потому",
]
RECOMMENDATION_MARKERS = [
    "рекомендуем", "рекомендация", "рекомендуется", "советуем", "совет:", "рекомендую",
    "нужно делать", "стоит добавить", "следует использовать", "используйте", "вам следует",
    "добавьте", "контент-план", "идеи постов", "идеи публикаций", "что делать дальше",
    "как вам повторить", "лучше публиковать", "планируйте", "сделайте так", "вывод для вас",
    "что взять себе", "примените", "протестируйте", "внедрите", "повторите это",
]
AI_FILLER_MARKERS = [
    "важно отметить", "в заключение хочется", "в современном мире", "нельзя не обратить",
    "данная публикация демонстрирует", "следует подчеркнуть", "комплексный подход",
    "в рамках данного анализа", "в динамично меняющемся",
]

# --------------------------------------------------------------- аргументы/обещания
ARGUMENT_PATTERNS = {
    "цифры и метрики": r"(\d+\s*(%|процент|\$|₽|руб|раз|млн|млрд|тыс|человек|клиент))",
    "кейс или личная история": r"(кейс|истори(я|ей)|в нашем проекте|у клиента|результат через)",
    "отзыв или цитата человека": r"(отзыв|мнение клиента|говорит|пишет|комментирет)",
    "демонстрация процесса": r"(смотри|показыва|разбор|по шагам|шаг \d|до/после|до и после)",
    "сравнение вариантов": r"(сравни|чем отличается|vs|против|лучше чем|до vs после|вариант а|вариант б)",
    "список или чек-лист": r"(топ-?\d|\d+\.\s|чек-?лист|подборк|списк)",
}
PROMISE_PATTERNS = {
    "обещание конкретного результата": r"(увеличишь|получишь|вырастет|поднимет|принесёт|сэкономит)",
    "обещание скорости": r"(за \d+ (минут|дней|часов)|быстро|за неделю|за месяц)",
    "обещание денег или клиентов": r"(клиент(ов)?|деньги|доход|прибыл|продаж)",
    "обещание секрета или инсайда": r"(секрет|тайн|инсайд|о чём молчат|не расскажут)",
}

EMOJI_RE = re.compile(r"[\U0001F000-\U0001FAFF\u2600-\u27BF\uFE0F\u200d]")


# ------------------------------------------------------------------ базовые хелперы
def first_line(text):
    if not text:
        return ""
    for line in str(text).splitlines():
        s = line.strip()
        if s:
            return s
    return ""


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path, data):
    parent = os.path.dirname(os.path.abspath(path))
    os.makedirs(parent, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)


def sha256_file(path, block=1 << 20):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            chunk = f.read(block)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


POST_URL_RE = re.compile(r"^https://vk\.com/(?:wall|clip)-\d+_\d+$")


def is_valid_post_url(u):
    return bool(POST_URL_RE.match((u or "").strip()))


def url_from_post_id(post_id):
    pid = str(post_id or "").strip()
    return f"https://vk.com/wall{pid}" if re.match(r"^-\d+_\d+$", pid) else None


def parse_date_msk(s):
    if not s:
        return None
    txt = str(s).strip().replace("T", " ")[:16]
    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            dt = datetime.strptime(txt, fmt)
        except ValueError:
            continue
        return dt.replace(tzinfo=MSK)
    return None


# --------------------------------------------------------------- ER и бенчмарки
def compute_er(likes, comments, reposts, views):
    try:
        v = float(views or 0)
    except (TypeError, ValueError):
        return None
    if v <= 0:
        return None
    return (float(likes or 0) + float(comments or 0) + float(reposts or 0)) / v


def er_matches(recorded, recomputed, tol_pp=ER_TOLERANCE_PP):
    if recorded is None or recomputed is None:
        return False
    return abs(float(recorded) - float(recomputed)) <= tol_pp


def benchmark_of(posts):
    vals = [p["er"] for p in posts if p.get("er") is not None]
    if not vals:
        return None
    return sum(vals) / len(vals)


def benchmarks_match(recorded, recomputed, rel_tol=BENCHMARK_TOLERANCE_REL):
    if recorded in (None, 0) or recomputed in (None, 0):
        return recorded == recomputed
    return abs(recorded - recomputed) / abs(recomputed) <= rel_tol


def rel_er(er, benchmark):
    if not er or not benchmark:
        return None
    return er / benchmark


def numeric_er_comparison_allowed(rel):
    """Числовое сравнение ER разрешено только при rel >= 2 или rel <= 0.5."""
    if rel is None:
        return False
    return rel >= ER_RATIO_THRESHOLD or rel <= 1.0 / ER_RATIO_THRESHOLD


# ------------------------------------------------------------------- сегменты 25%
def split_quartiles(posts, top=TOP_SHARE, bottom=BOTTOM_SHARE):
    scored = [p for p in posts if p.get("rel_er_vs_benchmark") is not None]
    scored.sort(key=lambda p: (-p["rel_er_vs_benchmark"], p.get("post_id", "")))
    n = len(scored)
    if not n:
        return [], [], []
    k_top = max(1, int(round(n * top)))
    k_bot = max(1, int(round(n * bottom)))
    k_top = min(k_top, n)
    k_bot = min(k_bot, max(0, n - k_top))
    return scored[:k_top], scored[k_top:n - k_bot], scored[n - k_bot:] if k_bot else []


def strong_weak_sets(posts):
    return split_quartiles(posts)


# ---------------------------------------------------------------------- медиа и клипы
def media_paths_of(post):
    out = []
    for key in ("image_paths", "images_local", "collage_paths", "clip_paths",
                "transcript_path", "transcripts"):
        val = post.get(key)
        if isinstance(val, str):
            out.append(val)
        elif isinstance(val, list):
            out += [v for v in val if isinstance(v, str)]
    return out


def is_clip(post):
    if post.get("is_clip") or post.get("clip_status"):
        return True
    if str(post.get("main_type") or "") in CLIP_TYPES:
        return True
    for c in (post.get("clips") or []):
        if isinstance(c, dict) and str(c.get("type") or "") in ("clip", "short_video"):
            return True
    for v in (post.get("videos") or []):
        if isinstance(v, dict) and str(v.get("type") or "") in ("clip", "short_video"):
            return True
    return False


def transcript_of(post, transcripts_dir=None):
    path = post.get("transcript_path")
    if isinstance(path, str) and path:
        candidates = [path]
        if transcripts_dir and not os.path.isabs(path):
            candidates.insert(0, os.path.join(transcripts_dir, os.path.basename(path)))
        for cand in candidates:
            if os.path.exists(cand):
                try:
                    with open(cand, "r", encoding="utf-8") as f:
                        raw = f.read()
                except OSError:
                    continue
                try:
                    data = json.loads(raw)
                    if isinstance(data, dict):
                        return data.get("text") or data.get("transcript") or ""
                    return raw
                except json.JSONDecodeError:
                    return raw
    inline = post.get("transcript") or post.get("clip_transcript")
    return inline if isinstance(inline, str) else ""


# ------------------------------------------------------------- комментарии и спам
def detect_spam_templates(comments, min_repeats=SPAM_MIN_REPEATS):
    groups = {}
    for c in comments:
        txt = re.sub(r"\s+", " ", (c.get("text") or "").strip().lower())
        if len(txt) < 20:
            continue
        groups.setdefault(txt, []).append(c)
    spam = {}
    for txt, items in groups.items():
        if len(items) >= min_repeats:
            key = hashlib.sha1(txt.encode("utf-8")).hexdigest()[:12]
            spam[key] = {"text": items[0].get("text"), "occurrences": len(items),
                         "post_ids": sorted({i.get("post_id") for i in items if i.get("post_id")})}
    return spam


def classify_comment(text, spam=False):
    cats = []
    body = (text or "").strip()
    if spam:
        return ["spam_ad"]
    if not body:
        return ["empty_or_emoji"]
    letters = re.sub(EMOJI_RE, "", body).strip()
    if not letters or not re.search(r"[А-Яа-яA-Za-z]", letters):
        return ["empty_or_emoji"]
    low = body.lower()
    if any(m in low for m in QUESTION_MARKS):
        cats.append("question")
    if re.search(PRODUCT_INTEREST, low):
        cats.append("product_interest_question")
    if re.search(PURCHASE_MOTIVE, low):
        cats.append("purchase_motive")
    objection = re.search(OBJECTION_MARKS[0], low) or any(m in low for m in OBJECTION_MARKS[1:])
    if objection:
        cats.append("objection_or_doubt")
    if re.search(PROBLEM_STATEMENT, low):
        cats.append("problem_statement")
    if re.search(PERSONAL_STORY, low):
        cats.append("personal_story_resonance")
    if re.search(DESIRES, low):
        cats.append("desire")
    if re.search(POSITIVE_LEX, low):
        cats.append("positive_reaction")
    if re.search(NEGATIVE_LEX, low):
        cats.append("negative_reaction")
    if re.search(TRIGGER_LEXICON["безопасность людей и ответственность за них"], low):
        cats.append("safety_concern")
    if not cats:
        cats.append("comment_on_topic_no_clear_signal")
    return sorted(set(cats))


COMMENT_CATEGORY_DEFS = {
    "question": "Вопрос аудитории (есть знак «?»)",
    "product_interest_question": "Вопрос с интересом к продукту или просьбой подсказать",
    "purchase_motive": "Мотив покупки: цена, запись, готовность платить",
    "objection_or_doubt": "Возражение, сомнение, спор, «но…»",
    "problem_statement": "Аудитория описывает свою проблему",
    "desire": "Желание, намерение, запрос продолжения",
    "personal_story_resonance": "Личная история «у меня так же» — узнавание",
    "safety_concern": "Тревога за безопасность людей",
    "positive_reaction": "Положительная реакция: спасибо, классно, согласие",
    "negative_reaction": "Отрицательная реакция: бред, пирамида, «листаем дальше»",
    "comment_on_topic_no_clear_signal": "Комментарий по теме без выраженного сигнала",
    "empty_or_emoji": "Пустой комментарий или только эмодзи",
    "spam_ad": "Рекламный спам-шаблон (исключён из сигналов)",
}


# ------------------------------------------------------------- сигналы публикации
def extract_cta(text):
    body = text or ""
    found = []
    for sentence in re.split(r"(?<=[.!?])\s+", body):
        low = sentence.lower()
        for label, pat in CTA_PATTERNS:
            if re.search(pat, low):
                found.append({"type": label, "quote": sentence.strip()[:240]})
                break
    dedup, seen = [], set()
    for item in found:
        if item["type"] in seen:
            continue
        seen.add(item["type"])
        dedup.append(item)
    if not dedup:
        dedup.append({"type": "без прямого призыва", "quote": first_line(body)[:240]})
    return dedup


def extract_hooks(text):
    body = text or ""
    fl = first_line(body)
    out = []
    if "?" in fl:
        out.append("вопрос в первой строке")
    if EMOJI_RE.match(fl[:2]):
        out.append("эмодзи-крючок в начале")
    if re.search(r"\d", fl[:40]):
        out.append("цифра в первых 40 символах")
    if 0 < len(fl) <= 60 and not fl.endswith("."):
        out.append("короткая фраза без точки в конце")
    if re.search(r"(как |почему |что будет, если)", fl, re.I):
        out.append("вопрос-интрига «как/почему»")
    return out


def argument_types(text):
    low = (text or "").lower()
    return [name for name, pat in ARGUMENT_PATTERNS.items() if re.search(pat, low)]


def promise_types(text):
    low = (text or "").lower()
    return [name for name, pat in PROMISE_PATTERNS.items() if re.search(pat, low)]


def trigger_hits(text):
    low = (text or "").lower()
    return [name for name, pat in TRIGGER_LEXICON.items() if re.search(pat, low)]


def tone_of(text):
    body = text or ""
    low = body.lower()
    out = []
    if re.search(r"\b(ты|твой|тебя| тебе)\b", low):
        out.append("на «ты»")
    if re.search(r"\b(вы|ваш|вас|вам)\b", low):
        out.append("на «вы»")
    if EMOJI_RE.search(body):
        out.append("с эмодзи")
    if re.search(r"(давай|друзья|ребят|народ)", low):
        out.append("разговорный")
    if re.search(r"(метод|алгоритм|стратегия|позиционирован)", low):
        out.append("экспертный")
    if re.search(r"(смешн|прикол|meme|мем)", low):
        out.append("шутливый")
    return out or ["нейтральный"]


def has_causal_claim(text):
    low = (text or "").lower()
    return [w for w in CAUSAL_WORDS if w in low]


def has_recommendation(text):
    low = (text or "").lower()
    return [m for m in RECOMMENDATION_MARKERS if m in low]


def has_ai_filler(text):
    low = (text or "").lower()
    return [m for m in AI_FILLER_MARKERS if m in low]


# ------------------------------------------------------------------------ HTML
def strip_html(html_text):
    txt = re.sub(r"<script.*?</script>", " ", html_text or "", flags=re.S | re.I)
    txt = re.sub(r"<style.*?</style>", " ", txt, flags=re.S | re.I)
    txt = re.sub(r"<[^>]+>", " ", txt)
    for a, b in (("&nbsp;", " "), ("&laquo;", "«"), ("&raquo;", "»"), ("&mdash;", "—"),
                 ("&ndash;", "–"), ("&amp;", "&"), ("&quot;", '"'), ("&#39;", "'")):
        txt = txt.replace(a, b)
    return re.sub(r"[ \t]+", " ", txt)


def sentences_of(html_text):
    """Считает только текстовые блоки отчёта (абзацы, заголовки, пункты списков).

    Метаслужебные строки (таблицы показателей, карточки метрик, ссылки-доказательства)
    не являются предложениями текста и в объём не входят.
    """
    txt = re.sub(r"<(script|style|table)\b.*?</\1>", " ", html_text or "", flags=re.S | re.I)
    parts = re.findall(r"<(?:p|h[1-6]|li)\b[^>]*>(.*?)</(?:p|h[1-6]|li)>", txt, flags=re.S | re.I)
    out = []
    for p in parts:
        s = strip_html(p).strip()
        if len(s) > 2 and not s.startswith(("http", "-")):
            out.extend(x.strip() for x in re.split(r"(?<=[.!?])\s+", s) if len(x.strip()) > 2)
    return out


def word_count(html_text):
    return len(strip_html(html_text).split())


LINK_RE = re.compile(r'<a\s[^>]*href="([^"]+)"[^>]*>', re.I)


def html_links(html_text):
    return LINK_RE.findall(html_text or "")


# ---------------------------------------------------------------- XLSX и нормализация
def read_xlsx_rows(path, sheet=None):
    import openpyxl
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    names = wb.sheetnames if sheet is None else [s for s in [sheet] if s in wb.sheetnames]
    result = {}
    for nm in names:
        ws = wb[nm]
        rows = [r for r in ws.iter_rows(values_only=True)]
        if not rows:
            result[nm] = []
            continue
        header = [str(h).strip() if h is not None else "" for h in rows[0]]
        recs = []
        for r in rows[1:]:
            if r is None or all(v is None for v in r):
                continue
            recs.append({header[i]: r[i] for i in range(min(len(header), len(r)))})
        result[nm] = recs
    wb.close()
    return result


def find_post_id_in_row(row):
    for key, val in row.items():
        if "id" in str(key).lower() and isinstance(val, str) and re.match(r"^-\d+_\d+$", val.strip()):
            return val.strip()
    for val in row.values():
        if isinstance(val, str):
            m = re.search(r"wall(-\d+_\d+)", val)
            if m:
                return m.group(1)
    return None


def find_url_in_row(row):
    for val in row.values():
        if isinstance(val, str) and val.startswith("http"):
            return val.strip()
    return None


POST_LIST_KEYS = ("posts", "best_posts", "worst_posts", "checked_posts", "items", "records", "data")


def normalize_dataset(raw):
    """Приводит датасет к списку публикаций. Возвращает (posts, meta_dict)."""
    if isinstance(raw, list):
        return raw, {}
    if isinstance(raw, dict):
        meta = {k: v for k, v in raw.items() if not isinstance(v, list)}
        posts = []
        for key in POST_LIST_KEYS:
            val = raw.get(key)
            if isinstance(val, list):
                for item in val:
                    if isinstance(item, dict):
                        it = dict(item)
                        it.setdefault("_source_list", key)
                        posts.append(it)
        if posts:
            return posts, meta
        for key, val in raw.items():
            if isinstance(val, list) and val and isinstance(val[0], dict):
                for item in val:
                    it = dict(item)
                    it.setdefault("_source_list", key)
                    posts.append(it)
                return posts, meta
    raise ValueError("В датасете не найден список публикаций")


def normalize_comments(raw):
    """comments.json любого вида -> плоский список {post_id, text, likes, ...}."""
    out = []

    def push(rec, fallback_pid=None):
        if not isinstance(rec, dict):
            return
        pid = rec.get("post_id") or rec.get("owner_item") or fallback_pid
        txt = rec.get("text") or rec.get("comment_text") or rec.get("body") or ""
        out.append({
            "post_id": str(pid).strip() if pid is not None else None,
            "text": txt,
            "likes": rec.get("likes", rec.get("comment_likes", 0)) or 0,
            "reply_to": rec.get("reply_to", rec.get("reply_to_cid")),
            "date": rec.get("date") or rec.get("date_msk"),
        })

    if isinstance(raw, list):
        for rec in raw:
            if isinstance(rec, dict) and isinstance(rec.get("comments"), list):
                for c in rec["comments"]:
                    push(c, rec.get("post_id"))
            else:
                push(rec)
        return out
    if isinstance(raw, dict):
        items = raw.get("comments") or raw.get("items") or raw.get("records") or raw.get("posts") or []
        if isinstance(items, dict):
            for pid, lst in items.items():
                for c in (lst or []):
                    push(c, pid)
            return out
        for rec in items:
            if isinstance(rec, dict) and isinstance(rec.get("comments"), list):
                for c in rec["comments"]:
                    push(c, rec.get("post_id"))
            else:
                push(rec)
    return out


def excel_sheet_map(xlsx_rows):
    mapping = {}
    for name in xlsx_rows:
        low = name.lower()
        if "лучш" in low or "best" in low:
            mapping.setdefault("best", name)
        elif "клип" in low or "clip" in low:
            mapping.setdefault("clips", name)
        elif "недоступ" in low or "unavailable" in low:
            mapping.setdefault("unavailable", name)
        elif "свод" in low or "summary" in low or "бенчмарк" in low:
            mapping.setdefault("summary", name)
        elif "провер" in low or "checked" in low or "пост" in low:
            mapping.setdefault("checked", name)
    return mapping


def group_key(post):
    return post.get("group_name") or post.get("group") or str(post.get("owner_id"))


def competitor_type(post):
    t = (post.get("group_type") or post.get("competitor_type") or "attention")
    return t if t in COMPETITOR_TYPE_ORDER else "attention"

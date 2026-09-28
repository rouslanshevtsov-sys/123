#!/usr/bin/env python3
"""Общие утилиты навыка analyze-vk-best-posts.

Не содержит токенов, данных конкретных запусков и абсолютных путей.
Все пути — относительные от рабочей директории (WORKDIR), задаётся через
VK_WORK_DIR или --workdir. Часовой пояс — Europe/Moscow (фиксированный UTC+3).
"""
import json
import os
import re
from datetime import datetime, timedelta, timezone

MSK = timezone(timedelta(hours=3))  # Europe/Moscow (stable UTC+3)
WINDOW_HOURS_DEFAULT = 168          # 7 × 24 часа
API_VERSION = "5.199"
API_URL = "https://api.vk.com/method/"

TYPE_ORDER = {"direct": 0, "indirect": 1, "attention": 2}
TYPE_RU = {
    "direct": "Прямые конкуренты",
    "indirect": "Косвенные конкуренты",
    "attention": "Конкуренты за внимание",
}
VALID_TYPES = set(TYPE_ORDER)

EXCEL_SHEETS = ["Сводка", "Лучшие посты", "Клипы", "Проверенные посты", "Недоступно"]
BEST_POSTS_COLUMNS = [
    "Сообщество", "Тип конкурента", "Ссылка на пост", "Текст", "Тип поста",
    "Опрос", "Розыгрыш", "Лайки", "Комментарии", "Просмотры для ER",
    "ER поста", "Бенчмарк", "Расшифровка", "Изображения", "ID поста",
]
VERIFIED_POSTS_COLUMNS = [
    "Сообщество", "VK сообщества", "Подписчики", "Дата поста", "Ссылка на пост",
    "Текст", "Тип поста", "Опрос", "Розыгрыш", "Лайки", "Комментарии", "Репосты",
    "Просмотры для ER", "ER поста", "Бенчмарк", "Результат", "Статус данных",
]
UNAVAILABLE_COLUMNS = ["Объект", "Ссылка", "Конкретная причина"]
CLIPS_COLUMNS = [
    "Сообщество", "Ссылка на пост", "Внешний тип", "Внутренний тип (video.get)",
    "Просмотры клипа", "Файл", "Статус обработки", "Расшифровка",
]


def workdir(create=False):
    d = os.environ.get("VK_WORK_DIR") or os.getcwd()
    if create:
        os.makedirs(d, exist_ok=True)
    return d


def path(*parts, base=None):
    return os.path.join(base or workdir(), *parts)


def load_json(name, default=None, base=None):
    p = path(name, base=base)
    if not os.path.exists(p):
        if default is not None:
            return default
        raise FileNotFoundError(f"Файл не найден: {name}")
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def save_json(name, data, base=None, indent=1):
    p = path(name, base=base)
    os.makedirs(os.path.dirname(p) or ".", exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=indent)
    return p


def parse_screen_name(url_or_sn):
    """https://vk.com/example -> example; @example -> example; vk.com/example?ref=x -> example."""
    s = str(url_or_sn).strip()
    s = re.sub(r"^@+", "", s)
    m = re.search(r"vk\.com/([^/?#\s]+)", s)
    if m:
        sn = m.group(1)
        if sn in ("wall", "video", "photo", "app", "club"):
            return None
        return sn
    if re.fullmatch(r"[A-Za-z0-9._]{2,64}", s):
        return s
    return None


# ---------------------------------------------------------------- classification
CLIP_INNER_TYPES = ("short_video", "clip")

GIVEAWAY_KEYWORDS = re.compile(
    r"(розыгрыш|конкурс|приз|победител|разыгрыва|giveaway|дарим бесплатно|в качестве приза)", re.I)
GIVEAWAY_MECHANIC = re.compile(
    r"(подписк|лайк|репост|комментари|участн|услов|до \d|итога|рандом|счастливчик|"
    r"выберем|определим|приз)", re.I)


def attachment_clip(att):
    """Возвращает dict с данными клипа, если вложение — VK Клип, иначе None.

    Правила: внешний attachments[].type == 'clip' | 'short_video';
    внутренний attachments[].video.type in ('short_video','clip');
    если внутренний type отсутствует — нужен video.get (возвращается {'needs_check': True,...}).
    Внешний type == 'video' сам по себе НЕ делает вложение обычным видео.
    """
    t = att.get("type")
    if t in ("clip", "short_video"):
        inner = att.get("clip") or att.get("short_video") or att.get("video") or {}
        return dict(inner) or {"needs_check": False}
    if t == "video":
        v = att.get("video") or {}
        it = v.get("type")
        if it in CLIP_INNER_TYPES:
            return dict(v)
        if it is None:
            return {"needs_check": True, **v}
        return None
    return None


def classify_post(text, attachments):
    """Назначает ровно один основной тип поста + флаги poll/giveaway.

    Возвращает (main_type, has_poll, is_giveaway, photos, videos, clips, carousel).
    Приоритет: Клип > Видео > Карусель (carousel-вложение или >=2 фото) > Картинка > Текстовый пост.
    """
    has_poll = False
    photos, videos, clips = [], [], []
    carousel = False
    for a in attachments or []:
        t = a.get("type")
        if t == "photo":
            photos.append(a.get("photo") or {})
        elif t == "photos_list":
            pl = a.get("photos_list") or []
            if len(pl) >= 2:
                carousel = True
            photos.extend(pl)
        elif t == "album":
            photos.append(a.get("album") or {})
        elif t == "carousel":
            carousel = True
            for card in (a.get("carousel") or {}).get("cards", []) or []:
                ph = card.get("photo")
                if ph:
                    photos.append(ph)
        elif t == "poll":
            has_poll = True
        elif t in ("video", "clip", "short_video"):
            c = attachment_clip(a)
            if c:
                clips.append(c)
            else:
                videos.append(a.get("video") or {})
    n = len(photos)
    if clips:
        main = "Клип"
    elif videos:
        main = "Видео"
    elif carousel and n >= 2:
        main = "Карусель"
    elif n >= 2:
        main = "Карусель"
    elif n == 1:
        main = "Картинка"
    else:
        main = "Текстовый пост"
    txt = text or ""
    giveaway = bool(GIVEAWAY_KEYWORDS.search(txt)) and bool(GIVEAWAY_MECHANIC.search(txt))
    return main, has_poll, giveaway, photos, videos, clips, carousel


def best_photo_url(photo, target=1600):
    """Выбирает вариант размера фото, ближайший к ~1600 по максимальной стороне."""
    sizes = photo.get("sizes") or []
    cand = [s for s in sizes if s.get("url")]
    if not cand:
        return None, None
    cand.sort(key=lambda s: abs(max(s.get("width") or 0, s.get("height") or 0) - target))
    s = cand[0]
    return s["url"], (s.get("width"), s.get("height"))


def compute_er(likes, comments, reposts, views):
    """ER = (лайки + комментарии + репосты) / просмотры; только при views > 0."""
    if not views or views <= 0:
        return None
    return (likes + comments + reposts) / views


def benchmark_of(er_values):
    """Индивидуальный бенчмарк сообщества = среднее всех валидных ER за окно."""
    vals = [e for e in er_values if e is not None]
    if not vals:
        return None
    return sum(vals) / len(vals)


def fmt_msk(ts):
    return datetime.fromtimestamp(int(ts), MSK).strftime("%Y-%m-%d %H:%M")

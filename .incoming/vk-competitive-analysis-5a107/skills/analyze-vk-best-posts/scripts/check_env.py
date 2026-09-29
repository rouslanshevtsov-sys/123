#!/usr/bin/env python3
"""Этап 0: проверка входного competitor_set.json и подготовка медиасреды.

Останавливает работу (exit code != 0) и печатает конкретную причину, если:
- файл отсутствует / повреждён (невалидный JSON);
- нет записей конкурентов;
- у записи нет ни ссылки на сообщество VK, ни screen_name/id;
- тип конкурента вне допустимого набора;
- отсутствуют обязательные медиазависимости (requests, PIL, openpyxl);
- Whisper-библиотека отсутствует (предупреждение; блокирует только при --require-whisper).

Токен берётся из переменной окружения VK_TOKEN или из файла .token в рабочей
директории. Никогда не печатает содержимое токена.

Использование:
    python check_env.py [--workdir DIR] [--competitor-set FILE] [--require-whisper]
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import VALID_TYPES, parse_screen_name, path  # noqa: E402

REQUIRED_PKGS = ["requests", "PIL", "openpyxl"]
WHISPER_PKGS = [["faster_whisper"], ["whisper"]]  # faster-whisper или openai-whisper


def fail(msg):
    print(f"STOP: {msg}")
    return 1


def ok(msg):
    print(f"OK: {msg}")


def check_imports(require_whisper):
    missing = []
    for mod in REQUIRED_PKGS:
        try:
            __import__(mod)
        except Exception:
            missing.append(mod)
    if missing:
        return fail("Отсутствуют обязательные медиазависимости: "
                    + ", ".join(missing)
                    + ". Установи: pip install requests pillow openpyxl")
    whisper_found = None
    for candidates in WHISPER_PKGS:
        for mod in candidates:
            try:
                __import__(mod)
                whisper_found = mod
                break
            except Exception:
                continue
        if whisper_found:
            break
    if not whisper_found:
        msg = ("Whisper-библиотека не найдена (faster-whisper/openai-whisper). "
               "Расшифровка клипов будет невозможна.")
        if require_whisper:
            return fail(msg)
        print(f"WARN: {msg}")
    else:
        ok(f"Whisper доступна: {whisper_found}")
    ok("Медиазависимости проверены: requests, PIL, openpyxl")
    return 0


def load_competitor_set(fp):
    if not os.path.exists(fp):
        return None, f"Входной файл не найден: {os.path.basename(fp)}"
    try:
        with open(fp, encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        return None, f"Повреждённый JSON в {os.path.basename(fp)}: {e}"
    items = data.get("competitors") if isinstance(data, dict) else data
    if not isinstance(items, list) or not items:
        return None, "В файле нет списка конкурентов (ключ competitors[] пуст или отсутствует)"
    return items, None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workdir", default=None)
    ap.add_argument("--competitor-set", default="competitor_set.json")
    ap.add_argument("--require-whisper", action="store_true")
    args = ap.parse_args()
    if args.workdir:
        os.environ["VK_WORK_DIR"] = args.workdir

    rc = check_imports(args.require_whisper)
    if rc:
        return rc

    fp = path(args.competitor_set)
    items, err = load_competitor_set(fp)
    if err:
        return fail(err)

    bad = []
    resolved = []
    for i, c in enumerate(items):
        if not isinstance(c, dict):
            bad.append(f"запись #{i}: не объект")
            continue
        name = c.get("name") or c.get("title")
        url = c.get("vk_url") or c.get("url") or c.get("screen_name") or c.get("link")
        sn = parse_screen_name(url) if url else None
        gid = c.get("group_id") or c.get("vk_id")
        if not sn and not gid:
            bad.append(f"запись #{i} ({name or 'без имени'}): нет ссылки/идентификатора сообщества VK")
            continue
        ctype = c.get("type")
        if ctype not in VALID_TYPES:
            bad.append(f"запись #{i} ({name}): недопустимый тип '{ctype}' "
                       f"(ожидается direct|indirect|attention)")
            continue
        if not name:
            bad.append(f"запись #{i}: отсутствует название")
            continue
        resolved.append({"name": name, "type": ctype, "screen_name": sn,
                         "group_id": gid, "url": url if isinstance(url, str) else None})

    if bad:
        return fail("competitor_set.json не прошёл проверку:\n  - " + "\n  - ".join(bad))

    ok(f"competitor_set.json валиден: {len(resolved)} сообществ")
    save_path = path("competitors_resolved.json")
    with open(save_path, "w", encoding="utf-8") as f:
        json.dump(resolved, f, ensure_ascii=False, indent=1)
    ok(f"Список зафиксирован: {os.path.basename(save_path)} "
       "(новые конкуренты в течение анализа не добавляются)")

    token_present = bool(os.environ.get("VK_TOKEN")) or os.path.exists(path(".token"))
    if token_present:
        ok("Токен VK API доступен (VK_TOKEN или .token в рабочей директории)")
    else:
        return fail("Токен VK API не найден: задай переменную окружения VK_TOKEN "
                    "или файл .token в рабочей директории")
    return 0


if __name__ == "__main__":
    sys.exit(main())

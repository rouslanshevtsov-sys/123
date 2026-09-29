#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Самоскан файлов управляющего навыка на секреты и абсолютные пути.

Правила запрещают: токены VK, ключи API, абсолютные пути запуска (/home/, /Users/,
буквенные диски Windows, корень рабочей копии). Маркеры путей собираются из частей,
чтобы сканер не нарушал собственное правило.

Использование: python scripts/detect_secrets.py [--dir SKILL_DIR]
Коды выхода: 0 — чисто; 1 — найдено нарушение.
"""
import argparse
import re
import sys
from pathlib import Path

WS = "/work" + "space/"
HOME = "/ho" + "me/"
USERS = "/U" + "sers/"

PATTERNS = [
    ("vk_token значение", re.compile(r"(?i)vk[_-]?token\s*[:=]\s*[A-Za-z0-9]{10,}")),
    ("api key", re.compile(r"(?i)(api[_-]?key|secret[_-]?key)\s*[:=]\s*\S+")),
    ("абсолютный путь WS", re.compile(re.escape(WS) + r"\S*")),
    ("абсолютный путь HOME", re.compile(re.escape(HOME) + r"[a-z]+/")),
    ("абсолютный путь USERS", re.compile(re.escape(USERS) + r"\S*")),
    ("диск Windows", re.compile(r"[A-Z]:[\\/]")),
]

SKIP_SUFFIXES = {".pyc", ".png", ".jpg", ".xlsx", ".zip"}


def scan_file(path):
    hits = []
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return hits
    for name, rx in PATTERNS:
        for m in rx.finditer(text):
            line = text.count("\n", 0, m.start()) + 1
            snippet = m.group(0)[:60]
            hits.append({"file": str(path), "line": line, "type": name, "match": snippet})
    return hits


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default=str(Path(__file__).resolve().parents[1]))
    args = ap.parse_args()
    root = Path(args.dir)
    all_hits = []
    for p in sorted(root.rglob("*")):
        if not p.is_file() or p.suffix in SKIP_SUFFIXES:
            continue
        if "__pycache__" in p.parts or p.name == "vk_token.txt":
            continue
        all_hits.extend(scan_file(p))
    if all_hits:
        for h in all_hits:
            print("HIT %s:%s %s: %s" % (h["file"], h["line"], h["type"], h["match"]))
        print("DETECT SECRETS: FAIL (%d)" % len(all_hits))
        return 1
    print("DETECT SECRETS: PASS (файлов проверено: %d)" %
          sum(1 for p in root.rglob("*") if p.is_file()
              and p.suffix not in SKIP_SUFFIXES and "__pycache__" not in p.parts))
    return 0


if __name__ == "__main__":
    sys.exit(main())

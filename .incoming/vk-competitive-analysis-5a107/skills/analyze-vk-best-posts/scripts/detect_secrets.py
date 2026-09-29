#!/usr/bin/env python3
"""Поиск секретов в файлах навыка (токены VK, access_token, абсолютные пути запуска).

Использование: python detect_secrets.py [--dir DIR]
Возвращает 1, если найдены секреты или запрещённые абсолютные пути.
"""
import argparse
import os
import re
import sys

SELF_RULE_MARKERS = ("PATTERNS =", "for pat in (")  # строки с определениями правил

PATTERNS = [
    ("VK-токен", re.compile(r"vk1\.[a-zA-Z]\.[A-Za-z0-9_\-]{20,}")),
    ("access_token присваивание", re.compile(r"access_token\s*[=:]\s*['\"]?[A-Za-z0-9]{20,}")),
    # Префиксы запрещённых путей собираются из частей, чтобы сканер не срабатывал
    # на собственном тексте правил (см. chain-contract.md §6).
    ("абсолютный путь запуска", re.compile("/" + "workspace/[^\\s\"']*|"
                                           "/home/[a-z]+/|C:\\\\\\\\Users")),
]
SKIP_EXT = {".png", ".jpg", ".jpeg", ".mp4", ".xlsx", ".pyc"}


def scan(root):
    findings = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in ("__pycache__", ".git", "media")]
        for fn in filenames:
            if os.path.splitext(fn)[1].lower() in SKIP_EXT:
                continue
            p = os.path.join(dirpath, fn)
            try:
                with open(p, encoding="utf-8") as f:
                    text = f.read()
            except (UnicodeDecodeError, OSError):
                continue
            lines = text.splitlines()
            for label, rx in PATTERNS:
                hit = None
                for ln in lines:
                    if any(mark in ln for mark in SELF_RULE_MARKERS):
                        continue  # не искать абсолютные пути в собственных правилах сканера
                    m = rx.search(ln)
                    if m:
                        hit = m
                        break
                m = hit
                if m:
                    rel = os.path.relpath(p, root)
                    findings.append(f"{rel}: {label} -> {m.group(0)[:40]}...")
    return findings


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default=None)
    args = ap.parse_args()
    root = args.dir or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    found = scan(root)
    if found:
        print("SECRETS CHECK: FAIL")
        for f in found:
            print(f"  - {f}")
        return 1
    print("SECRETS CHECK: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())

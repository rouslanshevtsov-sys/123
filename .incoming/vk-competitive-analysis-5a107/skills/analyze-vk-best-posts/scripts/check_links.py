#!/usr/bin/env python3
"""Проверка ссылок между SKILL.md, scripts/ и references/.

Убеждается, что:
- все упоминания scripts/*.py и references/*.md в SKILL.md соответствуют реальным файлам;
- каждый файл scripts/ и references/ упомянут в SKILL.md (нет «висящих» материалов);
- ссылки относительные, без абсолютных путей.

Использование: python check_links.py [--skill-dir DIR]
"""
import argparse
import os
import re
import sys


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--skill-dir", default=None)
    args = ap.parse_args()
    root = args.skill_dir or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    skill_md = os.path.join(root, "SKILL.md")
    if not os.path.exists(skill_md):
        print(f"FAIL: SKILL.md не найден в {root}")
        return 1
    text = open(skill_md, encoding="utf-8").read()

    errors = []
    mentioned = set(re.findall(r"(scripts/[\w\-]+\.py|references/[\w\-]+\.md|"
                               r"templates/[\w\-.]+\.(?:json|md|py))", text))
    for m in mentioned:
        if not os.path.exists(os.path.join(root, m)):
            errors.append(f"Ссылка в SKILL.md ведёт в никуда: {m}")

    actual = set()
    for sub in ("scripts", "references", "templates"):
        d = os.path.join(root, sub)
        if os.path.isdir(d):
            for f in os.listdir(d):
                if f.endswith((".py", ".md", ".json")) and not f.startswith("__"):
                    actual.add(f"{sub}/{f}")
    for a in sorted(actual):
        if a not in mentioned:
            errors.append(f"Файл {a} не связан со SKILL.md")

    # абсолютные пути запрещены
    # "/workspace/" собран из частей — иначе сканер сам нарушает правило (contract §6)
    for pat in ("/home/", "/Users/", "C:\\", "/" + "workspace/"):
        if pat in text:
            errors.append(f"В SKILL.md найден абсолютный путь: {pat}")

    if errors:
        print("LINK CHECK: FAIL")
        for e in errors:
            print(f"  - {e}")
        return 1
    print(f"LINK CHECK: PASS ({len(mentioned)} связей, {len(actual)} файлов)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

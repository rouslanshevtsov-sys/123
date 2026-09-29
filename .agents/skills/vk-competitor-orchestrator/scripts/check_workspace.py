#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Проверка структуры рабочего пространства и наличия навыков цепочки.

Использование: python scripts/check_workspace.py [--root DIR]
Коды выхода: 0 — OK; 1 — структура/навыки не соответствуют белому списку.
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from orchestrate_lib import ALLOWED_SKILLS, check_workspace  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=None)
    args = ap.parse_args()
    root = Path(args.root) if args.root else Path.cwd()
    errors = check_workspace(root)
    report = {"root": str(root), "allowedSkills": ALLOWED_SKILLS,
              "errors": errors, "status": "pass" if not errors else "fail"}
    print(json.dumps(report, ensure_ascii=False, indent=1))
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())

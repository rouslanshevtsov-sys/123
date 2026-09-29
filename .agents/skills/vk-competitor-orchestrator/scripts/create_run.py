#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Создание уникального каталога запуска runs/YYYY-MM-DD/<run-id>/.

Использование: python scripts/create_run.py --stage posts [--root DIR]
Вывод (JSON): runId, dir (относительный путь), createdAt.
Коды выхода: 0 — создан; 1 — ошибка (например, имя уже занято).
"""
import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from orchestrate_lib import MSK, STAGES, new_run_dir  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", required=True, choices=sorted(STAGES))
    ap.add_argument("--root", default=None)
    args = ap.parse_args()
    root = Path(args.root) if args.root else Path.cwd()
    rd, run_id, date = new_run_dir(root, args.stage)
    now = datetime.now(MSK).isoformat(timespec="seconds")
    print(json.dumps({"runId": run_id, "stage": args.stage,
                      "dir": "%s/%s/%s" % ("runs", date, run_id),
                      "createdAt": now}, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())

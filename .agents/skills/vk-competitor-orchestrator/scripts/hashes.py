#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Расчёт sha256 входных файлов (для handoff и проверки переиспользования).

Использование: python scripts/hashes.py FILE [FILE ...]
Вывод (JSON): {"имя": "sha256:<hex>", ...}; отсутствующий файл — "missing".
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from orchestrate_lib import input_hashes  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="+")
    args = ap.parse_args()
    print(json.dumps(input_hashes([Path(f) for f in args.files]),
                     ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())

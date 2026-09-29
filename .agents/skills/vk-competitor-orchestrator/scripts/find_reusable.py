#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Поиск последнего валидного результата этапа и решение о переиспользовании.

Использование:
    python scripts/find_reusable.py --stage posts [--root DIR]
Коды выхода: 0 — найден валидный результат (reuse); 3 — переиспользование невозможно
(запускайте новый этап). Вывод — compact JSON с runId/артефактами/хэшами.
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from orchestrate_lib import (RUNS_DIRNAME, STAGES, find_latest_valid,  # noqa: E402
                             input_hashes)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", required=True, choices=sorted(STAGES))
    ap.add_argument("--root", default=None)
    args = ap.parse_args()
    root = Path(args.root) if args.root else Path.cwd()
    inputs = [root / n for n in STAGES[args.stage]["inputs"]]
    ih = input_hashes(inputs)
    run_id = find_latest_valid(root, args.stage, ih)
    result = {"stage": args.stage, "inputHashes": ih,
              "reusableRunId": run_id,
              "decision": "reuse" if run_id else "run-new"}
    print(json.dumps(result, ensure_ascii=False, indent=1))
    return 0 if run_id else 3


if __name__ == "__main__":
    sys.exit(main())

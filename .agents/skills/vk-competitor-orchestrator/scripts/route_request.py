#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Разбор запроса пользователя и построение плана этапов (compact JSON).

Использование:
    python scripts/route_request.py --text "<запрос>" [--root DIR] [--period-hours N]
Коды выхода: 0 — план построен и можно стартовать; 2 — остановка (план.stop).
План записывается в runs/route-latest.json (компактный handoff для агента).
"""
import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from orchestrate_lib import (RUNS_DIRNAME, classify_intent, route,  # noqa: E402
                             workspace_root, MSK)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--text", required=True)
    ap.add_argument("--root", default=None)
    ap.add_argument("--period-hours", type=int, default=7 * 24)
    args = ap.parse_args()
    root = Path(args.root) if args.root else workspace_root()
    intent = classify_intent(args.text)
    plan = route(intent, root, period_hours=args.period_hours)
    plan["requestText"] = args.text[:200]
    plan["createdAt"] = datetime.now(MSK).isoformat(timespec="seconds")
    out_dir = root / RUNS_DIRNAME
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "route-latest.json").write_text(
        json.dumps(plan, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(plan, ensure_ascii=False, indent=1))
    return 2 if plan["stop"] else 0


if __name__ == "__main__":
    sys.exit(main())

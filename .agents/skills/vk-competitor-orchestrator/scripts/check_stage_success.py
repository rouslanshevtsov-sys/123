#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Проверка успешности этапа перед запуском следующего (stop condition).

Использование: python scripts/check_stage_success.py --stage posts [--root DIR]
Коды выхода: 0 — этап завершён успешно, следующий разрешён;
1 — ошибка/непройденная проверка; 2 — требует подтверждения пользователя.
Успех = последняя запись runs/index.json этого этапа со status="pass"
(pass записывается run_stage.py только при пройденном нативном gate навыка).
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from orchestrate_lib import RUNS_DIRNAME, STAGES  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", required=True, choices=sorted(STAGES))
    ap.add_argument("--root", default=None)
    args = ap.parse_args()
    root = Path(args.root) if args.root else Path.cwd()
    idx = root / RUNS_DIRNAME / "index.json"
    runs = []
    if idx.exists():
        try:
            runs = json.loads(idx.read_text(encoding="utf-8")).get("runs", [])
        except (ValueError, OSError):
            runs = []
    stage_runs = [r for r in runs if r.get("stage") == args.stage]
    last = sorted(stage_runs, key=lambda x: x.get("createdAt", ""))[-1] if stage_runs else None
    if last is None:
        print(json.dumps({"stage": args.stage, "success": False,
                          "reason": "нет ни одного запуска этапа"}, ensure_ascii=False))
        return 1
    status = last.get("status")
    if status == "pass":
        code = 0
    elif status in ("pending", "blocked-needs-confirmation"):
        code = 2
    else:
        code = 1
    print(json.dumps({"stage": args.stage, "runId": last.get("runId"),
                      "status": status, "success": status == "pass"},
                     ensure_ascii=False))
    return code


if __name__ == "__main__":
    sys.exit(main())

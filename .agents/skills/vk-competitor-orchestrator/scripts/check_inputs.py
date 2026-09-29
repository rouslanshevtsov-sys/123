#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Проверка обязательных входов этапа перед запуском.

Использование:
    python scripts/check_inputs.py --stage posts [--root DIR]
Коды выхода: 0 — входы готовы; 2 — остановка (не запускать этап).
Для этапа interview входов нет — всегда OK (интервью и есть способ их создать).
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from orchestrate_lib import STAGES, check_required_inputs, context_gate  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", required=True, choices=sorted(STAGES))
    ap.add_argument("--root", default=None)
    args = ap.parse_args()
    root = Path(args.root) if args.root else Path.cwd()
    missing = check_required_inputs(root, args.stage)
    reasons = ["Отсутствует или пуст вход этапа: %s" % m for m in missing]
    # Скрытый порог для этапов после интервью: контекст обязан быть confirmed.
    if args.stage != "interview":
        ok, reason = context_gate(root)
        if not ok:
            reasons.append(reason)
    # Деградированный медиарежим предыдущего этапа требует явного согласия.
    # Признак — gate_status.json каталога запуска этапа posts (см. run_stage.py):
    # media_gate PASS только с --allow-degraded => degraded=True.
    if args.stage == "report":
        degraded_seen = False
        for gs in sorted(root.glob("runs/*/*/gate_status.json")):
            try:
                g = json.loads(gs.read_text(encoding="utf-8"))
            except (ValueError, OSError):
                continue
            if g.get("stage") == "posts" and g.get("degraded"):
                degraded_seen = True
        if degraded_seen:
            consent_file = root / "degraded_media_consent.json"
            consent = None
            if consent_file.exists():
                try:
                    consent = json.loads(consent_file.read_text(encoding="utf-8"))
                except (ValueError, OSError):
                    consent = None
            if not (isinstance(consent, dict) and consent.get("userConsent") is True):
                reasons.append("Деградированный медиарежим этапа posts без явного "
                               "согласия пользователя (degraded_media_consent.json).")
    report = {"stage": args.stage, "missingInputs": missing,
              "ready": not reasons, "reasons": reasons}
    print(json.dumps(report, ensure_ascii=False, indent=1))
    return 0 if report["ready"] else 2


if __name__ == "__main__":
    sys.exit(main())

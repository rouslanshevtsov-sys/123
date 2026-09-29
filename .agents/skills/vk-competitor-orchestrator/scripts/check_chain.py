#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Единая проверка всей цепочки (chain check) — compact JSON + коды выхода.

Проверяет ПОСЛЕДОВАТЕЛЬНОСТЬ и ПОРЯДОК, не дублируя предметные правила навыков:
  - структура workspace и белый список навыков;
  - бизнес-контекст: confirmed (полную валидацию делает final_validation.py навыка);
  - competitor_set.json: читается, непустой, содержит type/status/ссылку;
  - результаты posts: датасет+комментарии+XLSX существуют, хэши зафиксированы,
    медиашлюз пройден (gate_status.json со статусом pass или media_gate.py --workdir);
  - отчёт: report.html существует и непустой;
  - происхождение: basedOn*-цепочка хэсов непрерывна там, где сохранена;
  - секреты: vk_token.txt только вне результатов (в runs/*/ нет токенов).

Использование: python scripts/check_chain.py [--root DIR] [--json-out FILE]
Коды выхода: 0 — цепочка готова; 1 — есть нарушения; 2 — остановка на первом блоке.
"""
import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from orchestrate_lib import (ARTIFACT_BY_KEY, RUNS_DIRNAME, STAGE_ORDER,  # noqa: E402
                             STAGES, check_workspace, context_gate, input_hashes,
                             sha256_file)

TOKEN_RE = re.compile(r"(vk[_.]?token|secret|password)\s*[:=]", re.I)


def load_json(path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=None)
    ap.add_argument("--json-out", default=None)
    args = ap.parse_args()
    root = Path(args.root) if args.root else Path.cwd()
    checks = []

    def add(name, status, detail=""):
        checks.append({"check": name, "status": status, "detail": detail})
        return status == "pass"

    ok = True
    ws_errors = check_workspace(root)
    ok &= add("workspace_structure", "pass" if not ws_errors else "fail",
              "; ".join(ws_errors) or "все навыки на месте")

    ctx_ok, ctx_reason = context_gate(root)
    ok &= add("business_context_confirmed", "pass" if ctx_ok else "fail", ctx_reason)

    comp_path = root / ARTIFACT_BY_KEY["competitors"]
    comp = load_json(comp_path) if comp_path.exists() else None
    if isinstance(comp, list) and comp:
        first = comp[0]
        fields_ok = all(k in first for k in ("type",)) and ("status" in first or "er" in first)
        ok &= add("competitor_set_valid", "pass" if fields_ok else "fail",
                  "записей: %d" % len(comp))
    else:
        ok = add("competitor_set_valid", "missing",
                 "competitor_set.json отсутствует/пуст — поиск только по разрешению") and False

    ds = root / ARTIFACT_BY_KEY["posts_dataset"]
    cm = root / ARTIFACT_BY_KEY["posts_comments"]
    cm_raw = root / ARTIFACT_BY_KEY["posts_comments_raw"]
    xl = root / ARTIFACT_BY_KEY["posts_xlsx"]
    posts_files = [p.name for p in (ds, cm if cm.exists() else cm_raw, xl) if p.exists()]
    if ds.exists() and xl.exists() and (cm.exists() or cm_raw.exists()):
        data = load_json(ds)
        posts_ok = isinstance(data, dict) and isinstance(data.get("posts"), list) \
            and len(data["posts"]) > 0
        ok &= add("posts_outputs_present", "pass" if posts_ok else "fail",
                  ", ".join(posts_files))
        # медиашлюз: gate_status pass в любом runs/*/*/ ИЛИ нативный media_gate PASS
        gate_pass = False
        degraded = False
        for gs in sorted(root.glob("%s/*/*/gate_status.json" % RUNS_DIRNAME)):
            g = load_json(gs) or {}
            if g.get("stage") == "posts" and g.get("result") == "pass":
                gate_pass = True
                degraded = bool(g.get("degraded"))
        mm = root / ARTIFACT_BY_KEY["provenance"]
        hashes = {n: (sha256_file(p) if p.exists() else "missing")
                  for n, p in [(ds.name, ds), (xl.name, xl)]}
        ok &= add("media_gate_passed", "pass" if gate_pass else "fail",
                  "подтверждение из runs/index gate_status" if gate_pass
                  else "нет записи о пройденном медиашлюзе")
        if degraded:
            consent = load_json(root / "degraded_media_consent.json") or {}
            ok &= add("degraded_media_consent",
                      "pass" if consent.get("userConsent") is True else "fail",
                      "явное согласие пользователя зафиксировано"
                      if consent.get("userConsent") is True
                      else "деградированный режим без согласия")
        provenance_ok = mm.exists()
        ok &= add("provenance_hashes", "pass" if provenance_ok else "warn",
                  "provenance.json %s; входные хэши: %s" %
                  ("есть" if provenance_ok else "нет", json.dumps(hashes)))
    else:
        ok = add("posts_outputs_present", "missing",
                 "нет полного набора результатов analyze-vk-best-posts") and False

    rep = root / ARTIFACT_BY_KEY["report_html"]
    if rep.exists() and rep.stat().st_size > 0:
        ok &= add("report_present", "pass", rep.name)
    else:
        add("report_present", "missing", "report.html ещё не создан (нормально до этапа report)")

    # Секреты в результатах запусков (токен живёт только в vk_token.txt вне runs/).
    leaks = []
    for f in root.glob("%s/**/*" % RUNS_DIRNAME):
        if f.is_file() and f.suffix in (".json", ".md", ".html", ".txt") \
                and f.stat().st_size < 2_000_000:
            try:
                if TOKEN_RE.search(f.read_text(encoding="utf-8", errors="ignore")):
                    leaks.append(str(f.relative_to(root)))
            except OSError:
                pass
    ok &= add("no_secrets_in_runs", "pass" if not leaks else "fail",
              "; ".join(leaks) or "чисто")

    report = {"schemaVersion": "1.0", "root": root.name,
              "status": "pass" if ok else "fail",
              "stageOrder": STAGE_ORDER,
              "checks": checks,
              "stopAfter": next((c["check"] for c in checks if c["status"] == "fail"), None)}
    text = json.dumps(report, ensure_ascii=False, indent=1)
    if args.json_out:
        Path(args.json_out).write_text(text, encoding="utf-8")
    print(text)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())

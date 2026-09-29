#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Запуск этапа и его gate-проверка нативным валидатором навыка.

Управляющий агент НЕ выполняет предметную работу этапа — он только:
  1) проверяет входы (check_inputs), 2) создаёт уникальный каталог запуска,
  3) вызывает нативной скрипт навыка (agent-driven этапы помечены как handoff),
  4) запускает gate-валидатор навыка над результатами, 5) пишет stage_status.json,
     gate_status.json и запись в runs/index.json (статус pass — только при gate OK).

Использование:
    python scripts/run_stage.py --stage posts --run-dir DIR [--root DIR]
        [--input competitor_set.json=PATH ...] [--allow-degraded]
Коды выхода: 0 — gate PASS; 1 — gate FAIL (следующий этап запрещён);
2 — остановка до запуска (входы/пороги не пройдены).
"""
import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from orchestrate_lib import (MSK, RUNS_DIRNAME, SKILLS_DIRNAME, STAGES,  # noqa: E402
                             ARTIFACT_BY_KEY, check_required_inputs, context_gate,
                             input_hashes, model_for_stage, load_policy,
                             new_run_dir, write_index_entry, workspace_root)

SKILL_ROOT = Path(__file__).resolve().parents[1]


def is_agent_driven(stage):
    """Этапы, где часть работы делает языковая модель по SKILL.md навыка.
    Для них run_stage фиксирует handoff и требует явного подтверждения завершения."""
    return stage in ("interview", "competitors", "posts", "report")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", required=True, choices=sorted(STAGES))
    ap.add_argument("--run-dir", default=None, help="каталог запуска (или создать новый)")
    ap.add_argument("--root", default=None)
    ap.add_argument("--first-complex-analysis", action="store_true",
                    help="первый сложный анализ рынка (policy analysis_first_complex)")
    ap.add_argument("--confirm-complete", action="store_true",
                    help="подтверждение, что agent-driven этап завершён навыком")
    ap.add_argument("--allow-degraded", action="store_true",
                    help="явное согласие пользователя на деградированный медиашлюз "
                         "(только posts; передаётся нативному media_gate.py)")
    args = ap.parse_args()
    root = Path(args.root) if args.root else Path.cwd()
    stage = args.stage
    spec = STAGES[stage]

    # 1. Пороги входа.
    missing = check_required_inputs(root, stage)
    if missing:
        print("STOP: отсутствуют входы этапа: %s" % ", ".join(missing))
        return 2
    if stage != "interview":
        ok, reason = context_gate(root)
        if not ok:
            print("STOP: %s" % reason)
            return 2

    # 2. Каталог запуска (уникальный, без перезаписи).
    if args.run_dir:
        rd = Path(args.run_dir)
        if not rd.is_dir():
            print("STOP: каталог запуска не найден: %s" % rd)
            return 2
        run_id = rd.name
        date = rd.parent.name
    else:
        rd, run_id, date = new_run_dir(root, stage)

    policy = load_policy(SKILL_ROOT)
    model = model_for_stage(policy, stage, args.first_complex_analysis)

    # 3. Handoff compact JSON: пути+хэши входов, артефакты, модель. НЕ содержимое файлов.
    inputs = {n: str(root / n) for n in spec["inputs"]}
    ih = input_hashes([Path(p) for p in inputs.values()])
    handoff = {"schemaVersion": "1.0", "stage": stage, "skill": spec["skill"],
               "runId": run_id, "model": model, "inputPaths": inputs,
               "inputHashes": ih, "expectedOutputs": spec["outputs"],
               "agentDriven": is_agent_driven(stage)}
    (rd / "handoff.json").write_text(json.dumps(handoff, ensure_ascii=False, indent=1),
                                     encoding="utf-8")

    # 4. Gate-проверка нативным валидатором навыка (единственный источник правил).
    ws = workspace_root(root)
    gate_script = root_skill_script(ws, spec["skill"], spec["gate"]["script"])
    artifacts_present = [a for a in spec["outputs"] if (rd / a).exists()]
    gate_status = {"stage": stage, "runId": run_id, "degraded": False,
                   "returncode": None, "checkedAt": datetime.now(MSK).isoformat(timespec="seconds")}
    if not artifacts_present:
        gate_status.update({"result": "pending-agent-work",
                            "note": "Артефакты этапа ещё не созданы; навык должен выполнить "
                                    "предметную работу и вызвать run_stage повторно "
                                    "с --run-dir и --confirm-complete."})
        status = "pending"
    elif not args.confirm_complete:
        gate_status.update({"result": "needs-confirmation",
                            "note": "Этап с участием модели требует подтверждения завершения "
                                    "(--confirm-complete) перед gate-проверкой."})
        status = "blocked-needs-confirmation"
    elif gate_script is None:
        gate_status.update({"result": "fail", "note": "Gate-скрипт навыка не найден"})
        status = "fail"
    else:
        cmd = [sys.executable, str(gate_script)] + resolve_gate_args(
            spec["gate"]["args"], rd, root, run_id)
        if args.allow_degraded and stage == "posts":
            cmd.append("--allow-degraded")
        proc = subprocess.run(cmd, cwd=str(rd), capture_output=True, text=True)
        out = proc.stdout + proc.stderr
        passed = proc.returncode == 0
        # деградация = gate прошёл только благодаря согласию (в выводе есть отметка навыка)
        degraded = bool(args.allow_degraded and passed and stage == "posts"
                        and "разрешён явным согласием" in out)
        gate_status.update({"result": "pass" if passed else "fail",
                            "returncode": proc.returncode,
                            "outputTail": out[-800:],
                            "degraded": degraded})
        status = "pass" if passed else "fail"

    (rd / "gate_status.json").write_text(json.dumps(gate_status, ensure_ascii=False, indent=1),
                                         encoding="utf-8")

    # 5. Индекс запусков: pass записывается только при пройденном gate.
    entry = {"runId": run_id, "date": date, "stage": stage, "skill": spec["skill"],
             "createdAt": gate_status["checkedAt"], "status": status,
             "inputHashes": ih, "artifacts": sorted(artifacts_present),
             "model": model}
    write_index_entry(root, entry)

    print(json.dumps({"runId": run_id, "dir": "%s/%s/%s" % (RUNS_DIRNAME, date, run_id),
                      "status": status, "gate": gate_status.get("result"),
                      "handoff": "handoff.json"}, ensure_ascii=False, indent=1))
    if status == "pass":
        return 0
    if status == "pending" or status == "blocked-needs-confirmation":
        return 2
    return 1


def root_skill_script(ws, skill_name, relpath):
    """Путь к gate-скрипту навыка: <workspace>/.agents/skills/<skill>/<relpath>."""
    script = Path(ws) / SKILLS_DIRNAME / skill_name / relpath
    return script if script.exists() else None


def resolve_gate_args(tmpl, rd, root, run_id):
    out = []
    for a in tmpl:
        a = a.replace("{run}", str(rd)).replace("{set}", str(rd / ARTIFACT_BY_KEY["competitors"]))\
             .replace("{excel}", str(next((rd / x for x in STAGES["competitors"]["outputs"]
                                           if x.endswith(".xlsx")), rd / "out.xlsx")))
        out.append(a)
    return out


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""
Сквозной тест цепочки навыков (интервью → конкуренты → посты → реакции).

Граничит с ответственностью навыка business-context-interview: проверяет, что
этап 1 корректно ПОДГОТОВИЛ передачу downstream-этапам по контракту
references/chain-contract.md:

  1. generate_card.py создаёт draft + provenance.json (compact summary);
  2. confirm_card.py переводит в confirmed, пересобирает MD из тех же данных,
     пересчитывает хэш и summary;
  3. final_validation.py (--dir) проходит целиком, включая hash_provenance;
  4. кэш load_cached_summary даёт HIT без пересборки и MISS после изменения контекста;
  5. require_confirmed_context пропускает confirmed и блокирует draft/dirty/missing;
  6. detect_secrets.py --dir не находит секретов; vk_token.txt игнорируется;
  7. chain_manifest.json собирается со всеми артефактами и хэшами.

Внешние действия (VK API, поиск) НЕ выполняются — вход синтетический.

Использование:
    python scripts/test_chain.py            # запуск из любой директории
Выход: 0 — все проверки пройдены.
"""

import json
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent          # .../scripts
SKILL_ROOT = HERE.parent                          # .../business-context-interview
sys.path.insert(0, str(HERE))

from common import (  # noqa: E402
    ARTIFACT_NAMES,
    canonical_hash,
    hash_of,
    file_sha256,
    load_json,
    save_json,
    detect_secrets_in_text,
    load_cached_summary,
    require_confirmed_context,
    build_summary,
)

SAMPLE_CONTEXT = {
    "status": "draft",
    "confirmationDate": None,
    "source": {"url": "https://vk.com/test_club", "accessible": True, "parseError": None},
    "business": {"name": "Тестовый клуб", "niche": "Онлайн-школы", "description": "Школа для кондиторов"},
    "products": {"main": ["Курс тортов"], "secondary": [], "producer": "Автор"},
    "audience": {"targetSegments": ["Начинающие кондиторы"]},
    "geography": {"regions": ["Россия"]},
    "channels": {"acquisition": ["VK"], "onlinePresence": ["https://vk.com/test_club"]},
    "competitors": {"known": ["Пекарня Про"], "classification": {"direct": "тот же продукт"}},
    "searchCriteria": {"searchQueries": ["курсы кондитера vk"], "count": 5},
    "gaps": [],
}

results = []


def check(name, ok, detail=""):
    results.append((name, ok, detail))
    print(("  ✓ " if ok else "  ✗ ") + name + (f" — {detail}" if detail and not ok else ""))


def run_script(script, args):
    return subprocess.run([sys.executable, str(SKILL_ROOT / "scripts" / script)] + args,
                          capture_output=True, text=True)


def main():
    print("=" * 60)
    print("СКВОЗНОЙ ТЕСТ ЦЕПОЧКИ (подготовка передачи downstream)")
    print("=" * 60)

    with tempfile.TemporaryDirectory() as tmp:
        run_dir = Path(tmp) / "Запуск_test"
        run_dir.mkdir()
        input_path = Path(tmp) / "input.json"
        save_json(input_path, SAMPLE_CONTEXT)

        # --- Этап 1: генерация draft ---
        r = run_script("generate_card.py", ["--output-dir", str(run_dir), "--data", str(input_path)])
        check("generate_card создаёт файлы", r.returncode == 0, r.stdout + r.stderr)
        ctx_p = run_dir / ARTIFACT_NAMES["context"]
        md_p = run_dir / ARTIFACT_NAMES["card"]
        prov_p = run_dir / ARTIFACT_NAMES["provenance"]
        check("draft: есть business_context.json + business_card.md + provenance.json",
              ctx_p.exists() and md_p.exists() and prov_p.exists())

        # до подтверждения порог должен блокировать downstream
        try:
            require_confirmed_context(ctx_p)
            blocked_pre = False
        except SystemExit:
            blocked_pre = True
        check("порог входа блокирует draft", blocked_pre)

        # --- подтверждение ---
        r = run_script("confirm_card.py", ["--input-dir", str(run_dir), "--date", "2026-09-29"])
        check("confirm_card проходит", r.returncode == 0, r.stdout + r.stderr)
        data = load_json(ctx_p)
        check("статус confirmed + дата", data["status"] == "confirmed" and data["confirmationDate"] == "2026-09-29")

        # --- единая итоговая проверка ---
        r = run_script("final_validation.py", ["--dir", str(run_dir)])
        check("final_validation --dir проходит", r.returncode == 0, r.stdout + r.stderr)

        # --- хэш происхождения ---
        stored = data["hashes"]["business_context.json"]
        recomputed = hash_of(data)
        check("канонический хэш воспроизводим", stored == recomputed)

        # --- кэш summary ---
        s1 = load_cached_summary(run_dir)
        mtime1 = prov_p.stat().st_mtime_ns
        s2 = load_cached_summary(run_dir)
        check("кэш summary: HIT без пересборки", s1 == s2 and prov_p.stat().st_mtime_ns == mtime1)
        data["business"]["name"] = "Тестовый клуб 2"
        data["hashes"]["business_context.json"] = hash_of(data)
        save_json(ctx_p, data)
        s3 = load_cached_summary(run_dir)
        check("кэш summary: MISS после изменения контекста", s3["businessName"] == "Тестовый клуб 2"
              and s3["contextHash"] == data["hashes"]["business_context.json"])
        # вернуть имя (чтобы синхронность MD/JSON не падала ниже — MD начинается с прежнего имени? нет:
        # префиксное правило «Тестовый клуб» — префикс «Тестовый клуб 2», расхождения нет)

        # --- порог входа пропускает confirmed ---
        try:
            require_confirmed_context(ctx_p)
            passed = True
        except SystemExit as e:
            passed = False
            print("    ", e)
        check("порог входа пропускает confirmed", passed)

        # --- отрицательные пороги ---
        dirty = dict(SAMPLE_CONTEXT)
        dirty.update({"status": "confirmed", "confirmationDate": "2026-09-29",
                      "business": {**SAMPLE_CONTEXT["business"],
                                   "description": "токен access_token=AbCdEfGhIjKlMnOpQrStUvWx"}})
        dirty_p = Path(tmp) / "dirty.json"
        save_json(dirty_p, dirty)
        try:
            require_confirmed_context(dirty_p)
            blocked_secret = False
        except SystemExit:
            blocked_secret = True
        check("порог входа блокирует контекст с секретом", blocked_secret)

        try:
            require_confirmed_context(Path(tmp) / "missing.json")
            blocked_missing = False
        except SystemExit:
            blocked_missing = True
        check("порог входа блокирует отсутствующий вход", blocked_missing)

        # --- секреты: чистая директория; vk_token.txt игнорируется сканером ---
        token_p = Path(tmp) / "scan" / "vk_token.txt"
        scan_dir = Path(tmp) / "scan"
        scan_dir.mkdir()
        for f in (ctx_p, md_p, prov_p):
            (scan_dir / f.name).write_bytes(f.read_bytes())
        r = run_script("detect_secrets.py", ["--dir", str(scan_dir)])
        check("detect_secrets --dir: чисто", r.returncode == 0, r.stdout + r.stderr)

        token_p.write_text("vk1.a.REALTOKENabc123DEF456", encoding="utf-8")
        r = run_script("detect_secrets.py", ["--dir", str(scan_dir)])
        check("detect_secrets --dir: легитимный vk_token.txt игнорируется", r.returncode == 0, r.stdout + r.stderr)
        token_p.unlink()

        leaky = scan_dir / "leak.txt"
        leaky.write_text("vk1.a.SECRETsecretSECRET", encoding="utf-8")
        r = run_script("detect_secrets.py", ["--dir", str(scan_dir)])
        check("detect_secrets --dir: находит секрет", r.returncode == 1)
        leaky.unlink()

        # --- имитация этапов 2–4 по контракту + манифест ---
        prov = load_json(prov_p)
        competitors = {
            "schemaVersion": "1.0",
            "basedOnContextHash": prov["contextHash"],
            "competitors": [{"name": "Пекарня Про", "vkUrl": "https://vk.com/pekarapro",
                             "type": "direct", "audience": 12000}],
        }
        comp_p = run_dir / ARTIFACT_NAMES["competitors"]
        save_json(comp_p, competitors)
        comp_hash = canonical_hash(competitors)

        posts = {
            "schemaVersion": "1.0",
            "basedOnCompetitorsHash": comp_hash,
            "posts": [{"postId": "-1_1", "competitorName": "Пекарня Про", "likes": 140,
                       "reposts": 12, "comments": 30, "views": 9000, "date": "2026-09-10"}],
        }
        posts_p = run_dir / ARTIFACT_NAMES["posts"]
        save_json(posts_p, posts)

        reactions = {"schemaVersion": "1.0",
                     "basedOnPostsHash": canonical_hash(posts),
                     "topFormats": [{"format": "рецепт", "avgLikes": 140}], "recommendations": []}
        react_p = run_dir / ARTIFACT_NAMES["reactions"]
        save_json(react_p, reactions)

        manifest = {"contractVersion": build_summary({}, None)["contractVersion"],
                    "runDir": str(run_dir.name), "chain": [
                        "business-context-interview", "competitor-analysis",
                        "best-posts-collection", "market-reaction-analysis"],
                    "artifacts": {}}
        for p in (ctx_p, md_p, comp_p, posts_p, react_p):
            entry = {"fileSha256": file_sha256(p)}
            if p.suffix == ".json":
                d = load_json(p)
                entry["canonicalHash"] = (d.get("hashes") or {}).get(p.name) or (
                    hash_of(d) if p == ctx_p else canonical_hash(d))
            manifest["artifacts"][p.name] = entry
        manifest_p = run_dir / ARTIFACT_NAMES["manifest"]
        save_json(manifest_p, manifest)

        m = load_json(manifest_p)
        hashes_ok = all(v["fileSha256"] == file_sha256(run_dir / k) for k, v in m["artifacts"].items())
        check("chain_manifest: хэши всех артефактов верны", hashes_ok)
        check("происхождение: basedOn*Hash образуют непрерывную цепочку",
              load_json(comp_p)["basedOnContextHash"] == load_json(prov_p)["contextHash"]
              and load_json(posts_p)["basedOnCompetitorsHash"] == canonical_hash(load_json(comp_p)))

        # --- обратная совместимость: документ v1.0 (без schemaVersion/hashes/validation) ---
        legacy = json.loads(json.dumps(SAMPLE_CONTEXT))
        legacy.update({"status": "confirmed", "confirmationDate": "2026-01-20"})
        legacy_p = Path(tmp) / "legacy.json"
        save_json(legacy_p, legacy)
        r = run_script("validate_json_schema.py", ["--file", str(legacy_p)])
        check("обратная совместимость: документ v1.0 проходит схему", r.returncode == 0, r.stdout + r.stderr)
        r = run_script("check_status.py", ["--file", str(legacy_p), "--expected", "confirmed"])
        check("обратная совместимость: статус v1.0 читается", r.returncode == 0, r.stdout + r.stderr)
        r = run_script("final_validation.py", ["--json", str(legacy_p)])
        check("обратная совместимость: final_validation --json работает без MD", r.returncode == 0, r.stdout + r.stderr)

    failed = [n for n, ok, _ in results if not ok]
    print("=" * 60)
    print(f"РЕЗУЛЬТАТ: {len(results) - len(failed)} пройдено, {len(failed)} не пройдено")
    if failed:
        print("Падения:", "; ".join(failed))
    print("=" * 60)
    return 1 if failed else 0


if __name__ == "__main__":
    exit(main())

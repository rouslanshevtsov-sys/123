#!/usr/bin/env python3
"""
Единый проверочный основной файл навыка business-context-interview.

Запускает все проверки за один проход (крупные файлы читаются минимально:
JSON — 1 раз, MD — 1 раз) и печатает компактный JSON-отчёт на stdout.

Использование:
    python scripts/final_validation.py --dir <папка_запуска>
    python scripts/final_validation.py --json <business_context.json> [--md <business_card.md>] [--expect-confirmed]

Выход: 0 — всё пройдено, 1 — есть падения.
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import (  # noqa: E402
    SCHEMA,
    load_json,
    validate_schema,
    check_required_values,
    detect_secrets_in_text,
    extract_data_from_markdown,
    check_sync_errors,
    hash_of,
)


def run_checks(json_path: Path, md_path: Path | None, expect_confirmed: bool) -> dict:
    report = {"checks": {}, "errors": []}

    def add(name, ok, detail=""):
        report["checks"][name] = "PASS" if ok else "FAIL"
        if not ok:
            report["errors"].append(f"{name}: {detail}")

    # 1. Загрузка JSON — единственный проход чтения крупного файла
    try:
        data = load_json(json_path)
    except FileNotFoundError:
        add("json_load", False, f"файл не найден: {json_path}")
        return report
    except ValueError as e:
        add("json_load", False, str(e))
        return report
    add("json_load", True)

    # 2. Схема
    schema_errors = validate_schema(data, SCHEMA)
    add("schema", not schema_errors, "; ".join(schema_errors[:5]))

    # 3. Обязательные непустые поля
    missing = check_required_values(data)
    add("required_fields", not missing, ", ".join(missing))

    # 4. Статус + дата подтверждения
    status = data.get("status")
    if expect_confirmed:
        ok = status == "confirmed" and bool(str(data.get("confirmationDate") or "").strip())
        add("status_confirmed", ok, f"status={status}, confirmationDate={data.get('confirmationDate')!r}")

    # 5. Секреты в JSON (по строке, без повторного чтения с диска)
    raw_json = json.dumps(data, ensure_ascii=False)
    secrets_json = detect_secrets_in_text(raw_json, str(json_path))
    add("secrets_json", not secrets_json, str([s["type"] for s in secrets_json]))

    # 6. Синхронность MD/JSON + секреты в MD — одно чтение MD
    if md_path is not None and md_path.exists():
        md_content = md_path.read_text(encoding="utf-8", errors="replace")
        md_data = extract_data_from_markdown(md_content)
        diffs = check_sync_errors(md_data, data)
        add("sync_md_json", not diffs, "; ".join(diffs[:5]))
        secrets_md = detect_secrets_in_text(md_content, str(md_path))
        add("secrets_md", not secrets_md, str([s["type"] for s in secrets_md]))
    elif md_path is not None:
        add("sync_md_json", False, f"Markdown не найден: {md_path}")

    # 7. Хэш происхождения (если поле заполнено — сверяем канонический хэш)
    stored = (data.get("hashes") or {}).get("business_context.json")
    if stored:
        recomputed = hash_of(data)  # единое правило — common.hash_of
        add("hash_provenance", stored == recomputed, f"stored={stored[:20]}…, recomputed={recomputed[:20]}…")

    return report


def main():
    parser = argparse.ArgumentParser(description="Итоговая проверка карточки бизнеса")
    parser.add_argument("--dir", help="Директория запуска (business_context.json + business_card.md внутри)")
    parser.add_argument("--json", dest="json_file", help="Путь к business_context.json")
    parser.add_argument("--md", dest="md_file", help="Путь к business_card.md")
    parser.add_argument("--expect-confirmed", action="store_true", default=True,
                        help="Требовать статус confirmed (по умолчанию включено)")
    parser.add_argument("--allow-draft", action="store_true", help="Не требовать статус confirmed")
    args = parser.parse_args()

    if args.dir:
        d = Path(args.dir)
        json_path = d / "business_context.json"
        md_path = d / "business_card.md"
    elif args.json_file:
        json_path = Path(args.json_file)
        md_path = Path(args.md_file) if args.md_file else None
    else:
        print("✗ Укажите --dir или --json")
        return 1

    report = run_checks(json_path, md_path, expect_confirmed=not args.allow_draft)
    report["ok"] = not report["errors"]
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if report["ok"]:
        print("✓ Итоговая проверка пройдена")
        return 0
    print("✗ Итоговая проверка НЕ пройдена:")
    for e in report["errors"]:
        print(f"  - {e}")
    return 1


if __name__ == "__main__":
    exit(main())

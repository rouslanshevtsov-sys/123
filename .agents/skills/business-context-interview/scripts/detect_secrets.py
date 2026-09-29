#!/usr/bin/env python3
"""
Поиск токенов и других секретов в файлах.

Паттерны — в scripts/common.py (используются также внутренними проверками
final_validation и self-scan навыка).

Режимы:
  --file <путь>   проверка одного файла (обратная совместимость)
  --dir <путь>    рекурсивная проверка текстовых файлов директории
                  (vk_token.txt игнорируется намеренно — это хранилище токена
                  вне результата; оно должно быть в .gitignore и не попадать в git)
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import detect_secrets_in_text  # noqa: E402

SKIP_NAMES = {"vk_token.txt"}
TEXT_SUFFIXES = {".json", ".md", ".txt", ".yaml", ".yml", ""}
MAX_FILE_BYTES = 2 * 1024 * 1024


def scan_file(path: Path) -> list:
    try:
        content = path.read_text(encoding="utf-8", errors="replace")
    except OSError as e:
        print(f"✗ Ошибка чтения файла {path}: {e}")
        return [{"type": "Ошибка чтения", "match": str(e)}]
    return detect_secrets_in_text(content, str(path))


def report(secrets: list) -> int:
    if secrets:
        print(f"✗ Найдено {len(secrets)} потенциальных секретов:")
        for s in secrets:
            print(f"  - {s['type']}: {s['match']}")
        return 1
    print("✓ Секреты не обнаружены")
    return 0


def main():
    parser = argparse.ArgumentParser(description="Поиск секретов в файлах")
    parser.add_argument("--file", help="Путь к файлу")
    parser.add_argument("--dir", help="Директория для рекурсивной проверки")
    args = parser.parse_args()

    if not args.file and not args.dir:
        print("✗ Укажите --file или --dir")
        return 1

    all_secrets = []

    if args.file:
        file_path = Path(args.file)
        if not file_path.exists():
            print(f"✗ Файл не найден: {file_path}")
            return 1
        all_secrets.extend(scan_file(file_path))

    if args.dir:
        dir_path = Path(args.dir)
        if not dir_path.is_dir():
            print(f"✗ Директория не найдена: {dir_path}")
            return 1
        for p in sorted(dir_path.rglob("*")):
            if not p.is_file() or p.name in SKIP_NAMES:
                continue
            if p.suffix.lower() not in TEXT_SUFFIXES or p.stat().st_size > MAX_FILE_BYTES:
                continue
            all_secrets.extend(scan_file(p))

    return report(all_secrets)


if __name__ == "__main__":
    exit(main())

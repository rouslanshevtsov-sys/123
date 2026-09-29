#!/usr/bin/env python3
"""
Проверка согласованности Markdown и JSON файлов.

Логика извлечения и сравнения — в scripts/common.py (единая точка правды).
Правило сверки названия: строгое равенство ИЛИ JSON-название начинается с MD-названия
(MD-заголовок карточки может быть сокращённым). См. references/skill-contract.md.
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import load_json, extract_data_from_markdown, check_sync_errors  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description='Проверка согласованности Markdown и JSON')
    parser.add_argument('--md', required=True, help='Путь к Markdown файлу')
    parser.add_argument('--json', required=True, help='Путь к JSON файлу')

    args = parser.parse_args()

    md_path = Path(args.md)
    json_path = Path(args.json)

    if not md_path.exists():
        print(f'✗ Файл не найден: {md_path}')
        return 1

    try:
        md_content = md_path.read_text(encoding='utf-8')
    except Exception as e:
        print(f'✗ Ошибка чтения Markdown: {e}')
        return 1

    try:
        json_data = load_json(json_path)
    except FileNotFoundError:
        print(f'✗ Файл не найден: {json_path}')
        return 1
    except ValueError as e:
        print(f'✗ {e}')
        return 1

    md_data = extract_data_from_markdown(md_content)
    differences = check_sync_errors(md_data, json_data)

    if differences:
        print(f'✗ Найдено {len(differences)} расхождений:')
        for diff in differences:
            print(f'  - {diff}')
        return 1

    print('✓ Markdown и JSON синхронизированы')
    return 0


if __name__ == '__main__':
    exit(main())

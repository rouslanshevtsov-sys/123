#!/usr/bin/env python3
"""
Проверка минимального набора обязательных полей business_context.json.

Список полей и логика — в scripts/common.py (REQUIRED_FIELDS, check_required_values).
Порог запуска downstream-навыков: эти поля должны быть заполнены НЕ пустыми.
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import load_json, check_required_values  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description='Проверка обязательных полей')
    parser.add_argument('--file', required=True, help='Путь к JSON файлу')

    args = parser.parse_args()

    try:
        data = load_json(args.file)
    except FileNotFoundError:
        print(f'✗ Файл не найден: {args.file}')
        return 1
    except ValueError as e:
        print(f'✗ {e}')
        return 1

    missing = check_required_values(data)

    if missing:
        print(f'✗ Отсутствуют или пусты обязательные поля ({len(missing)}):')
        for field in missing:
            print(f'  - {field}')
        return 1

    print('✓ Все обязательные поля заполнены')
    return 0


if __name__ == '__main__':
    exit(main())

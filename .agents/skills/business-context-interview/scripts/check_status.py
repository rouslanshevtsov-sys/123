#!/usr/bin/env python3
"""
Проверка статуса бизнес-контекста (draft / confirmed).

Условия (см. references/card-structure.md, раздел «Правила подтверждения»):
статус confirmed требует непустой confirmationDate.
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import STATUS_ENUM, load_json  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description='Проверка статуса')
    parser.add_argument('--file', required=True, help='Путь к JSON файлу')
    parser.add_argument('--expected', default=None,
                        choices=STATUS_ENUM, help='Ожидаемый статус')

    args = parser.parse_args()

    try:
        data = load_json(args.file)
    except FileNotFoundError:
        print(f'✗ Файл не найден: {args.file}')
        return 1
    except ValueError as e:
        print(f'✗ {e}')
        return 1

    status = data.get('status')
    if status is None:
        print('✗ Поле "status" отсутствует')
        return 1

    if args.expected and status != args.expected:
        print(f'✗ Ожидался статус "{args.expected}", получен "{status}"')
        return 1

    if status == 'confirmed':
        conf = data.get('confirmationDate')
        if not conf or not str(conf).strip():
            print('✗ Статус confirmed, но confirmationDate пуст — карточка не подтверждена корректно')
            return 1

    print(f'✓ Статус корректен: {status}')
    return 0


if __name__ == '__main__':
    exit(main())

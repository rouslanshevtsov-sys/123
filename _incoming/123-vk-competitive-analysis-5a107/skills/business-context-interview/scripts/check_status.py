#!/usr/bin/env python3
"""
Проверка статуса карточки бизнеса.

Проверяет, что статус соответствует ожидаемому.
"""

import argparse
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description='Проверка статуса')
    parser.add_argument('--file', required=True, help='Путь к JSON файлу')
    parser.add_argument('--expected', required=True, choices=['draft', 'confirmed'], help='Ожидаемый статус')
    
    args = parser.parse_args()
    
    file_path = Path(args.file)
    
    if not file_path.exists():
        print(f'✗ Файл не найден: {file_path}')
        return 1
    
    # Загружаем JSON
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        print(f'✗ Ошибка парсинга JSON: {e}')
        return 1
    
    # Проверяем статус
    actual_status = data.get('status')
    
    if actual_status is None:
        print(f'✗ Статус не указан')
        return 1
    
    if actual_status != args.expected:
        print(f'✗ Ожидался статус "{args.expected}", получен "{actual_status}"')
        return 1
    
    # Если статус confirmed, проверяем дату подтверждения
    if args.expected == 'confirmed':
        confirmation_date = data.get('confirmationDate')
        if not confirmation_date:
            print(f'✗ Статус confirmed, но дата подтверждения не указана')
            return 1
        print(f'✓ Статус: {actual_status}, дата подтверждения: {confirmation_date}')
    else:
        print(f'✓ Статус: {actual_status}')
    
    return 0


if __name__ == '__main__':
    exit(main())

#!/usr/bin/env python3
"""
Проверка обязательных полей в business_context.json.

Проверяет наличие минимального набора обязательных полей.
"""

import argparse
import json
from pathlib import Path


# Минимальный набор обязательных полей
REQUIRED_FIELDS = [
    ('business', 'name'),
    ('business', 'niche'),
    ('business', 'description'),
    ('products', 'main'),
    ('audience', 'targetSegments'),
    ('geography', 'regions'),
    ('channels', 'acquisition'),
]


def check_field(data: dict, path: tuple) -> bool:
    """Проверяет наличие и непустоту поля."""
    value = data
    for key in path:
        if not isinstance(value, dict):
            return False
        if key not in value:
            return False
        value = value[key]
    
    # Проверяем, что значение не пустое
    if value is None:
        return False
    if isinstance(value, str) and not value.strip():
        return False
    if isinstance(value, list) and len(value) == 0:
        return False
    
    return True


def main():
    parser = argparse.ArgumentParser(description='Проверка обязательных полей')
    parser.add_argument('--file', required=True, help='Путь к JSON файлу')
    
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
    
    # Проверяем обязательные поля
    missing_fields = []
    for field_path in REQUIRED_FIELDS:
        if not check_field(data, field_path):
            missing_fields.append('.'.join(field_path))
    
    if missing_fields:
        print(f'✗ Отсутствуют или пусты обязательные поля:')
        for field in missing_fields:
            print(f'  - {field}')
        return 1
    
    print(f'✓ Все обязательные поля заполнены')
    return 0


if __name__ == '__main__':
    exit(main())

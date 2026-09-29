#!/usr/bin/env python3
"""
Проверка схемы JSON файла business_context.json.

Проверяет наличие всех обязательных полей и их типы.
"""

import argparse
import json
import sys
from pathlib import Path


# Схема и логика валидации — единая точка правды в scripts/common.py
sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import SCHEMA, validate_schema  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description='Проверка схемы JSON')
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
    
    # Проверяем схему
    errors = validate_schema(data, SCHEMA)
    
    if errors:
        print(f'✗ Найдено {len(errors)} ошибок:')
        for error in errors:
            print(f'  - {error}')
        return 1
    
    print(f'✓ Схема JSON валидна')
    return 0


if __name__ == '__main__':
    exit(main())

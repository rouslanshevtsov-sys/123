#!/usr/bin/env python3
"""
Итоговая проверка соответствия результата всем условиям задачи.

Запускает все проверки и сообщает о результате.
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path


def run_check(script_name: str, args: list) -> tuple:
    """Запускает скрипт проверки и возвращает результат."""
    try:
        result = subprocess.run(
            ['python', script_name] + args,
            capture_output=True,
            text=True,
            timeout=10
        )
        return result.returncode == 0, result.stdout + result.stderr
    except Exception as e:
        return False, str(e)


def main():
    parser = argparse.ArgumentParser(description='Итоговая проверка')
    parser.add_argument('--dir', required=True, help='Директория с файлами')
    
    args = parser.parse_args()
    
    dir_path = Path(args.dir)
    json_path = dir_path / 'business_context.json'
    md_path = dir_path / 'business_card.md'
    
    # Проверяем существование файлов
    if not json_path.exists():
        print(f'✗ Файл не найден: {json_path}')
        return 1
    
    if not md_path.exists():
        print(f'✗ Файл не найден: {md_path}')
        return 1
    
    print('=' * 60)
    print('ИТОГОВАЯ ПРОВЕРКА')
    print('=' * 60)
    print()
    
    checks = []
    
    # 1. Проверка схемы JSON
    print('1. Проверка схемы JSON...')
    success, output = run_check('scripts/validate_json_schema.py', ['--file', str(json_path)])
    checks.append(('Схема JSON', success))
    print(f'   {"✓" if success else "✗"} {output.strip()}')
    print()
    
    # 2. Проверка статуса
    print('2. Проверка статуса...')
    success, output = run_check('scripts/check_status.py', ['--file', str(json_path), '--expected', 'confirmed'])
    checks.append(('Статус', success))
    print(f'   {"✓" if success else "✗"} {output.strip()}')
    print()
    
    # 3. Проверка обязательных полей
    print('3. Проверка обязательных полей...')
    success, output = run_check('scripts/check_required_fields.py', ['--file', str(json_path)])
    checks.append(('Обязательные поля', success))
    print(f'   {"✓" if success else "✗"} {output.strip()}')
    print()
    
    # 4. Поиск секретов в JSON
    print('4. Поиск секретов в JSON...')
    success, output = run_check('scripts/detect_secrets.py', ['--file', str(json_path)])
    checks.append(('Секреты в JSON', success))
    print(f'   {"✓" if success else "✗"} {output.strip()}')
    print()
    
    # 5. Поиск секретов в Markdown
    print('5. Поиск секретов в Markdown...')
    success, output = run_check('scripts/detect_secrets.py', ['--file', str(md_path)])
    checks.append(('Секреты в Markdown', success))
    print(f'   {"✓" if success else "✗"} {output.strip()}')
    print()
    
    # 6. Проверка согласованности
    print('6. Проверка согласованности Markdown и JSON...')
    success, output = run_check('scripts/check_sync.py', ['--md', str(md_path), '--json', str(json_path)])
    checks.append(('Согласованность', success))
    print(f'   {"✓" if success else "✗"} {output.strip()}')
    print()
    
    # Итоговый результат
    print('=' * 60)
    print('РЕЗУЛЬТАТ')
    print('=' * 60)
    
    all_passed = all(success for _, success in checks)
    
    if all_passed:
        print('✓ Все проверки пройдены успешно!')
        print()
        print('Карточка бизнеса:')
        print(f'  - Статус: confirmed')
        print(f'  - Файлы: {json_path}, {md_path}')
        return 0
    else:
        print('✗ Некоторые проверки не пройдены:')
        for name, success in checks:
            if not success:
                print(f'  - {name}')
        return 1


if __name__ == '__main__':
    exit(main())

#!/usr/bin/env python3
"""
Подтверждение карточки бизнеса.

Обновляет статус на confirmed, добавляет дату подтверждения,
синхронизирует Markdown и JSON.
"""

import argparse
import json
import re
from datetime import datetime
from pathlib import Path


def update_json(json_path: Path) -> dict:
    """Обновляет JSON файл: статус и дата подтверждения."""
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    data['status'] = 'confirmed'
    data['confirmationDate'] = datetime.now().strftime('%Y-%m-%d')
    
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    return data


def update_markdown(md_path: Path, data: dict):
    """Обновляет Markdown файл: статус и дата подтверждения."""
    with open(md_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Обновляем статус
    content = re.sub(
        r'\*\*Статус:\*\*.*',
        f'**Статус:** ✅ Подтверждено',
        content
    )
    
    # Обновляем дату подтверждения
    confirmation_date = data.get('confirmationDate', datetime.now().strftime('%Y-%m-%d'))
    content = re.sub(
        r'\*\*Дата подтверждения:\*\*.*',
        f'**Дата подтверждения:** {confirmation_date}',
        content
    )
    
    # Обновляем статус в конце файла
    content = re.sub(
        r'\*Статус:.*',
        f'*Статус: confirmed*',
        content
    )
    
    with open(md_path, 'w', encoding='utf-8') as f:
        f.write(content)


def sync_markdown_json(md_path: Path, json_path: Path, data: dict):
    """Синхронизирует Markdown и JSON."""
    # Обновляем Markdown на основе JSON
    update_markdown(md_path, data)


def main():
    parser = argparse.ArgumentParser(description='Подтверждение карточки бизнеса')
    parser.add_argument('--input-dir', required=True, help='Директория с файлами')
    
    args = parser.parse_args()
    
    input_dir = Path(args.input_dir)
    json_path = input_dir / 'business_context.json'
    md_path = input_dir / 'business_card.md'
    
    # Проверяем существование файлов
    if not json_path.exists():
        print(f'✗ Файл не найден: {json_path}')
        return 1
    
    if not md_path.exists():
        print(f'✗ Файл не найден: {md_path}')
        return 1
    
    # Обновляем JSON
    print('Обновляем JSON...')
    data = update_json(json_path)
    
    # Синхронизируем Markdown
    print('Синхронизируем Markdown...')
    sync_markdown_json(md_path, json_path, data)
    
    print(f'✓ Карточка подтверждена')
    print(f'  Статус: confirmed')
    print(f'  Дата: {data["confirmationDate"]}')
    
    return 0


if __name__ == '__main__':
    exit(main())

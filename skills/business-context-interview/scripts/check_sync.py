#!/usr/bin/env python3
"""
Проверка согласованности Markdown и JSON файлов.

Извлекает данные из обоих файлов и сравнивает их.
"""

import argparse
import json
import re
from pathlib import Path


def extract_data_from_markdown(md_content: str) -> dict:
    """Извлекает данные из Markdown."""
    data = {}
    
    # Название бизнеса
    match = re.search(r'# Карточка бизнеса:\s*(.+)', md_content)
    if match:
        data['business_name'] = match.group(1).strip()
    
    # Статус
    match = re.search(r'\*\*Статус:\*\*\s*(.+)', md_content)
    if match:
        status_text = match.group(1).strip()
        if 'Подтверждено' in status_text or 'confirmed' in status_text:
            data['status'] = 'confirmed'
        else:
            data['status'] = 'draft'
    
    # Дата подтверждения
    match = re.search(r'\*\*Дата подтверждения:\*\*\s*(.+)', md_content)
    if match:
        date_text = match.group(1).strip()
        if date_text != '—' and date_text != '—':
            data['confirmationDate'] = date_text
    
    # Источник
    match = re.search(r'\*\*Источник:\*\*\s*(.+)', md_content)
    if match:
        data['source_url'] = match.group(1).strip()
    
    # Ниша
    match = re.search(r'\*\*Ниша:\*\*\s*(.+)', md_content)
    if match:
        data['niche'] = match.group(1).strip()
    
    # Описание
    match = re.search(r'\*\*Описание:\*\*\s*(.+)', md_content)
    if match:
        data['description'] = match.group(1).strip()
    
    return data


def extract_data_from_json(json_content: str) -> dict:
    """Извлекает данные из JSON."""
    data = json.loads(json_content)
    
    result = {
        'business_name': data.get('business', {}).get('name'),
        'status': data.get('status'),
        'confirmationDate': data.get('confirmationDate'),
        'source_url': data.get('source', {}).get('url'),
        'niche': data.get('business', {}).get('niche'),
        'description': data.get('business', {}).get('description'),
    }
    
    return result


def compare_data(md_data: dict, json_data: dict) -> list:
    """Сравнивает данные из Markdown и JSON."""
    differences = []
    
    # Сравниваем название бизнеса
    if md_data.get('business_name') != json_data.get('business_name'):
        differences.append(f'business.name: MD="{md_data.get("business_name")}", JSON="{json_data.get("business_name")}"')
    
    # Сравниваем статус
    if md_data.get('status') != json_data.get('status'):
        differences.append(f'status: MD="{md_data.get("status")}", JSON="{json_data.get("status")}"')
    
    # Сравниваем дату подтверждения
    if md_data.get('confirmationDate') != json_data.get('confirmationDate'):
        # Игнорируем, если оба пустые
        if md_data.get('confirmationDate') or json_data.get('confirmationDate'):
            differences.append(f'confirmationDate: MD="{md_data.get("confirmationDate")}", JSON="{json_data.get("confirmationDate")}"')
    
    # Сравниваем источник
    if md_data.get('source_url') != json_data.get('source_url'):
        differences.append(f'source.url: MD="{md_data.get("source_url")}", JSON="{json_data.get("source_url")}"')
    
    # Сравниваем нишу
    if md_data.get('niche') != json_data.get('niche'):
        differences.append(f'business.niche: MD="{md_data.get("niche")}", JSON="{json_data.get("niche")}"')
    
    # Сравниваем описание
    if md_data.get('description') != json_data.get('description'):
        differences.append(f'business.description: MD="{md_data.get("description")}", JSON="{json_data.get("description")}"')
    
    return differences


def main():
    parser = argparse.ArgumentParser(description='Проверка согласованности Markdown и JSON')
    parser.add_argument('--md', required=True, help='Путь к Markdown файлу')
    parser.add_argument('--json', required=True, help='Путь к JSON файлу')
    
    args = parser.parse_args()
    
    md_path = Path(args.md)
    json_path = Path(args.json)
    
    # Проверяем существование файлов
    if not md_path.exists():
        print(f'✗ Файл не найден: {md_path}')
        return 1
    
    if not json_path.exists():
        print(f'✗ Файл не найден: {json_path}')
        return 1
    
    # Читаем файлы
    try:
        with open(md_path, 'r', encoding='utf-8') as f:
            md_content = f.read()
    except Exception as e:
        print(f'✗ Ошибка чтения Markdown: {e}')
        return 1
    
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            json_content = f.read()
    except Exception as e:
        print(f'✗ Ошибка чтения JSON: {e}')
        return 1
    
    # Извлекаем данные
    md_data = extract_data_from_markdown(md_content)
    json_data = extract_data_from_json(json_content)
    
    # Сравниваем
    differences = compare_data(md_data, json_data)
    
    if differences:
        print(f'✗ Найдено {len(differences)} расхождений:')
        for diff in differences:
            print(f'  - {diff}')
        return 1
    
    print(f'✓ Markdown и JSON синхронизированы')
    return 0


if __name__ == '__main__':
    exit(main())

#!/usr/bin/env python3
"""
Генерация карточки бизнеса из шаблонов.

Создаёт Markdown и JSON файлы на основе собранных данных.
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path


def load_template(template_path: str) -> str:
    """Загружает шаблон из файла."""
    with open(template_path, 'r', encoding='utf-8') as f:
        return f.read()


def generate_markdown(data: dict, template: str) -> str:
    """Генерирует Markdown из данных и шаблона."""
    # Заменяем плейсхолдеры в шаблоне на реальные данные
    result = template
    
    # Название бизнеса
    business_name = data.get('business', {}).get('name', '(название бизнеса)')
    result = result.replace('(название бизнеса)', business_name)
    result = result.replace('(название)', business_name)
    
    # Статус
    status = data.get('status', 'draft')
    if status == 'confirmed':
        result = result.replace('📝 Draft', '✅ Подтверждено')
    else:
        result = result.replace('📝 Draft', '📝 Draft')
    
    # Дата подтверждения
    confirmation_date = data.get('confirmationDate')
    if confirmation_date:
        result = result.replace('—', confirmation_date)
    else:
        result = result.replace('—', '—')
    
    # Источник
    source_url = data.get('source', {}).get('url', '(ссылка на источник)')
    result = result.replace('(ссылка на источник)', source_url)
    
    # Доступность
    accessible = data.get('source', {}).get('accessible', False)
    if accessible:
        result = result.replace('(доступен/недоступен)', 'Доступен')
    else:
        result = result.replace('(доступен/недоступен)', 'Недоступен')
    
    # Описание бизнеса
    business = data.get('business', {})
    result = result.replace('(маркетинговая ниша)', business.get('niche', '(ниша)'))
    result = result.replace('(позиционирование)', business.get('positioning', '(позиционирование)'))
    result = result.replace('(описание в 2-3 предложениях)', business.get('description', '(описание)'))
    
    # Продукты
    products = data.get('products', {})
    main_products = products.get('main', [])
    if main_products:
        main_list = '\n'.join([f'- {p}' for p in main_products])
        result = result.replace('- (продукт 1)\n- (продукт 2)', main_list)
    
    # Дата генерации
    generated_at = datetime.now().strftime('%Y-%m-%d')
    result = result.replace('(дата)', generated_at)
    
    return result


def generate_json(data: dict) -> str:
    """Генерирует JSON из данных."""
    # Добавляем дату генерации
    data['generatedAt'] = datetime.now().isoformat()
    
    # Форматируем JSON
    return json.dumps(data, ensure_ascii=False, indent=2)


def main():
    parser = argparse.ArgumentParser(description='Генерация карточки бизнеса')
    parser.add_argument('--output-dir', required=True, help='Директория для сохранения файлов')
    parser.add_argument('--data', help='JSON строка с данными (или путь к файлу)')
    parser.add_argument('--template-md', help='Путь к шаблону Markdown')
    parser.add_argument('--template-json', help='Путь к шаблону JSON')
    
    args = parser.parse_args()
    
    # Загружаем данные
    if args.data:
        if os.path.isfile(args.data):
            with open(args.data, 'r', encoding='utf-8') as f:
                data = json.load(f)
        else:
            data = json.loads(args.data)
    else:
        # Загружаем из templates/business_context.json
        template_json_path = args.template_json or 'templates/business_context.json'
        with open(template_json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    
    # Загружаем шаблон Markdown
    template_md_path = args.template_md or 'templates/business_card.md'
    template_md = load_template(template_md_path)
    
    # Генерируем файлы
    markdown_content = generate_markdown(data, template_md)
    json_content = generate_json(data)
    
    # Создаём директорию
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Сохраняем файлы
    md_path = output_dir / 'business_card.md'
    json_path = output_dir / 'business_context.json'
    
    with open(md_path, 'w', encoding='utf-8') as f:
        f.write(markdown_content)
    
    with open(json_path, 'w', encoding='utf-8') as f:
        f.write(json_content)
    
    print(f'✓ Файлы созданы:')
    print(f'  - {md_path}')
    print(f'  - {json_path}')


if __name__ == '__main__':
    main()

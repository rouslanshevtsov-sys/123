#!/usr/bin/env python3
"""
Подтверждение карточки бизнеса: draft -> confirmed.

Обновляет статус и confirmationDate, пересобирает Markdown из данных
(единый рендер в generate_card.render_markdown — без дублирующей логики),
пересчитывает канонический хэш и компактный provenance.json.

Использование:
    python scripts/confirm_card.py --input-dir ./Субагент\\ 1/Запуск_YYYY-MM-DD [--date YYYY-MM-DD]
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import load_json, save_json, hash_of, build_summary  # noqa: E402
from generate_card import render_markdown  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description='Подтверждение карточки бизнеса')
    parser.add_argument('--input-dir', required=True, help='Директория с файлами карточки')
    parser.add_argument('--date', default=None, help='Дата подтверждения (по умолчанию — сегодня)')

    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    json_path = input_dir / 'business_context.json'
    md_path = input_dir / 'business_card.md'

    try:
        data = load_json(json_path)
    except FileNotFoundError:
        print(f'✗ Файл не найден: {json_path}')
        return 1
    except ValueError as e:
        print(f'✗ {e}')
        return 1

    if data.get('status') not in ('draft', 'confirmed'):
        print(f"✗ Неожидаемый статус: {data.get('status')}")
        return 1

    conf_date = args.date or datetime.now().strftime('%Y-%m-%d')
    data['status'] = 'confirmed'
    data['confirmationDate'] = conf_date

    hashes = dict(data.get('hashes') or {})
    hashes['business_context.json'] = hash_of(data)
    data['hashes'] = hashes

    save_json(json_path, data)

    # Пересборка MD из тех же данных — синхронность гарантирована конструктивно
    md_path.write_text(render_markdown(data), encoding='utf-8')

    summary_path = input_dir / 'provenance.json'
    save_json(summary_path, build_summary(data, run_dir=input_dir))

    print('✓ Карточка подтверждена:')
    print(f'  - Статус: confirmed')
    print(f'  - Дата подтверждения: {conf_date}')
    print(f'  - Хэш контекста: {hashes["business_context.json"][:24]}…')
    print(f'  - Файлы: {json_path.name}, {md_path.name}, {summary_path.name}')
    return 0


if __name__ == '__main__':
    exit(main())

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

sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import hash_of, save_json, build_summary  # noqa: E402

SCHEMA_VERSION = "1.1"
NOT_FILLED = "⚠️ Не заполнено"


def _val(v):
    """Строковое представление значения для Markdown; пустое — явная метка."""
    if v is None or (isinstance(v, str) and not v.strip()):
        return NOT_FILLED
    return str(v)


def _lines(items):
    """Список → markdown-строки; пустой список — явная метка (не выдумываем данные)."""
    if not items:
        return f"- {NOT_FILLED}"
    return "\n".join(f"- {i}" for i in items)


def render_markdown(data: dict) -> str:
    """Собирает Markdown карточки из данных (без подстановки вымышленных значений)."""
    b = data.get('business', {})
    p = data.get('products', {})
    a = data.get('audience', {})
    g = data.get('geography', {})
    pr = data.get('pricing', {})
    sp = data.get('salesProcess', {})
    ch = data.get('channels', {})
    comp = data.get('competitors', {})
    cls = comp.get('classification', {})
    sc = data.get('searchCriteria', {})
    src = data.get('source', {})

    status = data.get('status', 'draft')
    status_line = "✅ Подтверждено" if status == 'confirmed' else "📝 Draft"
    conf_date = _val(data.get('confirmationDate')) if status == 'confirmed' else "—"
    accessible = "Доступен" if src.get('accessible') else "Недоступен"
    parse_error = src.get('parseError')
    if parse_error:
        accessible += f" ({parse_error})"
    today = datetime.now().strftime('%Y-%m-%d')

    def j(items):
        return ", ".join(items) if items else NOT_FILLED

    parts = [
        f"# Карточка бизнеса: {_val(b.get('name'))}",
        "",
        f"**Статус:** {status_line}",
        f"**Дата подтверждения:** {conf_date}",
        f"**Источник:** {_val(src.get('url'))}",
        f"**Доступность источника:** {accessible}",
        "",
        "---",
        "",
        "## 🏢 Описание бизнеса",
        "",
        f"**Название:** {_val(b.get('name'))}",
        f"**Ниша:** {_val(b.get('niche'))}",
        f"**Позиционирование:** {_val(b.get('positioning'))}",
        f"**Описание:** {_val(b.get('description'))}",
        "",
        "---",
        "",
        "## 📦 Продукты и ассортимент",
        "",
        "### Основные продукты:",
        _lines(p.get('main', [])),
        "",
        "### Второстепенные продукты:",
        _lines(p.get('secondary', [])),
        "",
        f"**Широта ассортимента:** {_val(p.get('assortmentWidth'))}",
        f"**Производитель/поставщик:** {_val(p.get('producer'))}",
        f"**Тип производства:** {_val(p.get('productionType'))}",
        "",
        "---",
        "",
        "## 👥 Аудитория",
        "",
        "### Целевые сегменты:",
        _lines(a.get('targetSegments', [])),
        "",
        "### Задачи клиентов:",
        _lines(a.get('tasks', [])),
        "",
        "### Боли:",
        _lines(a.get('painPoints', [])),
        "",
        "---",
        "",
        "## 🌍 География",
        "",
        f"**Регионы:** {j(g.get('regions', []))}",
        f"**Формат:** {_val(g.get('format'))}",
        "",
        "---",
        "",
        "## 💰 Цены",
        "",
        f"**Модель:** {_val(pr.get('model'))}",
        f"**Диапазон:** {_val(pr.get('range'))}",
        "",
        "---",
        "",
        "## 🛒 Процесс продаж",
        "",
        f"**Порядок заказа:** {_val(sp.get('orderProcess'))}",
        f"**Способы оплаты:** {j(sp.get('paymentMethods', []))}",
        f"**Доставка/доступ:** {_val(sp.get('deliveryOrAccess'))}",
        f"**Формат продаж:** {_val(sp.get('salesFormat'))}",
        "",
        "---",
        "",
        "## 📢 Каналы",
        "",
        "### Привлечение клиентов:",
        _lines(ch.get('acquisition', [])),
        "",
        "### Присутствие в интернете:",
        _lines(ch.get('onlinePresence', [])),
        "",
        "---",
        "",
        "## ⚡ Преимущества и ограничения",
        "",
        "### Преимущества:",
        _lines(data.get('advantages', [])),
        "",
        "### Ограничения:",
        _lines(data.get('limitations', [])),
        "",
        "---",
        "",
        "## 🔑 Ключевые особенности",
        "",
        _lines(data.get('keyFeatures', [])),
        "",
        "---",
        "",
        "## 🎯 Конкуренты",
        "",
        "### Известные конкуренты:",
        _lines(comp.get('known', [])),
        "",
        "### Правила классификации:",
        "",
        f"**Прямые конкуренты** — {cls.get('direct', NOT_FILLED)}",
        "",
        f"**Косвенные конкуренты** — {cls.get('indirect', NOT_FILLED)}",
        "",
        f"**Конкуренты за внимание** — {cls.get('attention', NOT_FILLED)}",
        "",
        "---",
        "",
        "## 🔍 Критерии поиска конкурентов",
        "",
        f"**Обязательные особенности:** {j(sc.get('mustHaveFeatures', []))}",
        f"**Платформы поиска:** {j(sc.get('searchPlatforms', []))}",
        f"**Количество:** {_val(sc.get('count'))}",
        f"**География:** {_val(sc.get('geography'))}",
        f"**Мин. аудитория VK:** {_val(sc.get('vkAudienceLimit'))}",
        f"**Свежесть публикаций:** {_val(sc.get('publicationFreshness'))}",
        "",
        "### Включить:",
        _lines(sc.get('include', [])),
        "",
        "### Исключить:",
        _lines(sc.get('exclude', [])),
        "",
        "### Предполагаемые поисковые запросы:",
        _lines([f"`{q}`" for q in sc.get('searchQueries', [])]),
        "",
        "---",
        "",
        "## ⚠️ Оставшиеся пробелы",
        "",
        _lines(data.get('gaps', [])),
        "",
        "---",
        "",
        f"*Файл сгенерирован: {today}*",
        f"*Статус: {status}*",
        "",
    ]
    return "\n".join(parts)


def main():
    skill_root = Path(__file__).resolve().parent.parent
    parser = argparse.ArgumentParser(description='Генерация карточки бизнеса')
    parser.add_argument('--output-dir', required=True, help='Директория для сохранения файлов')
    parser.add_argument('--data', help='JSON строка с данными (или путь к файлу)')
    parser.add_argument('--template-md', help='Устарело: Markdown собирается из данных (принимается, игнорируется)')
    parser.add_argument('--template-json', help='Путь к шаблону JSON (по умолчанию — templates/ навыка)')

    args = parser.parse_args()

    # Загружаем данные (один проход чтения)
    if args.data:
        if os.path.isfile(args.data):
            with open(args.data, 'r', encoding='utf-8') as f:
                data = json.load(f)
        else:
            data = json.loads(args.data)
    else:
        template_json_path = args.template_json or str(skill_root / 'templates/business_context.json')
        with open(template_json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

    # Метаданные происхождения данных (новые поля необязательны — обратная совместимость)
    data['schemaVersion'] = SCHEMA_VERSION
    data['generatedAt'] = datetime.now().isoformat()
    hashes = dict(data.get('hashes') or {})
    hashes['business_context.json'] = hash_of(data)
    data['hashes'] = hashes

    markdown_content = render_markdown(data)

    # Создаём директорию и сохраняем файлы
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    md_path = output_dir / 'business_card.md'
    json_path = output_dir / 'business_context.json'

    with open(md_path, 'w', encoding='utf-8') as f:
        f.write(markdown_content)

    save_json(json_path, data)

    # Компактный summary (~1 КБ) — следующий навык читает его вместо крупных файлов
    summary_path = output_dir / 'provenance.json'
    save_json(summary_path, build_summary(data, run_dir=output_dir))

    print('✓ Файлы созданы:')
    print(f'  - {md_path}')
    print(f'  - {json_path}')
    print(f'  - {summary_path}')


if __name__ == '__main__':
    main()

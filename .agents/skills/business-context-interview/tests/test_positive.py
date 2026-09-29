#!/usr/bin/env python3
"""
Положительные тесты для сценариев.

Тестирует успешные сценарии работы.
"""

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

# Каталог навыка (родитель tests/), чтобы тесты работали из любой директории запуска
SKILL_DIR = Path(__file__).resolve().parent.parent


def _run(script_args):
    """Запуск скрипта навыка: python3, абсолютный путь к скрипту, cwd=каталог навыка."""
    return subprocess.run(
        [sys.executable or "python3", str(SKILL_DIR / script_args[0])] + script_args[1:],
        capture_output=True,
        text=True,
        cwd=str(SKILL_DIR),
    )


def test_valid_confirmed_card():
    """Тест: подтверждённая карточка проходит все проверки."""
    print('Тест 1: Подтверждённая карточка...')
    
    # Создаём временную директорию
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        
        # Создаём валидный JSON
        data = {
            "status": "confirmed",
            "confirmationDate": "2026-01-20",
            "generatedAt": "2026-01-20T00:00:00.000Z",
            "source": {
                "url": "https://vk.com/test",
                "accessible": False,
                "parseError": ""
            },
            "business": {
                "name": "Тестовый бизнес",
                "niche": "Тестовая ниша",
                "positioning": "Тестовое позиционирование",
                "description": "Тестовое описание"
            },
            "products": {
                "main": ["Продукт 1", "Продукт 2"],
                "secondary": [],
                "assortmentWidth": None,
                "producer": "Тестовый производитель",
                "productionType": None
            },
            "audience": {
                "targetSegments": ["Сегмент 1"],
                "tasks": [],
                "painPoints": []
            },
            "geography": {
                "regions": ["Россия"],
                "format": "онлайн"
            },
            "pricing": {
                "model": None,
                "range": None
            },
            "salesProcess": {
                "orderProcess": None,
                "paymentMethods": [],
                "deliveryOrAccess": None,
                "salesFormat": None
            },
            "channels": {
                "acquisition": ["VK"],
                "onlinePresence": ["https://vk.com/test"]
            },
            "advantages": ["Преимущество 1"],
            "limitations": [],
            "keyFeatures": [],
            "competitors": {
                "known": [],
                "classification": {
                    "direct": "Прямые",
                    "indirect": "Косвенные",
                    "attention": "За внимание"
                }
            },
            "searchCriteria": {
                "mustHaveFeatures": [],
                "searchPlatforms": [],
                "count": None,
                "geography": None,
                "vkAudienceLimit": None,
                "publicationFreshness": None,
                "include": [],
                "exclude": [],
                "searchQueries": []
            },
            "gaps": [],
            "validation": {
                "jsonSyntaxValid": True,
                "syncedWithMarkdown": True,
                "noSecretsExposed": True,
                "noFabricatedData": True
            }
        }
        
        json_path = tmpdir / 'business_context.json'
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        # Создаём Markdown
        md_content = """# Карточка бизнеса: Тестовый бизнес

**Статус:** ✅ Подтверждено  
**Дата подтверждения:** 2026-01-20  
**Источник:** https://vk.com/test  
**Доступность источника:** Недоступен

---

## 🏢 Описание бизнеса

**Название:** Тестовый бизнес  
**Ниша:** Тестовая ниша  
**Позиционирование:** Тестовое позиционирование  
**Описание:** Тестовое описание
"""
        
        md_path = tmpdir / 'business_card.md'
        with open(md_path, 'w', encoding='utf-8') as f:
            f.write(md_content)
        
        # Запускаем проверки
        checks = [
            ('scripts/validate_json_schema.py', ['--file', str(json_path)]),
            ('scripts/check_status.py', ['--file', str(json_path), '--expected', 'confirmed']),
            ('scripts/check_required_fields.py', ['--file', str(json_path)]),
            ('scripts/detect_secrets.py', ['--file', str(json_path)]),
            ('scripts/detect_secrets.py', ['--file', str(md_path)]),
            ('scripts/check_sync.py', ['--md', str(md_path), '--json', str(json_path)]),
        ]
        
        all_passed = True
        for script, args in checks:
            result = _run([script] + args)
            if result.returncode != 0:
                print(f'  ✗ {script} не прошёл')
                print(f'    {result.stdout}')
                all_passed = False
        
        if all_passed:
            print('  ✓ Все проверки пройдены')
            return True
        else:
            return False


def main():
    print('=' * 60)
    print('ПОЛОЖИТЕЛЬНЫЕ ТЕСТЫ')
    print('=' * 60)
    print()
    
    tests = [
        test_valid_confirmed_card,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f'  ✗ Исключение: {e}')
            failed += 1
        print()
    
    print('=' * 60)
    print(f'РЕЗУЛЬТАТ: {passed} пройдено, {failed} не пройдено')
    print('=' * 60)
    
    return 0 if failed == 0 else 1


if __name__ == '__main__':
    exit(main())

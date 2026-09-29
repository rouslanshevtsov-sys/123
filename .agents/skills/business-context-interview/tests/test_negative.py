#!/usr/bin/env python3
"""
Отрицательные тесты для сценариев.

Тестирует обработку ошибок и невалидных данных.
"""

import json
import subprocess
import sys
import tempfile
from pathlib import Path

# Каталог навыка (родитель tests/), чтобы тесты работали из любой директории запуска
SKILL_DIR = Path(__file__).resolve().parent.parent


def _run(script_args):
    """Запуск скрипта навыка: текущий интерпретатор, абсолютный путь, cwd=каталог навыка."""
    return subprocess.run(
        [sys.executable or 'python3', str(SKILL_DIR / script_args[0])] + script_args[1:],
        capture_output=True,
        text=True,
        cwd=str(SKILL_DIR),
    )


def test_missing_source():
    """Тест: отсутствующий источник (файл не найден)."""
    print('Тест 1: Отсутствующий источник...')
    
    result = _run(['scripts/validate_json_schema.py', '--file', 'nonexistent.json'])
    
    if result.returncode != 0 and 'не найден' in result.stdout:
        print('  ✓ Корректно обработан отсутствующий файл')
        return True
    else:
        print('  ✗ Не удалось обработать отсутствующий файл')
        return False


def test_corrupted_json():
    """Тест: поврежденный JSON."""
    print('Тест 2: Поврежденный JSON...')
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        json_path = tmpdir / 'corrupted.json'
        
        # Создаём поврежденный JSON
        with open(json_path, 'w', encoding='utf-8') as f:
            f.write('{invalid json}')
        
        result = _run(['scripts/validate_json_schema.py', '--file', str(json_path)])
        
        if result.returncode != 0 and 'Ошибка парсинга' in result.stdout:
            print('  ✓ Корректно обработан поврежденный JSON')
            return True
        else:
            print('  ✗ Не удалось обработать поврежденный JSON')
            return False


def test_missing_required_fields():
    """Тест: отсутствие обязательных полей."""
    print('Тест 3: Отсутствие обязательных полей...')
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        json_path = tmpdir / 'incomplete.json'
        
        # Создаём JSON без обязательных полей
        data = {
            "status": "draft",
            "business": {
                "name": None,  # Пустое обязательное поле
                "niche": None,
                "description": None
            },
            "products": {
                "main": [],  # Пустой массив
                "producer": None
            },
            "audience": {
                "targetSegments": []  # Пустой массив
            },
            "geography": {
                "regions": []  # Пустой массив
            },
            "channels": {
                "acquisition": [],  # Пустой массив
                "onlinePresence": []
            },
            "competitors": {
                "known": [],
                "classification": {}
            },
            "gaps": []
        }
        
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        result = _run(['scripts/check_required_fields.py', '--file', str(json_path)])
        
        if result.returncode != 0 and 'Отсутствуют' in result.stdout:
            print('  ✓ Корректно обнаружены отсутствующие поля')
            return True
        else:
            print('  ✗ Не удалось обнаружить отсутствующие поля')
            return False


def test_wrong_status():
    """Тест: неправильный статус."""
    print('Тест 4: Неправильный статус...')
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        json_path = tmpdir / 'wrong_status.json'
        
        # Создаём JSON со статусом draft, но ожидаем confirmed
        data = {
            "status": "draft",
            "confirmationDate": None,
            "business": {"name": "Тест", "niche": "Тест", "description": "Тест"},
            "products": {"main": ["Тест"], "producer": "Тест"},
            "audience": {"targetSegments": ["Тест"]},
            "geography": {"regions": ["Тест"]},
            "channels": {"acquisition": ["Тест"], "onlinePresence": ["Тест"]},
            "competitors": {"known": [], "classification": {}},
            "gaps": []
        }
        
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        result = _run(['scripts/check_status.py', '--file', str(json_path), '--expected', 'confirmed'])
        
        if result.returncode != 0 and 'Ожидался статус' in result.stdout:
            print('  ✓ Корректно обнаружен неправильный статус')
            return True
        else:
            print('  ✗ Не удалось обнаружить неправильный статус')
            return False


def test_secret_detected():
    """Тест: обнаружение токена или секрета."""
    print('Тест 5: Обнаружение секрета...')
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        json_path = tmpdir / 'with_secret.json'
        
        # Создаём JSON с токеном
        data = {
            "status": "draft",
            "business": {
                "name": "Тест",
                "niche": "Тест",
                "description": "Тест с токеном vk1.a.ABC123XYZ789"
            },
            "products": {"main": [], "producer": None},
            "audience": {"targetSegments": []},
            "geography": {"regions": []},
            "channels": {"acquisition": [], "onlinePresence": []},
            "competitors": {"known": [], "classification": {}},
            "gaps": []
        }
        
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        result = _run(['scripts/detect_secrets.py', '--file', str(json_path)])
        
        if result.returncode != 0 and 'Найдено' in result.stdout and 'секрет' in result.stdout:
            print('  ✓ Корректно обнаружен секрет')
            return True
        else:
            print('  ✗ Не удалось обнаружить секрет')
            return False


def test_desync_markdown_json():
    """Тест: рассинхронизация Markdown и JSON."""
    print('Тест 6: Рассинхронизация Markdown и JSON...')
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        
        # Создаём JSON
        json_data = {
            "status": "confirmed",
            "confirmationDate": "2026-01-20",
            "business": {
                "name": "Бизнес из JSON",
                "niche": "Ниша из JSON",
                "description": "Описание из JSON"
            },
            "source": {"url": "https://vk.com/json", "accessible": False},
            "products": {"main": [], "producer": None},
            "audience": {"targetSegments": []},
            "geography": {"regions": []},
            "channels": {"acquisition": [], "onlinePresence": []},
            "competitors": {"known": [], "classification": {}},
            "gaps": []
        }
        
        json_path = tmpdir / 'business_context.json'
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, ensure_ascii=False, indent=2)
        
        # Создаём Markdown с другим названием
        md_content = """# Карточка бизнеса: Бизнес из Markdown

**Статус:** ✅ Подтверждено  
**Дата подтверждения:** 2026-01-20  
**Источник:** https://vk.com/md  
**Ниша:** Ниша из Markdown  
**Описание:** Описание из Markdown
"""
        
        md_path = tmpdir / 'business_card.md'
        with open(md_path, 'w', encoding='utf-8') as f:
            f.write(md_content)
        
        result = _run(['scripts/check_sync.py', '--md', str(md_path), '--json', str(json_path)])
        
        if result.returncode != 0 and 'расхождений' in result.stdout:
            print('  ✓ Корректно обнаружена рассинхронизация')
            return True
        else:
            print('  ✗ Не удалось обнаружить рассинхронизацию')
            return False


def main():
    print('=' * 60)
    print('ОТРИЦАТЕЛЬНЫЕ ТЕСТЫ')
    print('=' * 60)
    print()
    
    tests = [
        test_missing_source,
        test_corrupted_json,
        test_missing_required_fields,
        test_wrong_status,
        test_secret_detected,
        test_desync_markdown_json,
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

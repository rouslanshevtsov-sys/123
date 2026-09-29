#!/usr/bin/env python3
"""
Проверка схемы JSON файла business_context.json.

Проверяет наличие всех обязательных полей и их типы.
"""

import argparse
import json
import sys
from pathlib import Path


# Схема JSON
SCHEMA = {
    "type": "object",
    "required": ["status", "business", "products", "audience", "geography", "channels", "competitors", "gaps"],
    "properties": {
        "status": {"type": "string", "enum": ["draft", "confirmed"]},
        "confirmationDate": {"type": ["string", "null"]},
        "generatedAt": {"type": "string"},
        "source": {
            "type": "object",
            "required": ["url", "accessible"],
            "properties": {
                "url": {"type": "string"},
                "accessible": {"type": "boolean"},
                "parseError": {"type": "string"}
            }
        },
        "business": {
            "type": "object",
            "required": ["name", "niche", "description"],
            "properties": {
                "name": {"type": ["string", "null"]},
                "niche": {"type": ["string", "null"]},
                "positioning": {"type": ["string", "null"]},
                "description": {"type": ["string", "null"]}
            }
        },
        "products": {
            "type": "object",
            "required": ["main", "producer"],
            "properties": {
                "main": {"type": "array", "items": {"type": "string"}},
                "secondary": {"type": "array", "items": {"type": "string"}},
                "assortmentWidth": {"type": ["string", "null"]},
                "producer": {"type": ["string", "null"]},
                "productionType": {"type": ["string", "null"]}
            }
        },
        "audience": {
            "type": "object",
            "required": ["targetSegments"],
            "properties": {
                "targetSegments": {"type": "array", "items": {"type": "string"}},
                "tasks": {"type": "array", "items": {"type": "string"}},
                "painPoints": {"type": "array", "items": {"type": "string"}}
            }
        },
        "geography": {
            "type": "object",
            "required": ["regions"],
            "properties": {
                "regions": {"type": "array", "items": {"type": "string"}},
                "format": {"type": ["string", "null"]}
            }
        },
        "pricing": {
            "type": "object",
            "properties": {
                "model": {"type": ["string", "null"]},
                "range": {"type": ["string", "null"]}
            }
        },
        "salesProcess": {
            "type": "object",
            "properties": {
                "orderProcess": {"type": ["string", "null"]},
                "paymentMethods": {"type": "array", "items": {"type": "string"}},
                "deliveryOrAccess": {"type": ["string", "null"]},
                "salesFormat": {"type": ["string", "null"]}
            }
        },
        "channels": {
            "type": "object",
            "required": ["acquisition", "onlinePresence"],
            "properties": {
                "acquisition": {"type": "array", "items": {"type": "string"}},
                "onlinePresence": {"type": "array", "items": {"type": "string"}}
            }
        },
        "advantages": {"type": "array", "items": {"type": "string"}},
        "limitations": {"type": "array", "items": {"type": "string"}},
        "keyFeatures": {"type": "array", "items": {"type": "string"}},
        "competitors": {
            "type": "object",
            "required": ["known", "classification"],
            "properties": {
                "known": {"type": "array", "items": {"type": "string"}},
                "classification": {"type": "object"}
            }
        },
        "searchCriteria": {
            "type": "object",
            "properties": {
                "mustHaveFeatures": {"type": "array", "items": {"type": "string"}},
                "searchPlatforms": {"type": "array", "items": {"type": "string"}},
                "count": {"type": ["string", "null"]},
                "geography": {"type": ["string", "null"]},
                "vkAudienceLimit": {"type": ["string", "null"]},
                "publicationFreshness": {"type": ["string", "null"]},
                "include": {"type": "array", "items": {"type": "string"}},
                "exclude": {"type": "array", "items": {"type": "string"}},
                "searchQueries": {"type": "array", "items": {"type": "string"}}
            }
        },
        "gaps": {"type": "array", "items": {"type": "string"}},
        "validation": {
            "type": "object",
            "properties": {
                "jsonSyntaxValid": {"type": "boolean"},
                "syncedWithMarkdown": {"type": "boolean"},
                "noSecretsExposed": {"type": "boolean"},
                "noFabricatedData": {"type": "boolean"}
            }
        }
    }
}


def validate_type(value, expected_type):
    """Проверяет тип значения."""
    if isinstance(expected_type, list):
        return any(isinstance(value, t) for t in expected_type)
    return isinstance(value, expected_type)


def validate_schema(data: dict, schema: dict, path: str = "") -> list:
    """Рекурсивно проверяет схему."""
    errors = []
    
    # Проверяем тип
    if "type" in schema:
        if not validate_type(data, schema["type"]):
            errors.append(f"{path or 'root'}: ожидался тип {schema['type']}, получен {type(data).__name__}")
            return errors
    
    # Проверяем enum
    if "enum" in schema:
        if data not in schema["enum"]:
            errors.append(f"{path or 'root'}: значение должно быть одним из {schema['enum']}")
    
    # Проверяем обязательные поля
    if "required" in schema and isinstance(data, dict):
        for field in schema["required"]:
            if field not in data:
                errors.append(f"{path or 'root'}: отсутствует обязательное поле '{field}'")
    
    # Проверяем свойства
    if "properties" in schema and isinstance(data, dict):
        for prop, prop_schema in schema["properties"].items():
            if prop in data:
                prop_path = f"{path}.{prop}" if path else prop
                errors.extend(validate_schema(data[prop], prop_schema, prop_path))
    
    # Проверяем массив
    if schema.get("type") == "array" and isinstance(data, list):
        if "items" in schema:
            for i, item in enumerate(data):
                item_path = f"{path}[{i}]"
                errors.extend(validate_schema(item, schema["items"], item_path))
    
    return errors


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

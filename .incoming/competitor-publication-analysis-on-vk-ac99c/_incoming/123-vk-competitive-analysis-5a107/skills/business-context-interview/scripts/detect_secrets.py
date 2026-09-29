#!/usr/bin/env python3
"""
Поиск токенов и других секретов в файлах.

Проверяет, что в файлах нет токенов API, паролей и других секретов.
"""

import argparse
import json
import re
from pathlib import Path


# Паттерны для поиска секретов
SECRET_PATTERNS = [
    # VK API токены
    (r'vk1\.a\.[A-Za-z0-9_-]{10,}', 'VK API токен'),
    (r'vk[0-9]\.[A-Za-z0-9_-]{10,}', 'VK API токен'),
    
    # Общие токены
    (r'token["\s:=]+["\']?[A-Za-z0-9_-]{20,}', 'Токен'),
    (r'access_token["\s:=]+["\']?[A-Za-z0-9_-]{20,}', 'Access token'),
    
    # API ключи
    (r'api[_-]?key["\s:=]+["\']?[A-Za-z0-9_-]{20,}', 'API ключ'),
    
    # Пароли
    (r'password["\s:=]+["\']?[^\s"\']{8,}', 'Пароль'),
    (r'passwd["\s:=]+["\']?[^\s"\']{8,}', 'Пароль'),
    
    # Секретные ключи
    (r'secret["\s:=]+["\']?[A-Za-z0-9_-]{20,}', 'Секретный ключ'),
    (r'private[_-]?key["\s:=]+["\']?[A-Za-z0-9_-]{20,}', 'Приватный ключ'),
]


def detect_secrets_in_text(text: str, filename: str) -> list:
    """Ищет секреты в тексте."""
    found_secrets = []
    
    for pattern, secret_type in SECRET_PATTERNS:
        matches = re.finditer(pattern, text, re.IGNORECASE)
        for match in matches:
            found_secrets.append({
                'file': filename,
                'type': secret_type,
                'pattern': pattern,
                'match': match.group(0)[:50] + '...' if len(match.group(0)) > 50 else match.group(0)
            })
    
    return found_secrets


def main():
    parser = argparse.ArgumentParser(description='Поиск секретов в файлах')
    parser.add_argument('--file', required=True, help='Путь к файлу')
    
    args = parser.parse_args()
    
    file_path = Path(args.file)
    
    if not file_path.exists():
        print(f'✗ Файл не найден: {file_path}')
        return 1
    
    # Читаем файл
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print(f'✗ Ошибка чтения файла: {e}')
        return 1
    
    # Ищем секреты
    secrets = detect_secrets_in_text(content, str(file_path))
    
    if secrets:
        print(f'✗ Найдено {len(secrets)} потенциальных секретов:')
        for secret in secrets:
            print(f'  - {secret["type"]}: {secret["match"]}')
        return 1
    
    print(f'✓ Секреты не обнаружены')
    return 0


if __name__ == '__main__':
    exit(main())

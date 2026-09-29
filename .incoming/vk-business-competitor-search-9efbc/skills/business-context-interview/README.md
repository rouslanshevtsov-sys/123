# Навык: business-context-interview

## Описание

Навык для сбора и подтверждения бизнес-контекста с целью последующего поиска и анализа конкурентов.

## Структура

```
business-context-interview/
├── SKILL.md                          # Основной файл навыка
├── README.md                         # Этот файл
├── agents/
│   └── openai.yaml                   # Конфигурация агента
├── scripts/
│   ├── generate_card.py              # Генерация карточки из шаблонов
│   ├── confirm_card.py               # Подтверждение карточки
│   ├── validate_json_schema.py       # Проверка схемы JSON
│   ├── check_status.py               # Проверка статуса
│   ├── check_required_fields.py      # Проверка обязательных полей
│   ├── detect_secrets.py             # Поиск секретов
│   ├── check_sync.py                 # Проверка согласованности
│   └── final_validation.py           # Итоговая проверка
├── templates/
│   ├── business_card.md              # Шаблон карточки (Markdown)
│   └── business_context.json         # Шаблон контекста (JSON)
├── references/
│   └── card-structure.md             # Справочник по структуре карточки
└── tests/
    ├── test_positive.py              # Положительные тесты
    └── test_negative.py              # Отрицательные тесты
```

## Быстрый старт

### 1. Запуск навыка

```bash
# Навык запускается автоматически при запросе пользователя:
# "Собери контекст моего бизнеса"
# "Проведи интервью о бизнесе"
# "Найди конкурентов"
```

### 2. Проверка сценариев

```bash
cd skills/business-context-interview

# Проверка схемы JSON
python scripts/validate_json_schema.py --file business_context.json

# Проверка статуса
python scripts/check_status.py --file business_context.json --expected confirmed

# Проверка обязательных полей
python scripts/check_required_fields.py --file business_context.json

# Поиск секретов
python scripts/detect_secrets.py --file business_context.json

# Проверка согласованности
python scripts/check_sync.py --md business_card.md --json business_context.json

# Итоговая проверка
python scripts/final_validation.py --dir ./Субагент\ 1/Запуск_2026-01-20
```

### 3. Запуск тестов

```bash
cd skills/business-context-interview

# Положительные тесты
python tests/test_positive.py

# Отрицательные тесты
python tests/test_negative.py
```

## Требования

- Python 3.7+
- Доступ к VK API (опционально)

## Файлы результата

После подтверждения создаются два файла:

1. **business_card.md** — понятная карточка бизнеса
2. **business_context.json** — машиночитаемый контекст

Оба файла:
- Синхронизированы
- Имеют статус `confirmed`
- Не содержат секретов
- Проходят все проверки

## Проверки

Навык выполняет следующие проверки:

| Проверка | Скрипт | Описание |
|----------|--------|----------|
| Схема JSON | `validate_json_schema.py` | Проверка структуры и типов |
| Статус | `check_status.py` | Проверка статуса (draft/confirmed) |
| Обязательные поля | `check_required_fields.py` | Проверка минимального набора полей |
| Секреты | `detect_secrets.py` | Поиск токенов и паролей |
| Согласованность | `check_sync.py` | Сравнение Markdown и JSON |
| Итоговая | `final_validation.py` | Запуск всех проверок |

## Тесты

### Положительные тесты
- Подтверждённая карточка проходит все проверки

### Отрицательные тесты
- Отсутствующий источник (файл не найден)
- Поврежденный JSON
- Отсутствие обязательных полей
- Неправильный статус
- Обнаружение токена или секрета
- Рассинхронизация Markdown и JSON

## Примечания

- Навык не содержит данных конкретного бизнеса
- Навык не содержит токенов или секретов
- Навык использует относительные пути
- Все данные хранятся в рабочей папке пользователя

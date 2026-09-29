# Навык: Поиск и проверка конкурентов в VK

## Назначение и условия запуска

Навык находит и проверяет конкурентов в VK на основе подтверждённой JSON-карточки
бизнеса, формирует итоговый набор конкурентов с метриками (подписчики, активность, ER)
и создаёт артефакты для следующего этапа: Excel-отчёт и `competitor_set.json`.

Запускай навык, если:
- пользователь просит найти/проверить/обновить список конкурентов в VK;
- существует подтверждённый `business_context.json` (`status: "confirmed"`).

**Останови работу и сообщи причину, если:**
- файл `business_context.json` отсутствует, повреждён или не имеет статуса `confirmed`
  (сначала подтвердите бизнес-контекст — см. навык business-context-interview);
- нет токена VK API (файл `vk_token.txt` в проекте или переменная окружения `VK_API_TOKEN`).

Проверка gate: `python scripts/context.py validate <путь>/business_context.json`
(код выхода 2 = остановка).

## Обязательные входные данные

1. `business_context.json` со статусом `confirmed` — единственный источник критериев:
   `searchCriteria.count` (целевое число), `searchQueries`, `include/exclude`,
   `geography`, `vkAudienceLimit`, `publicationFreshness`, `competitors.known`
   (примеры-кандидаты для обязательной перепроверки).
2. Токен VK API: из файла `vk_token.txt` в корне проекта или переменной `VK_API_TOKEN`.
   Токен **никогда** не выводится в ответы, журналы, Excel, JSON и прочие результаты.
3. Каталог вывода этапа (например `output/competitor-analysis/`).

В файлах навыка и артефактах запрещены: данные текущего бизнеса, секреты,
подписанные URL, абсолютные пути.

## Последовательность работы

### Этап 1. Контекст и паспорт запуска
1. Прочитай и провалидируй карточку (`context.py validate`), извлеки критерии (`get_criteria`).
2. Вычисли SHA-256 карточки (`context.py hash`) — начало цепочки происхождения
   (см. [references/provenance.md](references/provenance.md)).
3. Создай `run_manifest.json` (`context.py manifest`): окно 31×24 ч, методы API, запросы,
   правила остановки, счётчики.

### Этап 2. Формирование пула
4. Составь список запросов: из карточки + дополнительные содержательные
   (синонимы ассортимента, названия продуктов, болей аудитории).
5. Для каждого запроса — `groups.search` с `count=1000` (`scripts/build_pool.py`).
   Расширение пула заверши, когда выполнено любое условие: два последовательных запроса
   добавили <5% новых уникальных ИЛИ пул достиг 3 кандидатов на одно целевое место.
6. Дедупликация по числовому `group_id`; учти `competitors.known` как отдельных кандидатов.

### Этап 3. Детализация и измеримые фильтры
7. Подробные данные — `groups.getById` пакетами (`vk_client.get_groups_batched`).
8. Фильтры доступности/типа/подписчиков/географии/офтопа/правил карточки —
   `scripts/filter_candidates.py`. Каждое исключение — с конкретной причиной
   ([references/exclusion-reasons.md](references/exclusion-reasons.md))).
9. Если пул > 200 — ранжируй по соответствию карточке и проверяй смысловыми пакетами
   до 200; следующий пакет только при недостатке подходящих в предыдущих.
   Языковой модели передавай только компактные данные квалификации.

### Этап 4. Смысловая квалификация (решения языковой модели)
10. Для каждого кандидата проверь ассортимент, аудиторию, географию, ценовой сегмент,
    модель продаж, производство (если критерий важен), онлайн/офлайн-формат
    по описанию и собственным постам; сверь сайты и первичные источники.
    Обязательное условие — действующее сообщество VK; только сайт без VK = исключить.
    Правила и типы — [references/classification.md](references/classification.md).
    Примеры конкурентов из карточки перепроверяются в первую очередь официальными
    сообществами VK/сайтами; если пример не найден — зафиксируй это, не выдумывай id.
11. Критерии ради достижения плана НЕ ослабляй; при дефиците зафиксируй фактическое
    число и причины (`shortfall` в манифесте).

### Этап 5. Публикации и ER
12. `scripts/collect_posts_er.py`: `wall.get count=100`, пагинация offset до покрытия
    окна 31×24 ч; закрепы отдельно; дедупликация по owner_id+post_id;
    ER=(лайки+комменты+репосты)/просмотры только при views>0; посты без просмотров —
    отдельно с причиной. Детали — [references/er-rules.md](references/er-rules.md).

### Этап 6. Итоговые артефакты
13. `scripts/build_outputs.py` создаёт:
    - `competitors.xlsx` — листы Сводка / Конкуренты / Проверены, но исключены /
      Посты за месяц / Методика (структура и колонки —
      [references/excel-structure.md](references/excel-structure.md), образец заполнения —
      [references/excel-example.md](references/excel-example.md));
    - `competitor_set.json` — основная передача дальше
      ([references/competitor-set-schema.md](references/competitor-set-schema.md));
    - обновлённый `run_manifest.json` с хэшем карточки и финальными счётчиками.

### Этап 7. Автопроверка
14. `python scripts/verify_results.py --context ... --competitor-set ... --excel ...
    --posts ... --manifest ...` — проверяет количество и уникальность group_id, корректность
    ER (пересчёт), наличие источников, причины исключений, согласованность Excel↔JSON,
    соответствие карточке, целостность цепочки по хэшу.
15. `python scripts/detect_secrets.py <каталог вывода>` и каталог навыка — секретов быть не должно.
16. Покажи пользователю краткий итог (число конкурентов, типы, средний ER, дефициты)
    и попроси подтвердить результат.

## Ожидаемые результаты

- В каталоге вывода: `pool_raw.json`, `details.json`, `shortlist.json`,
  `stage_filter.json`, `qualified.json`, `posts_er.json`, `competitor_set.json`,
  `competitors.xlsx`, `run_manifest.json`.
- Число конкурентов = целевому из карточки либо меньше с документированным дефицитом.
- У каждого конкурента — VK-ссылка (обязательно), сайт при наличии, тип, ER, обоснование,
  проверенные источники; у каждого исключённого — конкретная причина.

## Команды проверки

```bash
python skills/search-vk-competitors/tests/run_tests.py        # позитивные+негативные тесты
python skills/search-vk-competitors/scripts/vk_client.py      # наличие токена (без вывода)
python skills/search-vk-competitors/scripts/context.py validate <business_context.json>
python skills/search-vk-competitors/scripts/detect_secrets.py skills/search-vk-competitors
python skills/search-vk-competitors/scripts/verify_results.py --context ... --competitor-set ... \
    --excel ... --posts ... --manifest ...
```

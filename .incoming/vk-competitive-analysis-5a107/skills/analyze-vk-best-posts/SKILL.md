# Навык: analyze-vk-best-posts

Поисково-аналитический навык: по валидному `competitor_set.json` собирает публикации
VK сообществ-конкурентов за окно 7×24 ч, определяет лучшие посты по ER относительно
индивидуального бенчмарка сообщества, обрабатывает изображения и VK Клипы, расшифровывает
речь и создаёт проверенные XLSX/JSON. **Новых конкурентов не ищет** — работает только со
списком из входного файла.

## Условия запуска

Запускай, если пользователь просит:
- проанализировать публикации конкурентов из готового `competitor_set.json`;
- найти лучшие посты по ER за последнюю неделю;
- подготовить медиа/клипы/расшифровки и итоговый отчёт для следующего этапа.

Не запускай для поиска новых конкурентов (это другой навык) и без валидного входного файла.

## Обязательные входные данные

1. `competitor_set.json` — валидный список конкурентов (name, type direct|indirect|attention,
   vk_url или group_id). Схема и правила остановки — references/input-schema.md,
   шаблон — templates/competitor_set.example.json.
2. Токен VK API — переменная окружения `VK_TOKEN` или файл `.token` в рабочей директории.
   В артефакты и логи не попадает.
3. Рабочая директория запуска (`--workdir`/`VK_WORK_DIR`) — туда пишутся все артефакты.

Если входной файл отсутствует, повреждён или не содержит обязательных данных —
остановить работу и сообщить конкретную причину (`scripts/check_env.py`).

## Маршрут выполнения

Каждый шаг — отдельный сценарий `scripts/`; справочные материалы подключаются
только на соответствующем этапе.

### Шаг 0. Проверка входа и среды — `scripts/check_env.py`
Валидация JSON, типов и ссылок; проверка зависимостей (requests, Pillow, openpyxl,
Whisper). Справочник: references/input-schema.md.
Остановка при любой ошибке входа. Результат: `competitors_resolved.json`.

### Шаг 1. Сбор публикаций и комментариев — `scripts/collect_posts.py`
Единый момент старта фиксируется до начала сбора; часовой пояс Europe/Moscow;
окно ровно 168 ч. Полный обход пагинации wall.get(filter=owner), дедупликация,
исключение старых закрепплённых записей (до начала окна) и чужих репостов,
wall.getComments с ответами, недоступное — в `unavailable.json` с конкретной причиной.
Повторы при rate-limit/TLS. Правила окна: references/er-benchmarks.md.
Результаты: `run_meta.json`, `raw_posts.json`, `comments_replies.json`, `groups.json`.

### Шаг 2. ER, бенчмарки, лучшие посты, классификация — `scripts/analyze_posts.py`
Формула ER и правило «лучший = ER ≥ бенчмарка» — references/er-benchmarks.md;
типы постов, опрос, розыгрыш, закрепленные — references/post-types.md.
Посты без просмотров: статус «ER не рассчитан», в бенчмарк не входят.
Результат: `posts_analyzed.json`.

### Шаг 3. Медиа — `scripts/process_media.py`
Изображения лучших постов (~1600 px, кэш) и коллажи — references/images.md.
Подтверждение VK Клипов (внешний/внутренний тип, video.get), скачивание MP4/HLS/DASH,
oembed-fallback — references/vk-clips.md. **Обязательное правило: если просмотры
публикации и клипа различаются, ER и итоговая таблица используют только просмотры
клипа** (views_source='clip'). Расшифровка Whisper (модель ≥ small, VAD, очищенная
дословность, no_speech) — references/transcription.md. Обычные видео не скачиваются.
Результаты: `media/...`, `clips_processing.json`, обновлённые `posts_analyzed.json`, `benchmarks.json`.

### Шаг 4. Итоговые файлы — `scripts/build_outputs.py`
XLSX с пятью листами и точными колонками (references/excel-structure.md, шаблон
templates/excel_columns.json): Сводка, Лучшие посты (сортировка direct→indirect→attention,
внутри ER ↓), Клипы, Проверенные посты, Недоступно. JSON-датасеты и обезличенная
медиасводка — схемы в references/json-schemas.md.
Результаты: `competitors_vk_report.xlsx`, `vk_posts_dataset.json`,
`comments_replies.json`, `media_summary_anonymized.json`.

### Шаг 5. Блокирующий медиашлюз и автотест — `scripts/media_gate.py`
Проверяет всё из references/media-gate.md: полнота окна, дубли, ER/бенчмарки, связь
комментариев, классификация, статусы клипов, существование медиапутей, структура XLSX/JSON,
отсутствие секретов, запрет подмены просмотров клипа. FAIL блокирует завершение этапа.

### Шаг 6. Целостность навыка
`scripts/check_links.py` — связи SKILL.md ↔ scripts/references/templates;
`scripts/detect_secrets.py` — отсутствие токенов/абсолютных путей в файлах навыка.
Вспомогательные модули: `scripts/common.py` (правила классификации, ER, бенчмарков,
пути к артефактам) и `scripts/vkapi.py` (клиент VK API с ретраями и полной пагинацией).

## Основные смысловые правила

- Работать строго с конкурентами из competitor_set.json; новых не добавлять.
- Единое окно 7×24 ч для всех сообществ, Europe/Moscow.
- ER = (лайки + комментарии + репосты) / просмотры; только views > 0.
- Бенчмарк = среднее валидных ER сообщества за окно; лучший пост: ER ≥ бенчмарка.
- Ровно один основной тип поста; опрос — только по вложению poll; розыгрыш — только
  подтверждённый текстом механики.
- Клип определяется по внешнему ИЛИ внутреннему типу short_video/clip; при отсутствии
  внутреннего типа — video.get. Просмотры клипа никогда не заменяются просмотрами поста.
- Речь клипов расшифровывается только из аудиодорожки (не текст поста/описание/надписи).

## Условия остановки

Не завершай этап, если:
- competitor_set.json отсутствует/повреждён/неполон (Шаг 0);
- ожидались изображения лучших постов, но не скачано ни одного (Шаг 5);
- подтверждённый VK Клип не получил статус success или no_speech (Шаг 5);
- медиапути повреждены, зависимости отсутствуют, валидатор нашёл ошибки (Шаг 5).

Деградированный результат допустим **только после явного согласия пользователя**
(запуск медиашлюза с `--allow-degraded` и фиксация причин в листе «Недоступно»).

## Ожидаемые результаты

- `competitors_vk_report.xlsx` (5 листов, встроенные изображения, формат ER 0.00%);
- `vk_posts_dataset.json` — все проверенные публикации, метрики, бенчмарки, расшифровки, пути к медиа;
- `comments_replies.json` — комментарии и ответы, связанные строковым `post_id`;
- `media_summary_anonymized.json` — обезличенная медиасводка;
- `media/images`, `media/collages`, `media/clips` — медиафайлы;
- `unavailable.json` — недоступные объекты с конкретными причинами.

## Команды проверки

```bash
# среда и вход
python scripts/check_env.py --workdir <DIR> --competitor-set <DIR>/competitor_set.json [--require-whisper]
# сбор → анализ → медиа → итоги
python scripts/collect_posts.py --workdir <DIR>
python scripts/analyze_posts.py --workdir <DIR>
python scripts/process_media.py --workdir <DIR> --whisper-model small
python scripts/build_outputs.py --workdir <DIR>
# блокирующий шлюз и целостность навыка
python scripts/media_gate.py --workdir <DIR>
python scripts/check_links.py
python scripts/detect_secrets.py
# тесты сценариев (позитивные и негативные)
python -m pytest tests/ -q        # или: python tests/test_positive.py && python tests/test_negative.py
```

## Справочные материалы по этапам

| Этап | Документ |
|---|---|
| Вход | references/input-schema.md, templates/competitor_set.example.json |
| Окно/ER/бенчмарки | references/er-benchmarks.md |
| Классификация | references/post-types.md |
| Изображения | references/images.md |
| VK Клипы | references/vk-clips.md |
| Расшифровка | references/transcription.md |
| Excel | references/excel-structure.md, templates/excel_columns.json |
| JSON | references/json-schemas.md |
| Медиашлюз | references/media-gate.md |

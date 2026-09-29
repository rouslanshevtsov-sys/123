# Интервью → Конкуренты → Лучшие посты → Анализ реакции рынка: пример сквозного прогона

Директория запуска: `Субагент 1/Запуск_2026-09-29/`. Все этапы пишут в неё,
читают только артефакты непосредственного входа (см. chain-contract.md).

## Этап 1 — business-context-interview

```bash
cd skills/business-context-interview

# данные интервью собраны агентом, кладём во временный input.json и генерируем draft
python scripts/generate_card.py --output-dir "../../Субагент 1/Запуск_2026-09-29" --data input.json
# => business_card.md, business_context.json (status=draft), provenance.json

python scripts/confirm_card.py --input-dir "../../Субагент 1/Запуск_2026-09-29"
# => status=confirmed, confirmationDate, пересчёт хэша, пересборка MD из тех же данных

python scripts/final_validation.py --dir "../../Субагент 1/Запуск_2026-09-29"
python scripts/detect_secrets.py --dir "../../Субагент 1/Запуск_2026-09-29"
```

Ключевые решения этапа: не более 15+10 вопросов; пустое поле = null, а не выдумка;
токен — только в `vk_token.txt` (в `.gitignore`).

## Этап 2 — search-vk-competitors (поиск и проверка конкурентов в VK)

Вход: `provenance.json` (компактный) + `business_context.json` (для searchCriteria).
Gate навыка: `python scripts/context.py validate <контекст>` (код выхода 2 = остановка;
эквивалент порога входа §3 контракта). Токен: env `VK_API_TOKEN` или файл `vk_token.txt`.

```bash
python - <<'PY'
import sys; sys.path.insert(0, 'skills/business-context-interview/scripts')
from common import require_confirmed_context   # порог входа (§3 контракта)
ctx = require_confirmed_context('Субагент 1/Запуск_2026-09-29/business_context.json')
print(ctx['searchCriteria']['searchQueries'])
PY
```

Агент выполняет `groups.search` по запросам карточки, фильтрует и квалифицирует
(direct/indirect/attention), собирает посты за окно 31×24 ч и пишет **`competitor_set.json`**
(`scripts/build_outputs.py`; полная схема — references/competitor-set-schema.md навыка):

```json
{
  "status": "completed",
  "generated_at": "2026-09-29T12:00:00Z",
  "business_context": {"path": "business_context.json",
                       "sha256": "<байтовый SHA-256 карточки>", "status": "confirmed"},
  "time_window_hours": 744,
  "target_count": 10,
  "competitors": [
    {"gid": 123456789, "name": "...", "screen_name": "...",
     "vk_url": "https://vk.com/...", "site": "", "members_count": 12000,
     "competitor_type": "direct", "why_competitor": "...",
     "avg_er": 0.0389, "last_publication": 1750000000}
  ],
  "excluded_audit": [{"gid": 987, "name": "...", "reason": "конкретная причина"}],
  "provenance": {"run_manifest": "run_manifest.json",
                 "inputs": ["qualified.json", "posts_er.json", "stage_filter.json"]}
}
```

Правило остановки: если `business_context.sha256` ≠ хэша текущей карточки — контекст
изменился, этап 2 перезапускается, старые результаты не передаются дальше
(в черновом контракте это поле называлось `basedOnContextHash`).

## Этап 3 — analyze-vk-best-posts

Вход: `competitor_set.json` (только name/type/vk_url|group_id из файла; новых
конкурентов не добавляет). Окно — 7×24 ч (168 ч); сбор `wall.get` + `wall.getComments`,
ER относительно бенчмарка сообщества, клипы/расшифровки. Проверка входа и среды:
`python scripts/check_env.py --competitor-set competitor_set.json` — остановка при
любой ошибке входа. Выходные артефакты (`build_outputs.py`):

- **`vk_posts_dataset.json`** (схема `vk_posts_dataset/v1`) — компактный «заголовок»
  для передачи дальше: `schema`, `run.*` (окно, старт, TZ Europe/Moscow), `communities[]`,
  `benchmarks`, `unavailable[]`; крупные списки `posts[]`/`clips_processing[]` читаются точечно;
- **`comments.json`** — плоские комментарии `{post_id, comment_id, parent_id, from_id, text, likes}`
  (вариант с вложенными `replies` требует конвертации — контракт §2.3);
- **`competitors_vk_report.xlsx`** — листы «Лучшие» / «Проверенные»;
- медиа: `media/images/`, `media/clips/`, расшифровки.

Пример записи поста (фрагмент `posts[]`):

```json
{"post_id": "-123456789_111", "group_name": "...", "url": "https://vk.com/wall-123456789_111",
 "main_type": "Клип", "likes": 140, "comments": 30, "reposts": 12,
 "views_for_er": 9000, "views_source": "clip", "er": 0.0202,
 "benchmark": 0.0087, "is_best": true, "result": "Лучший",
 "transcript_status": "success", "data_status": "ok"}
```

После сбора фиксируется происхождение входа этапа 4:
`python scripts/make_provenance.py --workdir <wd>` → `provenance.json`
(sha256 каждого входа + множество проверенных post_id).

## Этап 4 — vk-content-report

Вход: `vk_posts_dataset.json` + `comments.json` + `competitors_vk_report.xlsx` +
`provenance.json` + media. Маршрут: `validate_inputs.py` (хэши и множества post_id —
несовпадение = STOP) → `validate_metrics.py` (пересчёт ER/бенчмарков, ≥90% комментариев
привязаны к датасету) → `classify_comments.py` → `analyze_posts.py` → выводы модели в
`report-draft.json` → `build_report.py` → `validate_report.py` (exit 2 — правки обязательны).
Выход — доказательный `report.html` без рекомендаций; машиночитаемые реакции —
необязательный `market_reactions.json` (топы форматов/тем по rel≥2x / ≤0.5x).

Итог цепочки — `chain_manifest.json` (ведёт этап 4; имена каноничны, см. контракт §2):

```json
{
  "chain": ["business-context-interview", "search-vk-competitors",
            "analyze-vk-best-posts", "vk-content-report"],
  "runDir": "Субагент 1/Запуск_2026-09-29",
  "artifacts": {
    "business_context.json":   {"canonicalHash": "sha256:…", "fileSha256": "sha256:…"},
    "competitor_set.json":     {"canonicalHash": "sha256:…", "fileSha256": "sha256:…"},
    "vk_posts_dataset.json":   {"canonicalHash": "sha256:…", "fileSha256": "sha256:…"},
    "comments.json":           {"fileSha256": "sha256:…"},
    "report.html":             {"fileSha256": "sha256:…"}
  },
  "checks": {"secretsScan": "PASS", "allStagesConfirmed": true,
             "provenanceChain": "continuous"}
}
```

## Расход контекста: что читает агент между этапами

| Передача | Читает агент | Размер |
|----------|--------------|--------|
| 1 → 2 | `provenance.json` (+ точечно searchCriteria) | ~1 КБ |
| 2 → 3 | компактные поля `competitor_set.json` (status, business_context, competitors[]) | ~2–5 КБ |
| 3 → 4 | заголовок `vk_posts_dataset.json` (`schema`, `run`, `communities`, `benchmarks`) + `provenance.json` | ~2–4 КБ |
| итог | `chain_manifest.json` | ~1 КБ |

Крупные файлы (`posts[]`, `excluded_audit[]`, тексты постов) целиком в контекст агента
не загружаются — только выборочная детализация по id.

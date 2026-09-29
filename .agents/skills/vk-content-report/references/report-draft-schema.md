# Схема report-draft.json (шаг 6)

Промежуточный файл модели. Его создаёт модель на основе `analysis-core.json` и
`comment-signals.json`, затем его читает `build_report.py`.

```json
{
  "meta": {"title": "<условный заголовок>", "subtitle": "<период и охват>"},
  "sections": {
    "scope": {"rows": [{"name": "<показатель>", "value": "<значение>"}], "text": "<сноска>"},
    "method": {"items": ["<формула ER>", "<правило бенчмарка>", "<сегменты>", "<приоритет уровней>"]},
    "top_posts": {"cards": [{
      "post_id": "-oid_pid", "url": "https://vk.com/wall-oid_pid", "group_name": "<имя>",
      "date_msk": "<дата>", "main_type": "<тип>", "bucket": "top25",
      "first_line": "<цитата первой строки>", "er": 0.0, "benchmark_er": 0.0,
      "rel_er_vs_benchmark": 0.0, "metrics": {"likes": 0, "comments": 0, "reposts": 0, "views": 0},
      "observation": "<что видно в данных>",
      "evidence_links": [{"post_id": "...", "url": "https://vk.com/...", "quote": "...",
                          "type": "post|comment|image|transcript", "source_file": "..."}]
    }]},
    "er_signals": {"items": [{"title": "...", "statement": "...", "competitor_level": "direct",
                              "confidence": "observed|confirmed", "evidence_links": [...]}]},
    "cta_signals": {"items": ["... та же структура ..."]},
    "content_signals": {"items": ["... та же структура ..."]},
    "comment_signals": {"items": ["... та же структура, type: comment обязательны ..."]},
    "clips": {"note": "<почему клипы отдельно>", "items": [
      {"group_name": "...", "post_id": "...", "statement": "...", "evidence_links": [
        {"url": "https://vk.com/clip-...", "type": "transcript", "source_file": "media/transcripts/..."}]}]},
    "low_posts": {"cards": ["... как top_posts, bucket: bottom25 ..."]},
    "conclusions": {"items": [
      {"title": "...", "statement": "...", "competitor_level": "direct|indirect|attention",
       "causal": false, "confirmation": "<чем подтверждён; обязательно при causal: true>",
       "evidence_links": [...]}]},
    "appendix": {"items": ["<недоступные посты, ограничения выгрузки>"]}
  }
}
```

## Инварианты

1. Каждая карточка и каждый item имеют непустой `evidence_links` с корректными url.
2. `causal: true` допустим только с заполненным `confirmation` (см. `evidence-rules.md`).
3. Тип публикации в url должен совпадать с блоком: `clip-` только в `clips`.
4. Ни одно поле не содержит рекомендаций (`no-recommendations.md`).

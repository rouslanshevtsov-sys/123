# Структура comment-signals.json

Файл создаётся скриптом `classify_comments.py` и используется на шагах 6 и 8.

```json
{
  "generated_at_msk": "<дата МСК>",
  "sources": {"dataset": "<имя файла>", "comments": "<имя файла>"},
  "note": "<строка о том, что классификация предварительная>",
  "total_posts_with_comments": 0,
  "total_comments": 0,
  "spam_templates": [{"text": "<шаблон>", "occurrences": 0}],
  "category_definitions": {"<категория>": "<расшифровка>"},
  "category_totals_excluding_spam": {"<категория>": 0},
  "spam_ad_excluded": 0,
  "category_totals_by_bucket": {"top25": {}, "middle": {}, "bottom25": {}},
  "category_totals_by_group": {"<сообщество>": {}},
  "category_totals_by_competitor_type": {"direct": {}, "indirect": {}, "attention": {}},
  "clips_only": {},
  "records": [
    {
      "post_id": "-oid_pid",
      "post_url": "https://vk.com/wall-oid_pid",
      "group_name": "<условное имя>",
      "competitor_type": "direct|indirect|attention",
      "bucket": "top25|middle|bottom25",
      "is_clip": false,
      "date_msk": "<дата поста>",
      "main_type": "<тип поста>",
      "post_er": 0.0,
      "benchmark_er": 0.0,
      "rel_er_vs_benchmark": 0.0,
      "comment_text": "<дословный текст>",
      "comment_likes": 0,
      "is_spam_template": false,
      "categories": ["<категория>"]
    }
  ]
}
```

## Инварианты

1. `post_id` каждой записи существует в датасете; `post_url` совпадает с датасетом.
2. `records` содержит только комментарии, привязанные к post_id (орфаны отбрасываются).
3. Сумма `category_totals_excluding_spam` считается по записям с `is_spam_template: false`.
4. `clips_only` отделён: категории комментариев под клипами считаются отдельно.
5. Ни одно поле не должно содержать абсолютных путей вне рабочей папки.

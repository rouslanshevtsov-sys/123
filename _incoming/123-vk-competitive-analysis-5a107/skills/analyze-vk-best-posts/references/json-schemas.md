# Схемы итоговых JSON-файлов

Все файлы создаются в рабочей директории запуска. Примеры содержат только условные данные.

## vk_posts_dataset.json (схема `vk_posts_dataset/v1`)

```json
{
  "schema": "vk_posts_dataset/v1",
  "run": {"run_started_at_msk": "<ISO>", "window_start_msk": "<ISO>",
          "window_end_msk": "<ISO>", "window_hours": 168, "timezone": "Europe/Moscow"},
  "timezone": "Europe/Moscow",
  "window_hours": 168,
  "secrets_note": "Токены и секреты в файл не включаются",
  "communities": [
    {"name": "<название>", "type": "direct|indirect|attention",
     "url": "https://vk.com/<sn>", "vk_id": -123, "members_count": 10000}
  ],
  "benchmarks": {"-123": 0.0087},
  "posts": [
    {
      "post_id": "-123_456", "owner_id": -123, "item_id": 456,
      "group_name": "<название>", "group_type": "attention",
      "url": "https://vk.com/wall-123_456",
      "date_ts": 1700000000, "date_msk": "YYYY-MM-DD HH:MM",
      "text": "<текст>", "main_type": "Клип|Видео|Картинка|Карусель|Текстовый пост",
      "has_poll": false, "is_giveaway": false,
      "likes": 10, "comments": 2, "reposts": 1,
      "views": 1000, "views_for_er": 950, "views_source": "clip|post",
      "clip_views_at_collection": 950,
      "er": 0.0137, "er_status": "ok|ER не рассчитан",
      "benchmark": 0.0087, "is_best": true, "result": "Лучший|Обычный|ER не рассчитан",
      "n_images": 2, "carousel": false,
      "image_urls": ["https://.../a.jpg"], "image_files": ["media/images/-123_456_0.jpg"],
      "collage_file": "media/collages/-123_456.jpg",
      "transcript": "<расшифровка или null>",
      "transcript_status": "success|no_speech|failed:<причина>|not_applicable_no_confirmed_clip",
      "pinned": false, "data_status": "ok"
    }
  ],
  "clips_processing": [
    {"post_id": "-123_456", "post_url": "...", "group_name": "...",
     "outer_type": "video|clip", "inner_type": "short_video|clip",
     "clip_views": 950, "file": "media/clips/-123_456.mp4",
     "status": "success|no_speech|failed:<причина>", "transcript": "..."}
  ],
  "unavailable": [{"object": "...", "link": "...", "reason": "<конкретная причина>"}]
}
```

Обязательные связи: `posts[].post_id` — строка `-<owner>_<item>`;
`views_source="clip"` ⇔ использованы просмотры клипа (подмена постами запрещена).

## comments_replies.json

Массив строк комментариев и ответов, связанных со строковым `post_id`:

```json
[{"post_id": "-123_456", "comment_id": 789, "parent_id": 0,
  "from_id": 321, "date_ts": 1700000100, "text": "...", "likes": 3}]
```

`parent_id != 0` — ответ на комментарий.

## unavailable.json / лист «Недоступно»

```json
[{"object": "<что недоступно>", "link": "<URL или null>", "reason": "<конкретная причина>"}]
```

## media_summary_anonymized.json (обезличенная медиасводка)

Без названий сообществ, ссылок и id; только ярлыки и диапазоны:

```json
{"generated_at_msk": "<ISO>",
 "window": {"start": "<ISO>", "end": "<ISO>", "hours": 168},
 "communities": [{"label": "Конкурент A", "type": "attention", "subscribers_band": "<500,000"}],
 "per_community": [{"label": "Конкурент A", "posts_in_window": 12, "benchmark_er": 0.0087,
   "best_posts": 5, "median_er_best": 0.012,
   "post_types": {"Картинка": 7, "Текстовый пост": 5},
   "polls": 1, "giveaways": 0, "confirmed_clips": 0}]}
```

## benchmarks.json

```json
{"-123": 0.0087, "-456": null}
```

Ключ — owner_id сообщества, значение — средний валидный ER за окно (null если валидных ER нет).

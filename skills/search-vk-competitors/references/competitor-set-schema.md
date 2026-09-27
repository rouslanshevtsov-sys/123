# Схема competitor_set.json

Основной файл данных для следующего этапа работы. Создаётся скриптом `build_outputs.py`.

```jsonc
{
  "status": "completed",                 // completed | blocked (нет токена/подтверждённой карточки)
  "generated_at": "<ISO8601 UTC>",
  "business_context": {                  // цепочка происхождения
    "path": "business_context.json",     // только имя файла, без абсолютного пути
    "sha256": "<хэш исходной карточки>",
    "status": "confirmed"
  },
  "time_window_hours": 744,              // единое окно сбора = 31 × 24 ч
  "target_count": 0,                     // searchCriteria.count из карточки
  "competitors": [                       // длина <= target_count
    {
      "gid": 123456789,                  // числовой id сообщества VK, уникален в списке
      "name": "Условное название",
      "screen_name": " условный_address",
      "vk_url": "https://vk.com/<address или publicID>",   // обязателен
      "site": "https://example.com",     // "" если сайта нет
      "members_count": 10000,
      "competitor_type": "direct | indirect | attention",
      "assortment": "…", "audience": "…", "geography": "…",
      "price_segment": "…", "sales_model": "…",
      "production": "…",                 // "" если критерий не важен
      "format": "online | offline | mixed",
      "why_competitor": "…",             // обязательная аргументация
      "sources_checked": ["vk:groups.getById", "vk:wall.get", "site:example.com"],
      "avg_er": 0.0389,                  // доля (0..1); null если нет постов с views>0
      "last_publication": 1750000000     // unix ts последней собственной публикации
    }
  ],
  "excluded_audit": [                    // полный аудит всех проверенных и отсеянных
    {"gid": 987, "name": "…", "reason": "конкретная причина исключения"}
  ],
  "provenance": {
    "run_manifest": "run_manifest.json",
    "inputs": ["qualified.json", "posts_er.json", "stage_filter.json"]
  }
}
```

## Инварианты (проверяются verify_results.py)

1. `business_context.sha256` равна фактическому SHA-256 карточки (иначе — разрыв цепочки).
2. У каждого конкурента есть валидный `vk_url`; group_id уникальны.
3. `len(competitors) <= target_count`; при недоборе — документированный `shortfall` в манифесте.
4. У каждой записи `excluded_audit` непустая `reason`.
5. `avg_er` соответствует пересчёту из posts-файла (см. er-rules.md).
6. Никаких токенов, секретов, подписанных URL и абсолютных путей.

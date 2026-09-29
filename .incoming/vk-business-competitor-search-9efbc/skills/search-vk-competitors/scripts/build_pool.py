#!/usr/bin/env python3
"""Сбор пула кандидатов: groups.search (count=1000), дедупликация по group_id,
правила остановки расширения пула.

Использование:
    python build_pool.py --queries-file queries.json --out-dir <dir> [--target N]
                         [--pool-factor 3] [--min-new-pct 5]

queries.json: ["запрос 1", "запрос 2", ...] — основной список из карточки,
затем генерируемые дополнительные содержательные запросы.
Результат: <out-dir>/pool_raw.json {pool: {gid: {...}}, queries_meta: [...]}
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from vk_client import VkClient  # noqa: E402


def build_pool(client, queries, target_count=None, pool_factor=3,
               min_new_pct=5.0, max_queries=None, logf=print):
    """Возвращает (pool dict gid->group_info, meta list).

    Правила остановки расширения:
      A) два последовательных запроса добавили < min_new_pct% новых уникальных;
      B) размер пула >= pool_factor * target_count.
    """
    pool = {}
    meta = []
    low_gain_streak = 0
    target_pool = (pool_factor * target_count) if target_count else None
    for qi, q in enumerate(queries):
        before = len(pool)
        try:
            items = client.search_groups(q, count=1000)
        except Exception as e:  # фиксируем ошибку, не роняем сбор
            meta.append({"query": q, "error": str(e), "returned": 0, "new_unique": 0})
            logf(f"[pool] query #{qi+1} ERROR: {e}")
            continue
        added = 0
        for g in items:
            gid = str(g.get("id"))
            if not gid or gid == "None":
                continue
            if gid not in pool:
                added += 1
                pool[gid] = {"gid": int(gid), "name": g.get("name"),
                             "screen_name": g.get("screen_name"),
                             "type": g.get("type"), "photo_50": g.get("photo_50"),
                             "found_by": [q]}
            else:
                fb = pool[gid]["found_by"]
                if q not in fb:
                    fb.append(q)
        after = len(pool)
        pct_new = (added / before * 100.0) if before else 100.0
        meta.append({"query": q, "returned": len(items), "new_unique": added,
                     "pool_size": after, "pct_new": round(pct_new, 2)})
        logf(f"[pool] '{q}': returned={len(items)} new={added} "
             f"({pct_new:.1f}%) pool={after}")
        low_gain_streak = low_gain_streak + 1 if (before and pct_new < min_new_pct) else 0
        stop_reason = None
        if low_gain_streak >= 2:
            stop_reason = "two consecutive queries added <5% new uniques"
        elif target_pool and after >= target_pool:
            stop_reason = f"pool reached {pool_factor}x target ({target_pool})"
        if stop_reason and (max_queries is None or qi + 1 < len(queries)):
            meta[-1]["stop"] = stop_reason
            logf(f"[pool] STOP expansion: {stop_reason}")
            break
        if max_queries and qi + 1 >= max_queries:
            break
    return pool, meta


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--queries-file", required=True)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--target", type=int, default=None,
                    help="целевое число конкурентов из карточки")
    ap.add_argument("--pool-factor", type=int, default=3)
    ap.add_argument("--min-new-pct", type=float, default=5.0)
    ap.add_argument("--token", default=None)
    args = ap.parse_args()

    with open(args.queries_file, encoding="utf-8") as f:
        queries = json.load(f)
    client = VkClient(token=args.token, logger=lambda m: print("[api]", m))
    pool, meta = build_pool(client, queries, target_count=args.target,
                            pool_factor=args.pool_factor,
                            min_new_pct=args.min_new_pct)
    os.makedirs(args.out_dir, exist_ok=True)
    out = os.path.join(args.out_dir, "pool_raw.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump({"pool": pool, "queries_meta": meta,
                   "unique_groups": len(pool)}, f, ensure_ascii=False)
    print(f"[pool] saved {len(pool)} unique groups -> {out}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Сбор публикаций за окно 31×24 ч и расчёт ER.

Использование:
    python collect_posts_er.py --candidates shortlist.json --out posts_er.json \
        [--window-hours 744] [--limit 200]

Правила (см. references/er-rules.md):
 - wall.get count=100, пагинация offset до полного покрытия окна;
 - закрепы обрабатываются отдельно от хронологии;
 - дедупликация постов по owner_id+post_id;
 - ER поста = (лайки + комментарии + репосты) / просмотры, только views > 0;
 - средний ER = среднее арифметическое ER всех собственных постов с views > 0;
 - посты без/с нулевыми просмотрами сохраняются отдельно с причиной исключения.
"""
import argparse
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from vk_client import VkClient  # noqa: E402


def compute_er(post):
    views = (post.get("views") or {}).get("count", 0) or 0
    if views <= 0:
        return None
    likes = (post.get("likes") or {}).get("count", 0) or 0
    comments = (post.get("comments") or {}).get("count", 0) or 0
    reposts = (post.get("reposts") or {}).get("count", 0) or 0
    return (likes + comments + reposts) / views


def process_group(client, gid, window_seconds):
    res = client.wall_posts_window(-gid, window_seconds=window_seconds)
    posts = res["posts"]
    start = res["window_start"]
    regular = [p for p in posts.values() if not p.get("is_pinned")
               and p.get("date", 0) >= start]
    pinned = [p for p in posts.values() if p.get("is_pinned")]
    scored, excluded_no_views = [], []
    for p in regular + pinned:
        er = compute_er(p)
        rec = {"owner_id": -gid, "post_id": p.get("id"), "date": p.get("date"),
               "is_pinned": bool(p.get("is_pinned")),
               "views": (p.get("views") or {}).get("count", 0),
               "likes": (p.get("likes") or {}).get("count", 0),
               "comments": (p.get("comments") or {}).get("count", 0),
               "reposts": (p.get("reposts") or {}).get("count", 0),
               "text_preview": (p.get("text") or "")[:180]}
        if er is None:
            rec["excluded_reason"] = "zero or missing views"
            excluded_no_views.append(rec)
        else:
            rec["er"] = round(er, 6)
            scored.append(rec)
    avg_er = (sum(r["er"] for r in scored) / len(scored)) if scored else None
    last_own = max([p["date"] for p in regular], default=None)
    return {
        "gid": gid, "pages": res["pages"], "window_covered": res["covered"],
        "own_posts_in_window": len(regular), "pinned_posts": len(pinned),
        "last_publication_date": last_own,
        "avg_er": round(avg_er, 6) if avg_er is not None else None,
        "scored_posts": sorted(scored, key=lambda r: -r["date"]),
        "excluded_posts": excluded_no_views,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--candidates", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--window-hours", type=int, default=31 * 24)
    ap.add_argument("--limit", type=int, default=200)
    ap.add_argument("--token", default=None)
    args = ap.parse_args()

    with open(args.candidates, encoding="utf-8") as f:
        cands = json.load(f)
    if isinstance(cands, dict):
        cands = list(cands.values())
    cands = cands[:args.limit]
    client = VkClient(token=args.token, logger=lambda m: print("[api]", m))
    window = args.window_hours * 3600
    results = {}
    for i, c in enumerate(cands):
        gid = c.get("gid") or c.get("id")
        try:
            results[str(gid)] = process_group(client, int(gid), window)
        except Exception as e:
            results[str(gid)] = {"gid": gid, "error": str(e)}
        if (i + 1) % 10 == 0:
            print(f"[er] {i+1}/{len(cands)} processed")
            with open(args.out, "w", encoding="utf-8") as f:
                json.dump(results, f, ensure_ascii=False)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False)
    ok = sum(1 for r in results.values() if r.get("avg_er") is not None)
    print(f"[er] done: {len(results)} groups, {ok} with avg ER -> {args.out}")


if __name__ == "__main__":
    main()

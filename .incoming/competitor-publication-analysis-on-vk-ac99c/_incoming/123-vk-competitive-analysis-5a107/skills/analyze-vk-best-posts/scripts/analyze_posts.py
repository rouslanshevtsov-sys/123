#!/usr/bin/env python3
"""Этап 2: расчёт ER, индивидуальных бенчмарков, выбор лучших постов, классификация.

Правила (см. references/er-benchmarks.md):
- ER = (лайки + комментарии + репосты) / просмотры, только при views > 0;
- для клипов используется count_views САМОГО клипа, а не поста-контейнера
  (замена просмотров клипа просмотрами поста запрещена);
- бенчмарк сообщества = среднее всех валидных ER этого сообщества за окно;
- лучший пост: ER >= бенчмарка; посты без просмотров -> статус 'ER не рассчитан',
  в бенчмарк не входят и лучшими не становятся.

Использование: python analyze_posts.py [--workdir DIR]
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import (best_photo_url, benchmark_of, classify_post, compute_er,  # noqa: E402
                    fmt_msk, load_json, save_json)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workdir", default=None)
    args = ap.parse_args()
    if args.workdir:
        os.environ["VK_WORK_DIR"] = args.workdir

    raw = load_json("raw_posts.json")

    posts_out = []
    for oid_s, rec in raw.items():
        g = rec["group"]
        oid = g["vk_id"]
        er_list = []
        records = []
        for p in rec["posts"]:
            likes = (p.get("likes") or {}).get("count", 0)
            comments_cnt = (p.get("comments") or {}).get("count", 0)
            reposts = (p.get("reposts") or {}).get("count", 0)
            views = (p.get("views") or {}).get("count")
            post_id = f"{oid}_{p['id']}"
            url = f"https://vk.com/wall{oid}_{p['id']}"
            main_type, has_poll, giveaway, photos, videos, clips, carousel = \
                classify_post(p.get("text", ""), p.get("attachments"))
            # Клип: ER считается по просмотрам самого клипа (video.get), не контейнера.
            views_for_er = views
            views_source = "post"
            clip_meta_pending = []
            if main_type == "Клип":
                for c in clips:
                    cv = c.get("count_views")
                    if cv is not None and cv > 0:
                        views_for_er = cv
                        views_source = "clip"
                    else:
                        clip_meta_pending.append(
                            {"owner_id": c.get("owner_id"), "video_id": c.get("id"),
                             "access_key": c.get("access_key")})
            er = compute_er(likes, comments_cnt, reposts, views_for_er)
            recd = {
                "post_id": post_id, "owner_id": oid, "item_id": p["id"],
                "group_name": g.get("resolved_name") or g["name"],
                "group_type": g["type"], "url": url,
                "date_ts": p.get("date"), "date_msk": fmt_msk(p.get("date", 0)),
                "text": p.get("text", ""), "main_type": main_type,
                "has_poll": has_poll, "is_giveaway": giveaway,
                "likes": likes, "comments": comments_cnt, "reposts": reposts,
                "views": views, "views_for_er": views_for_er,
                "views_source": views_source,
                "clip_needs_video_get": clip_meta_pending,
                "er": er,
                "er_status": "ok" if er is not None else "ER не рассчитан",
                "images": [best_photo_url(ph) for ph in photos],
                "n_images": len(photos), "carousel": carousel,
                "videos": videos, "clips": clips,
                "pinned": bool(p.get("is_pinned")), "data_status": "ok",
            }
            if er is not None:
                er_list.append(er)
            records.append(recd)
        bm = benchmark_of(er_list)
        for recd in records:
            recd["benchmark"] = bm
            if recd["er"] is not None and bm is not None:
                recd["is_best"] = recd["er"] >= bm
                recd["result"] = "Лучший" if recd["is_best"] else "Обычный"
            else:
                recd["is_best"] = False
                recd["result"] = "ER не рассчитан"
            posts_out.append(recd)
        print(f"{g['name']}: posts={len(records)} valid_er={len(er_list)} "
              f"benchmark={round(bm*100,3) if bm else None}% "
              f"best={sum(1 for x in records if x['is_best'])}")

    save_json("posts_analyzed.json", posts_out)
    ids = [x["post_id"] for x in posts_out]
    assert len(ids) == len(set(ids)), "Дубли публикаций!"
    print(f"total posts: {len(posts_out)} | duplicates removed: OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())

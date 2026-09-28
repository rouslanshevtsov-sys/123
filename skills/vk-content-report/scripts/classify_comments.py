#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Шаг 4. Предварительная классификация комментариев -> comment-signals.json.

Правила: references/comment-classification.md, структура: references/comment-signals-schema.md.
Спам-шаблоны (один текст на N+ постах) помечаются и исключаются из сигнальных категорий.
Каждая запись сохраняет post_id и ссылку на публикацию — без связи с постом сигнал не используется.
"""
import argparse
import os
import sys
from collections import Counter, defaultdict
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import (COMMENT_CATEGORY_DEFS, MSK, classify_comment, competitor_type,
                    detect_spam_templates, is_clip, load_json, normalize_comments,
                    normalize_dataset, write_json)


def build(workdir, dataset_name="vk_posts_dataset.json", comments_name="comments.json",
          out_name="comment-signals.json"):
    posts, _ = normalize_dataset(load_json(os.path.join(workdir, dataset_name)))
    index = {str(p.get("post_id")): p for p in posts}
    comments = normalize_comments(load_json(os.path.join(workdir, comments_name)))
    spam_map = detect_spam_templates(comments)
    spam_texts = {s["text"] for s in spam_map.values()}

    records = []
    for c in comments:
        pid = str(c.get("post_id") or "")
        post = index.get(pid)
        if not post:
            continue  # комментарий без связи с публикацией в анализ не попадает
        is_spam = bool(spam_map) and any(
            (c.get("text") or "").strip().lower() == (t or "").strip().lower() for t in spam_texts)
        cats = classify_comment(c.get("text"), spam=is_spam)
        bucket = post.get("_bucket") or post.get("bucket") or "middle"
        rec = {
            "post_id": pid,
            "post_url": post.get("url") or post.get("post_url"),
            "group_name": post.get("group_name"),
            "competitor_type": competitor_type(post),
            "bucket": bucket,
            "is_clip": is_clip(post),
            "date_msk": post.get("date_msk"),
            "main_type": post.get("main_type"),
            "post_er": post.get("er"),
            "benchmark_er": post.get("benchmark"),
            "rel_er_vs_benchmark": post.get("rel_er_vs_benchmark"),
            "comment_text": (c.get("text") or "").strip(),
            "comment_likes": c.get("likes") or 0,
            "is_spam_template": is_spam,
            "categories": cats,
        }
        records.append(rec)

    by_cat = Counter()
    by_bucket = defaultdict(Counter)
    by_group = defaultdict(Counter)
    by_type = defaultdict(Counter)
    clips_cat = Counter()
    for r in records:
        if r["is_spam_template"]:
            by_cat["spam_ad"] += 1
            continue
        for cat in r["categories"]:
            by_cat[cat] += 1
            b = r["bucket"] or "middle"
            by_bucket[b][cat] += 1
            by_group[r["group_name"] or "?"][cat] += 1
            by_type[r["competitor_type"]][cat] += 1
            if r["is_clip"]:
                clips_cat[cat] += 1

    payload = {
        "generated_at_msk": datetime.now(MSK).strftime("%Y-%m-%d %H:%M"),
        "sources": {"dataset": dataset_name, "comments": comments_name},
        "note": ("Классификация предварительная: категории присвоены по лексическим правилам. "
                 "Итоговые выводы по комментариям делает модель только при подтверждении "
                 "несколькими записями."),
        "total_posts_with_comments": len({r["post_id"] for r in records}),
        "total_comments": len(records),
        "spam_templates": [
            {"text": v["text"], "occurrences": v["occurrences"]} for v in spam_map.values()],
        "category_definitions": COMMENT_CATEGORY_DEFS,
        "category_totals_excluding_spam": {k: v for k, v in sorted(by_cat.items()) if k != "spam_ad"},
        "spam_ad_excluded": by_cat.get("spam_ad", 0),
        "category_totals_by_bucket": {b: dict(c) for b, c in by_bucket.items()},
        "category_totals_by_group": {g: dict(c) for g, c in by_group.items()},
        "category_totals_by_competitor_type": {t: dict(c) for t, c in by_type.items()},
        "clips_only": dict(clips_cat),
        "records": records,
    }
    write_json(os.path.join(workdir, out_name), payload)
    return payload


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workdir", required=True)
    ap.add_argument("--dataset", default="vk_posts_dataset.json")
    ap.add_argument("--comments", default="comments.json")
    ap.add_argument("--out", default="comment-signals.json")
    args = ap.parse_args()
    data = build(args.workdir, args.dataset, args.comments, args.out)
    if not data["records"]:
        print("FAIL classify_comments: ни один комментарий не связан с post_id из датасета")
        return 2
    print(f"OK classify_comments: комментариев {data['total_comments']}, "
          f"постов с комментариями {data['total_posts_with_comments']}, "
          f"спам-шаблонов {len(data['spam_templates'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

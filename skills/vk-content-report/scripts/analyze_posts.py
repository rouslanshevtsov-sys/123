#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Шаг 5. Анализ всех проверенных публикаций -> analysis-core.json.

Логика (references/analysis-contract.md, references/signal-separation.md,
references/competitor-priority.md, references/segmentation.md):
  - ER-, CTA- и содержательные сигналы разделяются и не смешиваются;
  - верхний и нижний сегменты — 25% относительно бенчмарка своего сообщества;
  - приоритет выводов: сначала данные прямых конкурентов, при их нехватке — косвенные,
    затем — конкуренты за внимание; каждый вывод помечает уровень опоры;
  - VK Клипы идут в отдельный блок и не смешиваются с обычными публикациями;
  - числовые сравнения ER допускаются только при rel >= 2x или <= 0.5x.

Скрипт готовит доказательную базу и компактный аналитический вход для модели;
смысловые выводы формулирует модель в report-draft.json (см. SKILL.md, шаг 6).
"""
import argparse
import os
import sys
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import (COMPETITOR_TYPE_ORDER, argument_types, competitor_type, extract_cta,
                    extract_hooks, first_line, is_clip, load_json, normalize_dataset,
                    numeric_er_comparison_allowed, parse_date_msk, promise_types,
                    split_quartiles, tone_of, transcript_of, trigger_hits, write_json)

MIN_DIRECT_POSTS = 10        # порог «данных достаточно» для уровня прямого конкурента
MIN_INDIRECT_POSTS = 10


def bucketize(posts):
    top, mid, bot = split_quartiles(posts)
    for p in top:
        p["_bucket"] = "top25"
    for p in mid:
        p["_bucket"] = "middle"
    for p in bot:
        p["_bucket"] = "bottom25"
    return top, mid, bot


def post_card(p, workdir):
    text = p.get("text") or ""
    card = {
        "post_id": str(p.get("post_id")),
        "url": p.get("url") or p.get("post_url"),
        "group_name": p.get("group_name"),
        "competitor_type": competitor_type(p),
        "date_msk": p.get("date_msk"),
        "main_type": p.get("main_type"),
        "is_clip": is_clip(p),
        "metrics": {"likes": p.get("likes"), "comments": p.get("comments"),
                    "reposts": p.get("reposts"), "views": p.get("views")},
        "er": p.get("er"),
        "benchmark_er": p.get("benchmark"),
        "rel_er_vs_benchmark": p.get("rel_er_vs_benchmark"),
        "er_comparison_allowed": numeric_er_comparison_allowed(p.get("rel_er_vs_benchmark")),
        "bucket": p.get("_bucket"),
        "first_line": first_line(text)[:200],
        "signals": {
            "er_signals": [],          # заполняет модель на основе rel_er и метрик
            "cta_signals": extract_cta(text),
            "content_signals": {
                "hooks": extract_hooks(text),
                "argument_types": argument_types(text),
                "promises": promise_types(text),
                "triggers_lexicon": trigger_hits(text),
                "tone": tone_of(text),
                "n_images": p.get("n_images") or len(p.get("images") or []),
                "has_poll": bool(p.get("has_poll")),
                "is_giveaway": bool(p.get("is_giveaway")),
            },
        },
    }
    media = []
    for key in ("image_paths", "collage_paths", "clip_paths"):
        val = p.get(key) or []
        if isinstance(val, list):
            media += [v for v in val if isinstance(v, str)]
    card["media_available"] = sorted(media)
    if card["is_clip"]:
        tr = transcript_of(p, os.path.join(workdir, "media", "transcripts"))
        card["clip"] = {
            "transcript_excerpt": (tr or "")[:700],
            "transcript_chars": len(tr or ""),
            "clip_views": (p.get("clips") or [{}])[0].get("views") if p.get("clips") else None,
            "status": p.get("clip_status") or ("success" if tr else "no_transcript"),
        }
    return card


def aggregate(cards):
    agg = defaultdict(lambda: {"n": 0, "types": Counter(), "cta": Counter(), "hooks": Counter(),
                               "arguments": Counter(), "triggers": Counter(), "promises": Counter()})
    for c in cards:
        g = agg[c["group_name"] or "?"]
        g["n"] += 1
        g["types"][c["main_type"]] += 1
        for item in c["signals"]["cta_signals"]:
            g["cta"][item["type"]] += 1
        cs = c["signals"]["content_signals"]
        for h in cs["hooks"]:
            g["hooks"][h] += 1
        for a in cs["argument_types"]:
            g["arguments"][a] += 1
        for t in cs["triggers_lexicon"]:
            g["triggers"][t] += 1
        for pr in cs["promises"]:
            g["promises"][pr] += 1
    out = {}
    for name, g in agg.items():
        out[name] = {"n_posts": g["n"],
                     "main_types": dict(g["types"]),
                     "cta_types": dict(g["cta"]),
                     "hooks": dict(g["hooks"]),
                     "argument_types": dict(g["arguments"]),
                     "triggers_lexicon": dict(g["triggers"]),
                     "promises": dict(g["promises"])}
    return out


def priority_coverage(cards):
    """Достаточно ли данных на каждом уровне конкурентов (references/competitor-priority.md)."""
    by_type = defaultdict(list)
    for c in cards:
        by_type[c["competitor_type"]].append(c)
    coverage = {}
    used_levels = []
    for t in COMPETITOR_TYPE_ORDER:
        n = len(by_type[t])
        threshold = {"direct": MIN_DIRECT_POSTS, "indirect": MIN_INDIRECT_POSTS,
                     "attention": 1}[t]
        enough = n >= threshold
        coverage[t] = {"posts": n, "enough_for_primary_conclusions": enough}
        if enough and t not in used_levels:
            used_levels.append(t)
        elif n and t not in used_levels:
            used_levels.append(t)  # данные есть, но их мало — уровень подключается как дополнение
    return coverage, used_levels


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workdir", required=True)
    ap.add_argument("--dataset", default="vk_posts_dataset.json")
    ap.add_argument("--out", default="analysis-core.json")
    args = ap.parse_args()
    wd = os.path.abspath(args.workdir)

    posts, meta = normalize_dataset(load_json(os.path.join(wd, args.dataset)))
    errors = []
    for p in posts:
        if p.get("rel_er_vs_benchmark") is None:
            errors.append(f"post_id={p.get('post_id')}: нет rel_er — пост выпадет из сегментов")

    regular = [p for p in posts if not is_clip(p)]
    clips = [p for p in posts if is_clip(p)]
    top, mid, bot = bucketize(regular)

    cards_all = [post_card(p, wd) for p in posts]
    for c in cards_all:
        pass  # bucket уже проставлен в исходных dict (те же объекты)

    top_ids = {str(p.get("post_id")) for p in top}
    bot_ids = {str(p.get("post_id")) for p in bot}
    clip_cards = [c for c in cards_all if c["is_clip"]]
    regular_cards = [c for c in cards_all if not c["is_clip"]]

    coverage, used_levels = priority_coverage(regular_cards + clip_cards)

    def compact(card):
        keep = ("post_id", "url", "group_name", "competitor_type", "date_msk", "main_type",
                "bucket", "rel_er_vs_benchmark", "er_comparison_allowed", "first_line",
                "metrics", "er", "benchmark_er")
        out = {k: card.get(k) for k in keep}
        out["cta_types"] = [i["type"] for i in card["signals"]["cta_signals"]]
        cs = card["signals"]["content_signals"]
        out["hooks"] = cs["hooks"]
        out["arguments"] = cs["argument_types"]
        out["triggers"] = cs["triggers_lexicon"]
        out["promises"] = cs["promises"]
        out["tone"] = cs["tone"]
        out["n_images"] = cs["n_images"]
        out["has_poll"] = cs["has_poll"]
        out["is_giveaway"] = cs["is_giveaway"]
        out["media_available_n"] = len(card["media_available"])
        if card.get("clip"):
            out["clip"] = {"transcript_chars": card["clip"]["transcript_chars"],
                           "status": card["clip"]["status"]}
        return out

    payload = {
        "method": ("ER = (лайки+комментарии+репосты)/просмотры поста; бенчмарк = средний ER "
                   "всех постов своего сообщества за окно; rel = ER поста / бенчмарк своего сообщества."),
        "window_days_covered": None,
        "counts": {
            "posts_total": len(posts), "regular": len(regular), "clips": len(clips),
            "top25": len(top), "middle": len(mid), "bottom25": len(bot),
        },
        "priority_coverage": coverage,
        "levels_used": used_levels,
        "aggregates_by_group": aggregate(cards_all),
        "segments": {
            "top25": [compact(c) for c in cards_all if c["post_id"] in top_ids],
            "bottom25": [compact(c) for c in cards_all if c["post_id"] in bot_ids],
        },
        "clips_block": [{**compact(c), "clip_transcript_excerpt": (c.get("clip") or {}).get("transcript_excerpt", "")}
                        for c in clip_cards],
        "validation_warnings": errors,
        "evidence_rule": ("Каждый вывод обязан ссылаться на post_id и url публикации; "
                          "причинный вывод допускается только при подтверждении данными "
                          "(несколько постов или комментарий с прямой формулировкой)."),
    }
    dates = [parse_date_msk(p.get("date_msk")) for p in posts]
    dates = [d for d in dates if d]
    if dates:
        payload["window_days_covered"] = (max(dates) - min(dates)).days + 1

    write_json(os.path.join(wd, args.out), payload)
    print(f"OK analyze_posts: постов {len(posts)} (обычных {len(regular)}, клипов {len(clips)}); "
          f"верхний сегмент {len(top)}, нижний {len(bot)}; уровни: {', '.join(used_levels)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

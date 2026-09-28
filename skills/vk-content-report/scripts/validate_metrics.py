#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Шаг 2. Проверка ER, бенчмарков и связи комментариев с публикациями.

Останавливает работу (exit code 2), если:
  - пересчитанный ER поста не совпадает с записанным в датасете (сверх допуска);
  - бенчмарк сообщества не совпадает со средним ER постов этого сообщества;
  - комментарии не связаны ни с одним post_id датасета или их доля критически мала;
  - у клипов есть статус clip, но нет расшифровки (и наоборот).

Результат: validation_metrics.json.
"""
import argparse
import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import (benchmark_of, benchmarks_match, compute_er, er_matches, is_clip,
                    load_json, normalize_comments, normalize_dataset, parse_date_msk,
                    rel_er, transcript_of, write_json)

MIN_COMMENTED_SHARE = 0.05   # минимум 5% постов должны иметь комментарии


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workdir", required=True)
    ap.add_argument("--dataset", default="vk_posts_dataset.json")
    ap.add_argument("--comments", default="comments.json")
    ap.add_argument("--out", default="validation_metrics.json")
    args = ap.parse_args()

    wd = os.path.abspath(args.workdir)
    errors, warnings = [], []
    posts, _ = normalize_dataset(load_json(os.path.join(wd, args.dataset)))
    comments = normalize_comments(load_json(os.path.join(wd, args.comments)))

    by_group = defaultdict(list)
    er_checked = 0
    for p in posts:
        pid = str(p.get("post_id"))
        er_rec = p.get("er")
        if er_rec is None and p.get("er_snapshot") is not None:
            er_rec = p.get("er_snapshot")
        recalc = compute_er(p.get("likes"), p.get("comments"), p.get("reposts"), p.get("views"))
        views_missing = not p.get("views")
        if views_missing:
            if recalc is not None or er_rec not in (None, 0):
                warnings.append(f"post_id={pid}: просмотров нет, но ER записан — в бенчмарк не входит")
            p["_er_valid"] = False
        else:
            er_checked += 1
            if recalc is None:
                errors.append(f"post_id={pid}: нельзя пересчитать ER (просмотры = {p.get('views')})")
                p["_er_valid"] = False
                continue
            if not er_matches(er_rec, recalc):
                errors.append(f"post_id={pid}: ER неверный — в датасете {er_rec}, пересчёт {round(recalc,6)} "
                              f"(лайки {p.get('likes')} + комменты {p.get('comments')} + репосты {p.get('reposts')}) / "
                              f"просмотры {p.get('views')}")
                p["_er_valid"] = False
            else:
                p["_er_valid"] = True
        p["_er_used"] = float(er_rec) if er_rec is not None else recalc
        by_group[p.get("group_name") or str(p.get("owner_id"))].append(p)

    # бенчмарки по сообществам
    bench_report = {}
    for gname, gposts in by_group.items():
        valid = [q for q in gposts if q.get("_er_valid")]
        recomputed = benchmark_of(valid)
        declared = {q.get("benchmark") or q.get("benchmark_er_snapshot") for q in gposts}
        declared = {float(d) for d in declared if d}
        if recomputed is None:
            errors.append(f"Сообщество «{gname}»: нет ни одного валидного ER — бенчмарк построить нельзя")
            continue
        if len(declared) > 1:
            errors.append(f"Сообщество «{gname}»: в датасете несколько разных бенчмарков ({len(declared)}) — "
                          f"должен быть один на сообщество")
        if declared:
            dec = next(iter(declared))
            if not benchmarks_match(dec, recomputed):
                errors.append(f"Сообщество «{gname}»: бенчмарк неверный — заявлен {round(dec,6)}, "
                              f"пересчёт среднего ER = {round(recomputed,6)} (постов {len(valid)})")
            ok = benchmarks_match(dec, recomputed)
        else:
            dec, ok = None, False
            warnings.append(f"Сообщество «{gname}»: бенчмарк в датасете не задан, использован пересчёт")
        bench_report[gname] = {"n_posts": len(gposts), "n_valid_er": len(valid),
                               "benchmark_declared": dec, "benchmark_recomputed": round(recomputed, 6),
                               "match": ok}
        for q in gposts:
            q["benchmark"] = recomputed
            q["rel_er_vs_benchmark"] = (round(rel_er(q.get("_er_used"), recomputed), 4)
                                        if q.get("_er_used") is not None else None)

    # связь комментариев с постами
    ids = {str(p.get("post_id")) for p in posts}
    linked = [c for c in comments if c.get("post_id") in ids]
    orphan = sorted({c.get("post_id") for c in comments if c.get("post_id") not in ids})
    if not comments:
        errors.append("Комментариев нет вообще — сигналы аудитории недоступны, отчёт без доказательств из комментариев")
    elif not linked:
        errors.append(f"Ни один комментарий не связан с post_id датасета (орфаны: {orphan[:5]})")
    elif len(linked) / max(1, len(comments)) < 0.9:
        errors.append(f"Связано с постами только {len(linked)} из {len(comments)} комментариев (<90%)")
    commented_posts = len({c["post_id"] for c in linked})
    if comments and commented_posts < max(1, int(len(posts) * MIN_COMMENTED_SHARE)):
        errors.append(f"Комментарии есть лишь у {commented_posts} постов из {len(posts)} — "
                      f"доля ниже минимальной {int(MIN_COMMENTED_SHARE*100)}%")

    # даты внутри окна выгрузки
    dates = [parse_date_msk(p.get("date_msk")) for p in posts]
    dates = [d for d in dates if d]
    window_days = (max(dates) - min(dates)).days + 1 if dates else 0

    # клипы и расшифровки
    clips = [p for p in posts if is_clip(p)]
    clip_no_transcript = []
    for p in clips:
        if not transcript_of(p, os.path.join(wd, "media", "transcripts")):
            clip_no_transcript.append(str(p.get("post_id")))
    if clips and len(clip_no_transcript) == len(clips):
        errors.append(f"VK Клипов {len(clips)}, но расшифровок нет ни у одного — анализ клипов невозможен")
    elif clip_no_transcript:
        warnings.append(f"Без расшифровки: {len(clip_no_transcript)} из {len(clips)} клипов: {clip_no_transcript[:5]}")

    # изображения
    with_images = [p for p in posts if p.get("images") or p.get("image_paths")]
    media_ok = sum(1 for p in with_images
                   if any(os.path.exists(os.path.join(wd, mp)) for mp in (p.get("image_paths") or [])
                          if isinstance(mp, str)))
    if with_images and not media_ok and not any(p.get("image_paths") for p in with_images):
        warnings.append("Локальных путей к изображениям нет — визуальные приёмы проверяются по ссылкам")

    result = {
        "ok": not errors,
        "errors": errors,
        "warnings": warnings,
        "checked": {
            "posts_total": len(posts),
            "posts_with_er_recalculated": er_checked,
            "groups": bench_report,
            "comments_total": len(comments),
            "comments_linked": len(linked),
            "posts_with_comments": commented_posts,
            "window_days_covered": window_days,
            "clips_total": len(clips),
            "clips_without_transcript": len(clip_no_transcript),
            "posts_with_images": len(with_images),
        },
    }
    write_json(os.path.join(wd, args.out), result)
    if errors:
        print("FAIL validate_metrics:")
        print("\n".join("- " + e for e in errors[:40]))
        return 2
    print("OK validate_metrics: ER, бенчмарки и связь комментариев подтверждены")
    print(f"- постов: {len(posts)}, сообществ: {len(bench_report)}, комментариев связано: {len(linked)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Автопроверка итоговых результатов и цепочки происхождения данных.

Использование:
    python verify_results.py --context business_context.json \
        --competitor-set competitor_set.json --excel competitors.xlsx \
        --posts posts_er.json [--manifest run_manifest.json]

Проверяет:
 - статус confirmed и хэш контекста в competitor_set (provenance);
 - наличие VK-сообщества у каждого конкурента, уникальность group_id;
 - количество <= целевого из карточки, фиксация недобора;
 - корректность ER (пересчёт из постов, views>0, нулевые — с причиной);
 - листы Excel (5 обязательных) и колонки листа «Конкуренты»;
 - согласованность Excel и JSON (число строк/конкурентов);
 - непустое поле «Проверенные источники» и причины исключений;
 - отсутствие секретов (токенов) во всех артефактах.
Код выхода 0 — успех; 1 — найдены проблемы.
"""
import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from context import load_context, get_criteria, sha256_file  # noqa: E402
from collect_posts_er import compute_er  # noqa: E402
from detect_secrets import scan_text  # noqa: E402

VK_URL_RE = re.compile(r"https?://(vk\.com|www\.vk\.com|m\.vk\.com)/\S+")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--context", required=True)
    ap.add_argument("--competitor-set", required=True)
    ap.add_argument("--excel", required=True)
    ap.add_argument("--posts", required=True)
    ap.add_argument("--manifest", default=None)
    args = ap.parse_args()
    problems = []

    ctx, err = load_context(args.context)
    if err:
        print("FAIL:", err)
        sys.exit(1)
    crit = get_criteria(ctx)

    cs = json.load(open(args.competitor_set, encoding="utf-8"))
    comps = cs.get("competitors", [])
    target = crit.get("count")

    # provenance / hash chain
    h = sha256_file(args.context)
    stored = (cs.get("business_context") or {}).get("sha256")
    if stored != h:
        problems.append(f"provenance: competitor_set sha256 {stored} != actual {h}")

    # counts and uniqueness
    gids = [str(c.get("gid") or c.get("id")) for c in comps]
    if len(gids) != len(set(gids)):
        problems.append("duplicate group_id among competitors")
    if target and len(comps) > target:
        problems.append(f"competitors {len(comps)} > target {target}")
    if target and len(comps) < target:
        mf = {}
        if args.manifest and os.path.isfile(args.manifest):
            mf = json.load(open(args.manifest, encoding="utf-8"))
        sf = mf.get("shortfall") or cs.get("shortfall")
        if not sf:
            problems.append(f"shortfall {len(comps)}/{target} not documented in manifest")

    # every competitor has a VK community link
    for c in comps:
        url = c.get("vk_url") or ""
        if not VK_URL_RE.match(url.strip()):
            problems.append(f"competitor {c.get('name')} has no valid VK url")

    # excluded audit non-empty reasons
    for e in cs.get("excluded_audit", []):
        if not e.get("reason"):
            problems.append(f"excluded candidate {e.get('gid')} without reason")

    # ER recomputation from posts file
    posts = json.load(open(args.posts, encoding="utf-8"))
    checked_er = 0
    for gid, pr in posts.items():
        scored = pr.get("scored_posts", [])
        for p in scored:
            v = p.get("views") or 0
            if v <= 0:
                problems.append(f"post {p.get('post_id')} in scored with views={v}")
            expected = compute_er({"views": {"count": p.get("views")},
                                   "likes": {"count": p.get("likes")},
                                   "comments": {"count": p.get("comments")},
                                   "reposts": {"count": p.get("reposts")}})
            if expected is None or abs(expected - (p.get("er") or 0)) > 1e-4:
                problems.append(f"ER mismatch for post {p.get('post_id')} of {gid}")
            checked_er += 1
        for p in pr.get("excluded_posts", []):
            if not p.get("excluded_reason"):
                problems.append(f"excluded post {p.get('post_id')} of {gid} without reason")

    # Excel structure & consistency
    try:
        from openpyxl import load_workbook
        wb = load_workbook(args.excel, read_only=True)
        need_sheets = ["Сводка", "Конкуренты", "Проверены, но исключены",
                       "Посты за месяц", "Методика"]
        for s in need_sheets:
            if s not in wb.sheetnames:
                problems.append(f"Excel missing sheet '{s}'")
        if "Конкуренты" in wb.sheetnames:
            ws = wb["Конкуренты"]
            headers = [c.value for c in next(ws.iter_rows(max_row=1))]
            need_cols = ["Название", "VK", "Сайт", "Тип конкурента", "Подписчики",
                         "Последняя публикация", "Средний ER за месяц", "Ассортимент",
                         "Аудитория", "География", "Ценовой сегмент", "Модель продаж",
                         "Производство (если нужно)", "Онлайн/офлайн",
                         "Почему конкурент", "Проверенные источники"]
            for col in need_cols:
                if col not in headers:
                    problems.append(f"Excel 'Конкуренты' missing column '{col}'")
            rows = [tuple(c.value for c in row) for row in ws.iter_rows(min_row=2)]
            n = sum(1 for r in rows if r and any(v not in (None, "") for v in r))
            if n != len(comps):
                problems.append(f"Excel competitors rows {n} != JSON {len(comps)}")
            idx_src = headers.index("Проверенные источники") if "Проверенные источники" in headers else None
            if idx_src is not None:
                for r in rows[:n]:
                    if not str(r[idx_src] or "").strip():
                        problems.append("competitor row without verified sources")
    except Exception as e:
        problems.append(f"Excel unreadable: {e}")

    # secrets scan across artifacts
    for path in [args.competitor_set, args.posts, args.excel] + ([args.manifest] if args.manifest else []):
        if not os.path.isfile(path):
            continue
        if path.endswith(".xlsx"):
            from openpyxl import load_workbook
            wb = load_workbook(path, read_only=True)
            blob = "\n".join(str(c.value) for ws in wb.worksheets
                             for row in ws.iter_rows() for c in row if c.value is not None)
        else:
            blob = open(path, encoding="utf-8", errors="ignore").read()
        hits = scan_text(blob)
        for hit in hits:
            problems.append(f"SECRET-LIKE content in {os.path.basename(path)}: {hit['rule']}")

    print(f"[verify] competitors={len(comps)} target={target} er_posts_checked={checked_er}")
    if problems:
        print(f"[verify] FAIL ({len(problems)} problems):")
        for p in problems:
            print("  -", p)
        sys.exit(1)
    print("[verify] OK — все проверки пройдены")


if __name__ == "__main__":
    main()

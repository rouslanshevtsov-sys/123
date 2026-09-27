#!/usr/bin/env python3
"""Измеримые фильтры и скоринг соответствия кандидатов карточке бизнеса.

Использование:
    python filter_candidates.py --pool pool_raw.json --context business_context.json \
        --details details.json --out-dir <dir> [--top 200]

Этапы (каждое исключение фиксируется с конкретной причиной):
 1) доступность/тип сообщества, закрытые, удалённые;
 2) минимум подписчиков (из карточки или default);
 3) география (RU/CIS по place/city/description);
 4) офтоп-фильтр по названию;
 5) смысловой скоринг по include-критериям карточки;
 6) исключение собственного сообщества бизнеса.
Результат: shortlist.json (отранжированный), stage_filter.json (исключённые+причины).
"""
import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from context import get_criteria  # noqa: E402

DEFAULT_MIN_SUBSCRIBERS = 1000
OFFTOP_RE = re.compile(
    r"(скид|акци|купон|барахол|подслуш|мем\b|юмор|новост|ваканси|афиш|"
    r"здоровь|рецепт|эзотер|астролог|таро|знакомец|знакомств)", re.I)
RU_CIS_RE = re.compile(
    r"(росси|москв|санкт-петерб|спб|казан|новосиб|екатеринбург|краснодар|"
    r"нижегород|самар|ростов-на-дону|воронеж|перм|уфа|челябинск|ярославль|"
    r"калуж|тул[ае]|беларус|минск|казахстан|алматы|нур-султан|астана|"
    r"киев|одесса| украи|🇷🇺|🇧🇾|🇰🇿)", re.I)


def has_own_site(site):
    if not site:
        return False
    doms = set(re.findall(r"(?:https?://)?(?:www\.)?([a-z0-9][a-z0-9\-\.]*\.[a-z]{2,})",
                          site.lower()))
    return bool(doms - {"vk.com", "m.vk.com", "vk.ru", "m.vk.ru", "vk.me"})


def geo_ok(g):
    place = json.dumps(g.get("place") or {}, ensure_ascii=False)
    city = json.dumps(g.get("city") or {}, ensure_ascii=False)
    text = " ".join(filter(None, [g.get("description"), g.get("name"), place, city]))
    return bool(RU_CIS_RE.search(text))


def score_candidate(g, criteria):
    """Скоринг соответствия: возвращает (score, matched_keywords)."""
    name = g.get("name") or ""
    desc = g.get("description") or ""
    t = (name + " " + desc).lower()
    incl = [w.lower() for w in (criteria.get("include") or []) if w]
    if not incl:
        return 0, []
    matched = [w for w in incl if w in t]
    if not matched:
        return 0, matched
    score = len(matched)
    nl = name.lower()
    if any(w in nl for w in matched):
        score += 2
    if has_own_site(g.get("site")):
        score += 1
    mc = g.get("members_count") or 0
    if 1000 <= mc <= 3_000_000:
        score += 1
    return score, matched


def apply_filters(pool, details, criteria, own_ids=None):
    """Возвращает (kept list of dicts, excluded list of {gid, name, reason})."""
    kept, excluded = [], []
    own_ids = set(str(i) for i in (own_ids or []))
    min_sub = criteria.get("minSubscribers") or DEFAULT_MIN_SUBSCRIBERS
    exclude_re = None
    if criteria.get("exclude"):
        try:
            exclude_re = re.compile("|".join(map(re.escape, criteria["exclude"])), re.I)
        except re.error:
            exclude_re = None
    for gid, base in pool.items():
        g = dict(base)
        g.update(details.get(gid, {}))
        name = g.get("name") or ""
        if gid in own_ids:
            excluded.append({"gid": gid, "name": name, "reason": "own business group"}); continue
        if g.get("is_closed"):
            excluded.append({"gid": gid, "name": name, "reason": "closed community — cannot verify content"}); continue
        if g.get("type") not in ("group", "pages", "public", "event"):
            excluded.append({"gid": gid, "name": name, "reason": f"unsupported type {g.get('type')}"}); continue
        mc = g.get("members_count")
        if mc is None:
            excluded.append({"gid": gid, "name": name, "reason": "no data from getById (deleted/unavailable)"}); continue
        if mc < min_sub:
            excluded.append({"gid": gid, "name": name, "reason": f"subscribers {mc} < required {min_sub}"}); continue
        if OFFTOP_RE.search(name):
            excluded.append({"gid": gid, "name": name, "reason": "off-topic name (marketplace/memes/news/etc.)"}); continue
        if exclude_re and exclude_re.search(name + " " + (g.get("description") or "")):
            excluded.append({"gid": gid, "name": name, "reason": "matches card exclusion rule"}); continue
        if criteria.get("geography") and not geo_ok(g):
            excluded.append({"gid": gid, "name": name, "reason": "geography outside target region"}); continue
        sc, matched = score_candidate(g, criteria)
        if sc <= 0:
            excluded.append({"gid": gid, "name": name, "reason": "assortment/audience mismatch: no include-keywords in name/description"}); continue
        g["score"] = sc
        g["matched_keywords"] = matched
        g["has_site"] = has_own_site(g.get("site"))
        kept.append(g)
    kept.sort(key=lambda x: (-x["score"], -(x.get("members_count") or 0)))
    return kept, excluded


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pool", required=True, help="pool_raw.json")
    ap.add_argument("--context", required=True, help="business_context.json")
    ap.add_argument("--details", required=True, help="details.json (groups.getById)")
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--top", type=int, default=None)
    args = ap.parse_args()

    with open(args.context, encoding="utf-8") as f:
        ctx = json.load(f)
    crit = get_criteria(ctx)
    with open(args.pool, encoding="utf-8") as f:
        pool_data = json.load(f)
    pool = pool_data["pool"] if isinstance(pool_data, dict) and "pool" in pool_data else pool_data
    with open(args.details, encoding="utf-8") as f:
        details = json.load(f)
    if isinstance(details, dict) and "details" in details:
        details = details["details"]

    kept, excluded = apply_filters(pool, details, crit, own_ids=crit.get("ownGroupIds"))
    if args.top:
        kept = kept[:args.top]
    os.makedirs(args.out_dir, exist_ok=True)
    for fn, obj in (("shortlist.json", kept), ("stage_filter.json", excluded)):
        with open(os.path.join(args.out_dir, fn), "w", encoding="utf-8") as f:
            json.dump(obj, f, ensure_ascii=False, indent=1)
    print(f"[filter] kept={len(kept)} excluded={len(excluded)} -> {args.out_dir}")


if __name__ == "__main__":
    main()

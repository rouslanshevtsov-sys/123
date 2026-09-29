#!/usr/bin/env python3
"""Контекст: загрузка/валидация business_context.json, хэши, паспорт запуска.

Использование:
    python context.py validate <путь>/business_context.json   # gate: status==confirmed
    python context.py hash <файл...>                          # SHA-256 файла
    python context.py manifest --out run_manifest.json --status running ...
"""
import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone

REQUIRED_STATUS = "confirmed"


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def load_context(path):
    """Загружает карточку; возвращает (dict, error|None). Остановка при проблемах."""
    if not os.path.isfile(path):
        return None, f"business_context.json not found at {path}"
    try:
        with open(path, "r", encoding="utf-8") as f:
            ctx = json.load(f)
    except json.JSONDecodeError as e:
        return None, f"business_context.json is corrupted: {e}"
    status = ctx.get("status")
    if status != REQUIRED_STATUS:
        return None, (f"business_context.json status is '{status}', expected "
                      f"'{REQUIRED_STATUS}'. Confirm the business context first.")
    return ctx, None


def get_criteria(ctx):
    """Извлекает критерии поиска из карточки (с безопасными значениями по умолчанию)."""
    sc = (ctx.get("searchCriteria") or {})
    own = ctx.get("ownGroup") or {}
    return {
        "count": sc.get("count"),
        "queries": sc.get("searchQueries") or [],
        "include": sc.get("include") or [],
        "exclude": sc.get("exclude") or [],
        "geography": sc.get("geography"),
        "minSubscribers": sc.get("vkAudienceLimit"),
        "freshnessHours": sc.get("publicationFreshness"),
        "knownCompetitors": (ctx.get("competitors") or {}).get("known") or [],
        "ownGroupIds": [own.get("id")] if own.get("id") else [],
    }


def make_manifest(window_hours=31 * 24, methods=None, queries=None,
                  stop_rules=None, counters=None, errors=None, notes=None):
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "time_window": {"hours": window_hours,
                        "seconds": window_hours * 3600,
                        "definition": "rolling last N hours from collection time"},
        "vk_api_methods": methods or ["groups.search", "groups.getById", "wall.get"],
        "search_queries": queries or [],
        "pool_expansion_stop_rules": stop_rules or [
            "two consecutive queries added <5% new unique groups",
            "pool reached 3 candidates per target slot",
        ],
        "pagination": {"wall_get_count": 100, "offset_step": 100,
                       "stop_condition": "all regular posts in last page older than window start",
                       "dedup_key": "owner_id+post_id", "pinned_handling": "separate"},
        "counters": counters or {},
        "errors": errors or [],
        "notes": notes or [],
    }


def save_json(obj, path):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)

    p1 = sub.add_parser("validate")
    p1.add_argument("context")

    p2 = sub.add_parser("hash")
    p2.add_argument("files", nargs="+")

    p3 = sub.add_parser("manifest")
    p3.add_argument("--out", required=True)
    p3.add_argument("--window-hours", type=int, default=31 * 24)
    p3.add_argument("--queries-file", help="JSON file with list of queries")
    p3.add_argument("--counters", help="JSON string of counters")
    p3.add_argument("--errors", help="JSON string of errors list")

    args = ap.parse_args()
    if args.cmd == "validate":
        ctx, err = load_context(args.context)
        if err:
            print("STOP:", err)
            sys.exit(2)
        crit = get_criteria(ctx)
        print("OK confirmed. target count=%s, queries=%d, known competitors=%d"
              % (crit["count"], len(crit["queries"]), len(crit["knownCompetitors"])))
    elif args.cmd == "hash":
        for fp in args.files:
            print(sha256_file(fp), fp)
    elif args.cmd == "manifest":
        queries = []
        if args.queries_file:
            with open(args.queries_file, encoding="utf-8") as f:
                queries = json.load(f)
        m = make_manifest(window_hours=args.window_hours, queries=queries,
                          counters=json.loads(args.counters) if args.counters else None,
                          errors=json.loads(args.errors) if args.errors else None)
        save_json(m, args.out)
        print("manifest saved:", args.out)


if __name__ == "__main__":
    main()

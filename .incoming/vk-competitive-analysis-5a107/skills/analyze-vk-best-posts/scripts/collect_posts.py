#!/usr/bin/env python3
"""Этап 1: сбор публикаций и комментариев VK через официальный API.

Делает:
- фиксирует единый момент старта и окно 7×24 ч (Europe/Moscow) в run_meta.json;
- резолвит screen_name сообществ через groups.getById (id + подписчики);
- wall.get(filter=owner) с полной пагинацией, дедупликацией по post_id;
- исключает посты вне окна, старые закрепленные (до начала окна) и репосты чужих;
- wall.getComments с ответами (parent_id), полная пагинация;
- недоступные объекты пишет в unavailable.json с конкретной причиной.

Использование: python collect_posts.py [--workdir DIR] [--window-hours 168]
"""
import argparse
import json
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import MSK, WINDOW_HOURS_DEFAULT, load_json, path, save_json  # noqa: E402
import vkapi  # noqa: E402

WALL_FIELDS = "attachments,likes,comments,reposts,views,copy_history,is_pinned"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workdir", default=None)
    ap.add_argument("--window-hours", type=int, default=WINDOW_HOURS_DEFAULT)
    args = ap.parse_args()
    if args.workdir:
        os.environ["VK_WORK_DIR"] = args.workdir

    competitors = load_json("competitors_resolved.json")
    now = datetime.now(MSK)
    ws_dt = now.replace(microsecond=0) - __import__("datetime").timedelta(hours=args.window_hours)
    window_start_ts = int(ws_dt.timestamp())
    meta = {
        "run_started_at_msk": now.isoformat(),
        "window_start_msk": datetime.fromtimestamp(window_start_ts, MSK).isoformat(),
        "window_end_msk": now.isoformat(),
        "window_hours": args.window_hours,
        "timezone": "Europe/Moscow",
    }
    save_json("run_meta.json", meta, indent=2)
    print(f"RUN START: {meta['run_started_at_msk']} | WINDOW FROM: {meta['window_start_msk']}")

    unavailable = []
    groups_out = []
    all_posts = {}

    sn_list = [c["screen_name"] for c in competitors if c.get("screen_name")]
    gid_map = {}
    if sn_list:
        r = vkapi.call("groups.getById", {"group_ids": ",".join(sn_list)})
        if "response" in r:
            for g in r["response"]:
                gid_map[str(g.get("screen_name")).lower()] = g
        else:
            print(f"WARN groups.getById: {r.get('error_msg')}")

    for c in competitors:
        sn = (c.get("screen_name") or "").lower()
        g = gid_map.get(sn)
        oid = None
        if c.get("group_id"):
            oid = -abs(int(c["group_id"]))
        elif g is not None and g.get("type") == "group":
            oid = -int(g["id"])
        if oid is None:
            unavailable.append({
                "object": f"Сообщество {c['name']}",
                "link": c.get("url") or f"https://vk.com/{sn}",
                "reason": ("groups.getById не вернул сообщество по screen_name "
                           f"'{sn}' (HTTP/адрес недоступен или id не найден)")})
            groups_out.append({**c, "vk_id": None, "members_count": None})
            continue

        members = g.get("members_count") if g else None
        groups_out.append({**c, "vk_id": oid, "members_count": members,
                           "resolved_name": g.get("name") if g else c["name"]})

        items, err = vkapi.paginate(
            "wall.get",
            {"owner_id": oid, "filter": "owner", "fields": WALL_FIELDS},
            page_size=100, deadline_ts=window_start_ts)
        if err and not items:
            unavailable.append({"object": f"Стена {c['name']}",
                                "link": c.get("url"), "reason": err})
            continue
        seen, own = set(), []
        pinned_old = 0
        for p in items:
            key = f"{oid}_{p['id']}"
            if key in seen:
                continue
            seen.add(key)
            if p.get("date", 0) < window_start_ts:
                if p.get("is_pinned"):
                    pinned_old += 1
                continue
            ch = p.get("copy_history")
            if ch and ch[0].get("from_id") != oid:
                continue  # репост чужой записи — не собственная публикация
            own.append(p)
        all_posts[str(oid)] = {"group": groups_out[-1], "posts": own,
                               "raw_fetched": len(items),
                               "excluded_pinned_before_window": pinned_old}
        print(f"{sn}: fetched={len(items)} own_in_window={len(own)} pinned_old_excl={pinned_old}")

    # ---- комментарии с ответами ----
    comments_out = []
    for oid_s, rec in all_posts.items():
        oid = int(oid_s)
        for p in rec["posts"]:
            cnt = p.get("comments", {}).get("count", 0)
            if cnt <= 0:
                continue
            off, err = 0, None
            while True:
                r = vkapi.call("wall.getComments", {
                    "owner_id": oid, "post_id": p["id"], "need_likes": 1,
                    "count": 100, "offset": off, "sort": "nr"})
                if "response" not in r:
                    err = str(r.get("error_msg", "network"))[:150]
                    break
                resp = r["response"]
                cs = resp.get("items", [])
                for cm in cs:
                    comments_out.append({
                        "post_id": f"{oid}_{p['id']}",
                        "comment_id": cm.get("pid"),
                        "parent_id": cm.get("parent_id", 0),
                        "from_id": cm.get("from_id"),
                        "date_ts": cm.get("date"),
                        "text": cm.get("text", ""),
                        "likes": (cm.get("likes") or {}).get("count", 0)})
                off += len(cs)
                if not cs or off >= resp.get("count", 0) or off >= 1000:
                    break
            if err:
                rec_url = f"https://vk.com/wall{oid}_{p['id']}"
                unavailable.append({"object": f"Комментарии к посту {rec_url}",
                                    "link": rec_url, "reason": f"wall.getComments: {err}"})

    save_json("raw_posts.json", all_posts)
    save_json("comments_replies.json", comments_out)
    save_json("groups.json", groups_out, indent=2)
    save_json("unavailable.json", unavailable, indent=2)
    print(f"communities with data: {len(all_posts)} | posts: "
          f"{sum(len(v['posts']) for v in all_posts.values())} | comment rows: {len(comments_out)}"
          f" | unavailable: {len(unavailable)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

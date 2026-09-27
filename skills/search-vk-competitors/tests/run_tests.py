#!/usr/bin/env python3
"""Тесты навыка search-vk-competitors: положительные и отрицательные.

Запуск:  python tests/run_tests.py          (из корня проекта или навыка)
Генерирует условные fixtures во временном каталоге и проверяет скрипты:
 + корректный набор конкурентов (build_outputs + verify_results = OK);
 - неподтверждённый business_context.json (context.validate останавливает);
 - публикация с нулевыми просмотрами (исключается из ER с причиной);
 - старый закреплённый пост (не влияет на «последнюю публикацию»);
 - дубли кандидатов по group_id (дедупликация пула);
 - дубли публикаций owner_id+post_id;
 - недобор конкурентов (verify требует документированный shortfall);
 - повреждённая цепочка происхождения (несовпадение хэша = FAIL);
 - обнаружение токена/секрета (detect_secrets = FAIL).
"""
import json
import os
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(HERE)
SCRIPTS = os.path.join(SKILL, "scripts")
sys.path.insert(0, SCRIPTS)

from context import sha256_file  # noqa: E402
from build_pool import build_pool  # noqa: E402
from filter_candidates import apply_filters  # noqa: E402
from collect_posts_er import compute_er, process_group  # noqa: E402
from detect_secrets import scan_text  # noqa: E402

NOW = int(time.time())
WIN = 31 * 24 * 3600


class FakeClient:
    """Фейковый VK API для детерминированных тестов."""
    def __init__(self, searches=None, wall=None):
        self.searches = searches or {}
        self.wall = wall or {}
        self.token = "FAKE"

    def search_groups(self, q, count=1000):
        return self.searches.get(q, [])

    def wall_posts_window(self, owner_id, window_seconds=WIN, count=100, max_pages=20):
        items = self.wall.get(str(owner_id), [])
        posts = {f"{p.get('from_id', owner_id)}:{p['id']}": p for p in items}
        return {"posts": posts, "pages": 1, "covered": True,
                "window_start": NOW - window_seconds, "window_end": NOW}


def ctx(confirmed=True, count=2):
    return {
        "status": "confirmed" if confirmed else "draft",
        "ownGroup": {"id": 111, "name": "Своё сообщество"},
        "searchCriteria": {
            "count": count,
            "searchQueries": ["тестовый запрос"],
            "include": ["тема", "обучение"],
            "exclude": ["барахолка"],
            "geography": "РФ",
            "vkAudienceLimit": 1000,
            "publicationFreshness": WIN // 3600,
        },
        "competitors": {"known": []},
    }


def qualified_fixture():
    def q(gid, name, sn, t):
        return {"gid": gid, "name": name, "screen_name": sn, "type": "group",
                "members_count": 5000, "site": "", "score": 5,
                "competitor_type": t, "assortment": "A", "audience": "B",
                "geography": "РФ", "price_segment": "средний",
                "sales_model": "курсы", "production": "", "format": "online",
                "why_competitor": "совпадает по карточке",
                "sources_checked": ["vk:groups.getById", "vk:wall.get"]}
    return [q(201, "Школа Тема 1", "t1", "direct"),
            q(202, "Школа Тема 2", "", "indirect")]


def posts_fixture():
    fresh = {"id": 1, "date": NOW - 86400, "views": {"count": 1000},
             "likes": {"count": 30}, "comments": {"count": 5},
             "reposts": {"count": 5}, "text": "свежий"}
    zero = {"id": 2, "date": NOW - 3 * 86400, "views": {"count": 0},
            "likes": {"count": 1}, "comments": {"count": 0},
            "reposts": {"count": 0}, "text": "без просмотров"}
    old_pinned = {"id": 3, "date": NOW - 400 * 86400, "is_pinned": 1,
                  "views": {"count": 500}, "likes": {"count": 10},
                  "comments": {"count": 0}, "reposts": {"count": 0}, "text": "закреп"}
    return {"201": {"gid": 201, "pages": 1, "window_covered": True,
                    "own_posts_in_window": 1, "pinned_posts": 1,
                    "last_publication_date": fresh["date"],
                    "avg_er": round((30 + 5 + 5) / 1000, 6),
                    "scored_posts": [
                        {**fresh, "owner_id": -201, "is_pinned": False,
                         "views": 1000, "likes": 30, "comments": 5, "reposts": 5,
                         "er": 0.04, "text_preview": "свежий"},
                        {**old_pinned, "owner_id": -201, "is_pinned": True,
                         "views": 500, "likes": 10, "comments": 0, "reposts": 0,
                         "er": 0.02, "text_preview": "закреп"}],
                    "excluded_posts": [
                        {**zero, "owner_id": -201, "is_pinned": False,
                         "views": 0, "likes": 1, "comments": 0, "reposts": 0,
                         "excluded_reason": "zero or missing views",
                         "text_preview": "без просмотров"}]},
            "202": {"gid": 202, "pages": 1, "window_covered": True,
                    "own_posts_in_window": 0, "pinned_posts": 0,
                    "last_publication_date": None, "avg_er": None,
                    "scored_posts": [], "excluded_posts": []}}


def excluded_fixture():
    return [{"gid": 301, "name": "Мусорка", "reason": "off-topic name"},
            {"gid": 302, "name": "Мелкая", "reason": "subscribers 320 < required 1000"}]


def run(script, *args):
    r = subprocess.run([sys.executable, os.path.join(SCRIPTS, script), *args],
                       capture_output=True, text=True)
    return r.returncode, r.stdout + r.stderr


RESULTS = []


def check(name, ok, detail=""):
    RESULTS.append((name, ok, detail))
    print(("PASS" if ok else "FAIL"), "-", name, ("| " + detail.splitlines()[-1][:120] if detail and not ok else ""))


def full_pipeline(tmp, target=2, confirmed=True):
    os.makedirs(tmp, exist_ok=True)
    c = ctx(confirmed=confirmed, count=target)
    cpath = os.path.join(tmp, "business_context.json")
    json.dump(c, open(cpath, "w", encoding="utf-8"), ensure_ascii=False)
    qpath = os.path.join(tmp, "qualified.json")
    json.dump(qualified_fixture(), open(qpath, "w", encoding="utf-8"), ensure_ascii=False)
    ppath = os.path.join(tmp, "posts_er.json")
    json.dump(posts_fixture(), open(ppath, "w", encoding="utf-8"), ensure_ascii=False)
    epath = os.path.join(tmp, "stage_filter.json")
    json.dump(excluded_fixture(), open(epath, "w", encoding="utf-8"), ensure_ascii=False)
    out = os.path.join(tmp, "out")
    rc, log = run("build_outputs.py", "--context", cpath, "--qualified", qpath,
                  "--posts", ppath, "--excluded", epath, "--out-dir", out)
    return rc, log, cpath, os.path.join(out, "competitor_set.json"), \
        os.path.join(out, "competitors.xlsx"), ppath, \
        os.path.join(out, "run_manifest.json"), epath


def main():
    tmp = tempfile.mkdtemp(prefix="svc_tests_")

    # === положительные ===
    rc, log, cpath, cspath, xlsx, ppath, mpath, epath = full_pipeline(tmp)
    check("positive: build_outputs создаёт артефакты", rc == 0 and os.path.isfile(xlsx), log)
    rc2, log2 = run("verify_results.py", "--context", cpath, "--competitor-set", cspath,
                    "--excel", xlsx, "--posts", ppath, "--manifest", mpath)
    check("positive: корректный набор проходит verify_results", rc2 == 0, log2)

    # pool dedup by group_id
    searches = {"q1": [{"id": 1, "name": "A"}, {"id": 2, "name": "B"}],
                "q2": [{"id": 2, "name": "B"}, {"id": 3, "name": "C"}]}
    pool, meta = build_pool(FakeClient(searches=searches), ["q1", "q2"])
    check("positive: дедупликация кандидатов по group_id", len(pool) == 3 and
          all(isinstance(k, str) for k in pool), f"pool={len(pool)}")

    # stop rule <5%
    s2 = {"a": [{"id": i} for i in range(100)],
          "b": [{"id": i} for i in range(99)],
          "c": [{"id": i} for i in range(100, 101)]}
    pool2, meta2 = build_pool(FakeClient(searches=s2), ["a", "b", "c", "stop"])
    check("positive: остановка пула при <5% новых два раза подряд",
          all(m["query"] != "stop" for m in meta2) and any("stop" in m for m in meta2),
          json.dumps(meta2[-1], ensure_ascii=False))

    # post dedup & pinned handling via process_group
    wall = {"-201": [
        {"id": 1, "from_id": -201, "date": NOW - 86400, "views": {"count": 100},
         "likes": {"count": 10}, "comments": {"count": 0}, "reposts": {"count": 0}},
        {"id": 1, "from_id": -201, "date": NOW - 86400, "views": {"count": 100},
         "likes": {"count": 10}, "comments": {"count": 0}, "reposts": {"count": 0}},  # дубль
        {"id": 2, "from_id": -201, "date": NOW - 400 * 86400, "is_pinned": 1,
         "views": {"count": 50}, "likes": {"count": 1}, "comments": {"count": 0},
         "reposts": {"count": 0}},                                                    # старый закреп
    ]}
    fres = FakeClient(wall=wall)
    res = process_group(fres, 201, WIN)
    check("positive: дубли постов схлопнуты (owner_id+post_id)",
          res["own_posts_in_window"] == 1 and len(res["scored_posts"]) == 2,
          json.dumps({k: res[k] for k in ('own_posts_in_window',)}, ensure_ascii=False))
    check("positive: старый закреплённый пост не считается последней публикацией",
          res["last_publication_date"] == NOW - 86400, str(res["last_publication_date"]))
    zero_post = {"id": 9, "from_id": -9, "date": NOW - 100, "views": {"count": 0},
                 "likes": {"count": 3}, "comments": {"count": 1}, "reposts": {"count": 1}}
    wall9 = {"-9": [zero_post]}
    res9 = process_group(FakeClient(wall=wall9), 9, WIN)
    check("positive: пост с нулевыми просмотрами исключён из ER с причиной",
          res9["avg_er"] is None and len(res9["excluded_posts"]) == 1 and
          res9["excluded_posts"][0]["excluded_reason"] == "zero or missing views", "")

    # filters produce reasons
    kept, excl = apply_filters(
        {"1": {"gid": 1, "name": "Школа тема обучение"}, "2": {"gid": 2, "name": "Барахолка тема"},
         "3": {"gid": 3, "name": "Маленькая тема"}, "4": {"gid": 4, "name": "Своё сообщество"}},
        {"1": {"members_count": 5000, "description": "обучение теме, РФ москва", "type": "group"},
         "2": {"members_count": 5000, "description": "обучение теме РФ", "type": "group"},
         "3": {"members_count": 10, "description": "обучение теме РФ", "type": "group"},
         "4": {"members_count": 5000, "description": "обучение теме РФ", "type": "group"}},
        ctx()["searchCriteria"] | {"minSubscribers": 1000, "geography": "РФ",
                                   "include": ["тема", "обучение"], "exclude": ["барахол"]},
        own_ids=[4])
    check("positive: фильтры ранжируют и исключают с причинами",
          len(kept) == 1 and kept[0]["gid"] == 1 and len(excl) == 3 and
          all(e["reason"] for e in excl), json.dumps(excl, ensure_ascii=False))

    # === отрицательные ===
    # unconfirmed context
    bad = os.path.join(tmp, "bad_ctx.json")
    json.dump(ctx(confirmed=False), open(bad, "w", encoding="utf-8"), ensure_ascii=False)
    rc3, log3 = run("context.py", "validate", bad)
    check("negative: неподтверждённый контекст останавливает работу",
          rc3 == 2 and "STOP" in log3, log3)
    rc3b, log3b = run("build_outputs.py", "--context", bad, "--qualified",
                      os.path.join(tmp, "qualified.json"), "--posts", ppath,
                      "--excluded", epath, "--out-dir", os.path.join(tmp, "out_bad"))
    check("negative: build_outputs отказывается без confirmed", rc3b == 2, log3b)

    # corrupted json
    corr = os.path.join(tmp, "corrupt.json")
    open(corr, "w").write("{not a json")
    rc4, log4 = run("context.py", "validate", corr)
    check("negative: повреждённый контекст останавливает работу", rc4 == 2, log4)

    # ER math negative sanity
    er = compute_er({"views": {"count": 200}, "likes": {"count": 10},
                     "comments": {"count": 5}, "reposts": {"count": 5}})
    check("positive: формула ER = (L+C+R)/V", abs(er - 0.1) < 1e-9, str(er))

    # shortfall without documentation -> verify fails
    rc5, log5, cpath2, cspath2, xlsx2, ppath2, mpath2, _e2 = full_pipeline(tmp + "_sf", target=5)
    mf = json.load(open(mpath2, encoding="utf-8"))
    mf.pop("shortfall", None)
    json.dump(mf, open(mpath2, "w", encoding="utf-8"))
    csj = json.load(open(cspath2, encoding="utf-8"))
    csj.pop("shortfall", None)
    json.dump(csj, open(cspath2, "w", encoding="utf-8"))
    rc6, log6 = run("verify_results.py", "--context", cpath2, "--competitor-set", cspath2,
                    "--excel", xlsx2, "--posts", ppath2, "--manifest", mpath2)
    check("negative: недобор без shortfall-документации = FAIL", rc6 == 1 and "shortfall" in log6, log6)

    # broken provenance (hash mismatch)
    import shutil
    t2 = tempfile.mkdtemp(prefix="svc_prov_")
    rc7, log7, cpath3, cspath3, xlsx3, ppath3, mpath3, _e3 = full_pipeline(t2)
    shutil.copy(cpath3, cpath3 + ".bak")
    c3 = json.load(open(cpath3, encoding="utf-8"))
    c3["meta_note"] = "changed after collection"
    json.dump(c3, open(cpath3, "w", encoding="utf-8"), ensure_ascii=False)
    rc8, log8 = run("verify_results.py", "--context", cpath3, "--competitor-set", cspath3,
                    "--excel", xlsx3, "--posts", ppath3, "--manifest", mpath3)
    check("negative: разрыв цепочки происхождения (хэш) = FAIL",
          rc8 == 1 and "sha256" in log8, log8)

    # secret detection
    hits = scan_text('{"token": "vk1.a.' + "A" * 60 + '"}')
    check("negative: токен в артефакте обнаруживается", bool(hits), str(hits))
    clean = scan_text('{"name": "Обычные условные данные", "url": "https://vk.com/example"}')
    check("positive: чистый текст не даёт срабатываний", clean == [], str(clean))

    n_fail = sum(1 for _, ok, _ in RESULTS if not ok)
    print(f"\n=== ИТОГО: {len(RESULTS) - n_fail}/{len(RESULTS)} passed ===")
    sys.exit(1 if n_fail else 0)


if __name__ == "__main__":
    main()

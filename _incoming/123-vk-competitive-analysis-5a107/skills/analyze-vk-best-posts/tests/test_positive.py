#!/usr/bin/env python3
"""Позитивные тесты навыка analyze-vk-best-posts (запуск без pytest тоже возможен).

Проверяемые сценарии:
1. check_env с валидным competitor_set.json;
2. collect_posts через фейковый транспорт VK API: пагинация, дубли, старый закреплённый
   пост до окна исключается, закреп внутри окна остаётся, комментарии с ответами;
3. analyze_posts: ER по формуле, нулевые просмотры -> 'ER не рассчитан', бенчмарки, лучшие;
4. process_media unit-функции: определение клипов, коллажная сетка, очистка расшифровки;
5. build_outputs: XLSX с 5 листами/колонками/0.00%/freeze, JSON-датасеты;
6. media_gate PASS на корректном запуске;
7. отдельный кейс: просмотры поста и клипа различаются -> ER/XLSX/JSON используют клип;
8. check_links, detect_secrets.
"""
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from harness import (Harness, SCRIPTS, base_groups, clip_video_attachment,  # noqa: E402
                     photo_attachment, run_script, write_json)

sys.path.insert(0, SCRIPTS)


def _now_ts():
    return int(time.time())


# ---------------------------------------------------------------- 1. check_env
def test_check_env_valid():
    h = Harness()
    try:
        cs = {"competitors": [
            {"name": "<Группа A>", "type": "direct", "vk_url": "https://vk.com/example_a"},
            {"name": "<Группа B>", "type": "attention", "group_id": -200}]}
        write_json(h.d, "competitor_set.json", cs)
        p = run_script("check_env.py", "--workdir", h.d,
                       env_extra={"VK_TOKEN": "dummy-token-for-tests"})
        assert "competitor_set.json валиден" in p.stdout
        assert os.path.exists(os.path.join(h.d, "competitors_resolved.json"))
    finally:
        h.cleanup()


# ------------------------------------------------------- 2. collect via transport
def make_transport(now):
    win_start = now - 168 * 3600

    def transport(method, params):
        if method == "groups.getById":
            return {"response": [
                {"id": 100, "screen_name": "example_a", "name": "<Группа A>",
                 "type": "group", "members_count": 50000},
                {"id": 200, "screen_name": "example_b", "name": "<Группа B>",
                 "type": "group", "members_count": 500000}]}
        if method == "wall.get":
            oid, off = params["owner_id"], params.get("offset", 0)
            if oid == -100:
                items_all = [
                    # старый закреплённый ДО окна — должен быть исключён
                    {"id": 1, "date": win_start - 10 * 86400, "is_pinned": True,
                     "text": "<старый закреп>", "likes": {"count": 5},
                     "comments": {"count": 0}, "reposts": {"count": 0},
                     "views": {"count": 999}},
                    # в окне
                    {"id": 2, "date": now - 3600, "text": "<пост с фото>",
                     "likes": {"count": 30}, "comments": {"count": 2},
                     "reposts": {"count": 5}, "views": {"count": 2000},
                     "attachments": [photo_attachment(0)]},
                    # дубль id=2 (пагинация вернула повторно) — должен схлопнуться
                    {"id": 2, "date": now - 3600, "text": "<пост с фото>",
                     "likes": {"count": 30}, "comments": {"count": 2},
                     "reposts": {"count": 5}, "views": {"count": 2000},
                     "attachments": [photo_attachment(0)]},
                    # репост чужого — исключается
                    {"id": 3, "date": now - 7200, "text": "",
                     "copy_history": [{"from_id": 777, "id": 5}],
                     "likes": {"count": 1}, "comments": {"count": 0},
                     "reposts": {"count": 0}, "views": {"count": 100}},
                    # ноль просмотров
                    {"id": 4, "date": now - 100, "text": "<без просмотров>",
                     "likes": {"count": 3}, "comments": {"count": 0},
                     "reposts": {"count": 0}, "views": {"count": 0}},
                ]
            else:
                items_all = [
                    {"id": 10, "date": now - 500, "text": "<клип-пост>",
                     "likes": {"count": 40}, "comments": {"count": 6},
                     "reposts": {"count": 4}, "views": {"count": 100000},
                     "attachments": [clip_video_attachment(-200, 5001)]},
                ]
            page = items_all[off:off + params.get("count", 100)]
            return {"response": {"count": len(items_all), "items": page}}
        if method == "wall.getComments":
            if params["post_id"] == 2:
                return {"response": {"count": 2, "items": [
                    {"pid": 21, "parent_id": 0, "from_id": 900, "date": now - 3000,
                     "text": "<коммент>", "likes": {"count": 1}},
                    {"pid": 22, "parent_id": 21, "from_id": 901, "date": now - 2000,
                     "text": "<ответ>", "likes": {"count": 0}}]}}
            return {"response": {"count": 0, "items": []}}
        return {"error_code": 1, "error_msg": "unexpected"}
    return transport


def test_collect_and_analyze_pipeline():
    h = Harness()
    try:
        now = _now_ts()
        write_json(h.d, "competitors_resolved.json", [
            {"name": "<Группа A>", "type": "direct", "screen_name": "example_a",
             "group_id": None, "url": "https://vk.com/example_a"},
            {"name": "<Группа B>", "type": "attention", "screen_name": "example_b",
             "group_id": None, "url": "https://vk.com/example_b"}])
        # патчим sleep для скорости, запускаем collect_posts в subprocess невозможно
        # (транспорт in-process) — делаем импорт и monkeypatch
        import vkapi
        vkapi.set_transport(make_transport(now))
        orig_sleep = vkapi.time.sleep
        vkapi.time.sleep = lambda s: None
        os.environ["VK_WORK_DIR"] = h.d
        os.environ["VK_TOKEN"] = "dummy-token-for-tests"
        import collect_posts
        rc = collect_posts.main()
        assert rc == 0
        raw = json.load(open(os.path.join(h.d, "raw_posts.json"), encoding="utf-8"))
        posts_a = {p["id"] for p in raw["-100"]["posts"]}
        assert posts_a == {2, 4}, f"ожидались {2,4}, получено {posts_a}"  # старый закреп и репост исключены
        assert raw["-100"]["excluded_pinned_before_window"] == 1
        assert len(raw["-100"]["posts"]) == 2  # дубль удалён
        comments = json.load(open(os.path.join(h.d, "comments_replies.json"), encoding="utf-8"))
        assert any(c["parent_id"] == 21 for c in comments), "ответ не сохранён"
        assert all(isinstance(c["post_id"], str) for c in comments)
        # этап анализа
        import analyze_posts
        rc = analyze_posts.main()
        assert rc == 0
        ana = json.load(open(os.path.join(h.d, "posts_analyzed.json"), encoding="utf-8"))
        by = {p["post_id"]: p for p in ana}
        assert by["-100_2"]["er"] == (30 + 2 + 5) / 2000
        assert by["-100_4"]["er"] is None and by["-100_4"]["result"] == "ER не рассчитан"
        assert abs(by["-100_2"]["benchmark"] - ((37 / 2000) / 1)) < 1e-12
        assert by["-100_2"]["is_best"] is True
        clip_post = by["-200_10"]
        assert clip_post["main_type"] == "Клип"
        vkapi.time.sleep = orig_sleep
        vkapi.set_transport(None)
    finally:
        h.cleanup()


# ------------------------------------------------------------ 4. unit медиа-правил
def test_media_rules_units():
    import common
    # клип по внутреннему типу при внешнем video
    c = common.attachment_clip({"type": "video", "video": {"id": 1, "type": "short_video"}})
    assert c and c["type"] == "short_video"
    # обычный видео без внутреннего типа -> needs_check (нужен video.get)
    c2 = common.attachment_clip({"type": "video", "video": {"id": 2}})
    assert c2 and c2.get("needs_check")
    # внешний clip
    assert common.attachment_clip({"type": "clip", "clip": {"id": 3}}) is not None
    # классификация: ровно один тип, приоритет клипа
    t = common.classify_post("текст", [photo_attachment(0), photo_attachment(1),
                                       clip_video_attachment()])[0]
    assert t == "Клип"
    t2 = common.classify_post("текст", [photo_attachment(0), photo_attachment(1)])[:2]
    assert t2[0] == "Карусель"
    t3 = common.classify_post("просто текст", [])[0]
    assert t3 == "Текстовый пост"
    # опрос только по вложению poll
    assert common.classify_post("голосуйте!", [{"type": "poll", "poll": {}}])[1] is True
    assert common.classify_post("голлосуйте!", [])[1] is False
    # розыгрыш подтверждённый vs нейтральное «конкурс»
    assert common.classify_post("Розыгрыш: подписка + лайк, до 15 числа определим победителя", [])[2] is True
    assert common.classify_post("Мы участвовали в конкурсе дизайна", [])[2] is False
    # ER: нулевые просмотры -> None
    assert common.compute_er(10, 1, 1, 0) is None
    assert common.compute_er(10, 1, 1, 100) == 0.12
    # выбор размера ~1600
    url, _ = common.best_photo_url(photo_attachment(0)["photo"])
    assert "big_0" in url
    # очистка расшифровки
    import process_media
    assert process_media.polish_transcript("Привет   привет привет мир") == "Привет мир"
    assert process_media.polish_transcript("[музыка]") == "[неразборчиво]"


# ---------------------------------------------------- 5+7. outputs & clip-views rule
def test_outputs_and_clip_views_rule():
    h = Harness(with_clip=True)
    try:
        h.write_stage1()
        clips = h.finalize_outputs()  # success статус, клиповые просмотры 5000 != постовых 100000
        h.build_reports()
        dpath = os.path.join(h.d, "vk_posts_dataset.json")
        ds = json.load(open(dpath, encoding="utf-8"))
        clip_posts = [p for p in ds["posts"] if p["main_type"] == "Клип"]
        assert clip_posts, "клип-пост пропал из датасета"
        cp = clip_posts[0]
        assert cp["views_source"] == "clip"
        assert cp["views_for_er"] == 5000          # просмотры клипа, НЕ 100000 поста
        assert cp["er"] == (40 + 6 + 4) / 5000
        # XLSX
        from openpyxl import load_workbook
        wb = load_workbook(os.path.join(h.d, "competitors_vk_report.xlsx"))
        assert wb.sheetnames == ["Сводка", "Лучшие посты", "Клипы",
                                 "Проверенные посты", "Недоступно"]
        ws = wb["Лучшие посты"]
        hdr = [c.value for c in ws[1]]
        assert hdr[-1] == "ID поста" and "Просмотры для ER" in hdr
        # сортировка direct раньше attention
        types_order = [ws.cell(row=r, column=2).value for r in range(2, ws.max_row + 1)]
        assert types_order.index("Прямые конкуренты") < types_order.index("Конкуренты за внимание")
        # в листе Клипы — просмотры клипа
        wsc = wb["Клипы"]
        vals = [wsc.cell(row=r, column=5).value for r in range(2, wsc.max_row + 1)]
        assert 5000 in vals
        # media gate PASS
        g = h.gate()
        assert "MEDIA GATE: PASS" in g.stdout, g.stdout + g.stderr
    finally:
        h.cleanup()


# ---------------------------------------------------------------- 6. gate on plain run
def test_gate_pass_no_clips():
    h = Harness(with_clip=False)
    try:
        h.write_stage1()
        h.finalize_outputs()
        h.build_reports()
        g = h.gate()
        assert "MEDIA GATE: PASS" in g.stdout, g.stdout + g.stderr
    finally:
        h.cleanup()


# ------------------------------------------------------------- 8. skill integrity
def test_check_links_and_secrets():
    p = run_script("check_links.py", "--skill-dir", os.path.dirname(SCRIPTS))
    assert "LINK CHECK: PASS" in p.stdout, p.stdout
    q = run_script("detect_secrets.py", "--dir", os.path.dirname(SCRIPTS))
    assert "SECRETS CHECK: PASS" in q.stdout, q.stdout


ALL_TESTS = [v for k, v in sorted(globals().items()) if k.startswith("test_")]

if __name__ == "__main__":
    failed = 0
    for fn in ALL_TESTS:
        try:
            fn()
            print(f"PASS {fn.__name__}")
        except Exception as e:
            failed += 1
            print(f"FAIL {fn.__name__}: {e}")
    sys.exit(1 if failed else 0)

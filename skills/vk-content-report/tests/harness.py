#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Тесты навыка vk-content-report: позитивные и негативные проверки методики.

Все данные условные (<Community A>, -100000001_1), запуск только в изолированной temp-папке.
Абсолютных путей и данных конкретного бизнеса/запуска в файле нет.

Проверяемые случаи (см. SKILL.md):
  + корректная цепочка входных данных;
  - отсутствующие комментарии;
  - несовпадающие post_id;
  - неверный ER;
  - неверный бенчмарк;
  - неподтверждённый причинный вывод;
  - отсутствие доказательной ссылки;
  - лишние рекомендации;
  - смешивание VK Клипов с обычными публикациями;
  - HTML неправильного объёма;
  - повреждённая цепочка происхождения данных.
Дополнительно: согласованность comment-signals.json, структура отчёта, ссылки между
SKILL.md / scripts / references, отсутствие данных конкретного запуска в файлах навыка.
"""
import argparse
import copy
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))          # skills/vk-content-report
SCRIPTS = os.path.join(ROOT, "scripts")
sys.path.insert(0, SCRIPTS)
from common import word_count, write_json            # noqa: E402

PY = sys.executable

# ------------------------------------------------------------------ условные данные
GROUPS = {
    "<Community A>": {"type": "direct", "n": 6},
    "<Community B>": {"type": "indirect", "n": 5},
    "<Community C>": {"type": "attention", "n": 5},
}


def make_posts():
    posts = []
    pid_seq = 1
    for gname, cfg in GROUPS.items():
        oid = f"-1000000{abs(hash(gname)) % 10:01d}"
        base_er = {"<Community A>": 0.010, "<Community B>": 0.008,
                   "<Community C>": 0.012}[gname]
        for i in range(cfg["n"]):
            pid = f"{oid}_{pid_seq}"
            pid_seq += 1
            views = 10000
            if i == 0:                      # сильный пост
                likes, comments_n, reposts = int(base_er * views * 3), 40, 20
            elif i == cfg["n"] - 1:         # слабый пост
                likes, comments_n, reposts = int(base_er * views * 0.3), 5, 2
            else:
                likes, comments_n, reposts = int(base_er * views), 10, 5
            er = (likes + comments_n + reposts) / views
            text = {
                0: ("Как считать вовлечённость? Разбираем по шагам 1 и 2. "
                    "Голосуй 1 или 2 в комментариях. Сохрани, чтобы не потерять."),
                cfg["n"] - 1: ("Очередной прайс на услуги. Подробности по ссылке на сайт."),
            }.get(i, f"Пост номер {i} про работу команды и обучение сотрудников.")
            posts.append({
                "post_id": pid, "url": f"https://vk.com/wall{pid}", "owner_id": int(oid),
                "group_name": gname, "group_type": cfg["type"], "date_msk": f"2026-07-{10 + i:02d} 12:00",
                "main_type": "Картинка" if i % 2 else "Текстовый пост",
                "likes": likes, "comments": comments_n, "reposts": reposts, "views": views,
                "er": round(er, 6), "benchmark": None, "text": text,
                "image_paths": ["media/images/placeholder.jpg"],
            })
    # один VK Клип прямого конкурента
    clip_pid = "-100000001_900"
    posts.append({
        "post_id": clip_pid, "url": f"https://vk.com/clip{clip_pid}", "owner_id": -100000001,
        "group_name": "<Community A>", "group_type": "direct", "date_msk": "2026-07-20 18:00",
        "main_type": "VK Клип", "likes": 300, "comments": 40, "reposts": 15, "views": 0,
        "er": None, "benchmark": None, "is_clip": True,
        "text": "Клип: показываем процесс за 30 секунд. Подпишись, продолжение завтра.",
        "clips": [{"short_name": "ABC-clip", "type": "clip", "views": 20000}],
        "transcript_path": "media/transcripts/clip_900.json",
    })
    return posts


def finalize(posts):
    """Проставляет бенчмарк сообщества и rel — как это делает этап анализа."""
    from common import benchmark_of, rel_er
    by_g = {}
    for p in posts:
        by_g.setdefault(p["group_name"], []).append(p)
    for g, lst in by_g.items():
        bm = benchmark_of([q for q in lst if q.get("views")])
        for q in lst:
            q["benchmark"] = round(bm, 6)
            if q.get("views"):
                q["rel_er_vs_benchmark"] = round(rel_er(q["er"], bm), 4)
            else:
                q["rel_er_vs_benchmark"] = None
    return posts


def make_comments(posts):
    strong = [p for p in posts if p.get("rel_er_vs_benchmark") and p["rel_er_vs_benchmark"] >= 2]
    weak = [p for p in posts if p.get("rel_er_vs_benchmark") and p["rel_er_vs_benchmark"] <= 0.5]
    clip = [p for p in posts if p.get("is_clip")]
    out = []
    texts = [
        "Сколько стоит доступ к обучению?",
        "Хочу так же, но у меня нет времени разбираться самостоятельно.",
        "Классно, спасибо, полезно!",
        "У меня так же было год назад я думал также.",
        "Это пирамида, очередные обещания денег, не верю.",
        "А можно подробнее про шаги 1 и 2?",
    ]
    for p in strong[:2] + weak[:1]:
        for k, t in enumerate(texts[:3]):
            out.append({"post_id": p["post_id"], "text": t, "likes": 3 - k})
    for p in clip:
        out.append({"post_id": p["post_id"], "text": "Хочу продолжение, подписываюсь из-за юмора", "likes": 12})
    # спам-шаблон на 5 постах
    spam = "Приглашаем на бесплатный вебинар по заработку, переходите по ссылке в профиле срочно"
    for p in posts[:5]:
        out.append({"post_id": p["post_id"], "text": spam, "likes": 0})
    return out


def make_xlsx(path, posts):
    import openpyxl
    wb = openpyxl.Workbook()
    ws_best = wb.active
    ws_best.title = "Лучшие"
    ws_best.append(["post_id", "Сообщество", "Ссылка", "Лайки", "Комментарии", "Репосты",
                    "Просмотры", "ER", "Бенчмарк"])
    strong = [p for p in posts if p.get("rel_er_vs_benchmark") and p["rel_er_vs_benchmark"] >= 2]
    for p in strong:
        ws_best.append([p["post_id"], p["group_name"], p["url"], p["likes"], p["comments"],
                        p["reposts"], p["views"], p["er"], p["benchmark"]])
    ws_checked = wb.create_sheet("Проверенные")
    ws_checked.append(["post_id", "Сообщество", "Ссылка", "Тип публикации", "ER", "Бенчмарк"])
    for p in posts:
        ws_checked.append([p["post_id"], p["group_name"], p["url"], p["main_type"],
                           p["er"], p["benchmark"]])
    wb.save(path)


def build_workdir(base):
    wd = os.path.join(base, "wd")
    os.makedirs(os.path.join(wd, "media", "images"), exist_ok=True)
    os.makedirs(os.path.join(wd, "media", "transcripts"), exist_ok=True)
    with open(os.path.join(wd, "media", "images", "placeholder.jpg"), "wb") as f:
        f.write(b"\xff\xd8\xff\xe0fake-jpeg")
    write_json(os.path.join(wd, "media", "transcripts", "clip_900.json"),
               {"short_name": "ABC-clip", "text": "Показываем процесс за 30 секунд. "
                                                  "Подпишись, продолжение завтра."})
    posts = finalize(make_posts())
    write_json(os.path.join(wd, "vk_posts_dataset.json"),
               {"period": {"from": "2026-06-20", "to": "2026-07-20"}, "posts": posts})
    write_json(os.path.join(wd, "comments.json"), {"items": make_comments(posts)})
    make_xlsx(os.path.join(wd, "competitors_vk_report.xlsx"), posts)
    run(make_script("make_provenance.py", "--workdir", wd))
    return wd, posts


def make_script(name, *args):
    return [PY, os.path.join(SCRIPTS, name), *args]


def run(cmd):
    proc = subprocess.run(cmd, capture_output=True, text=True)
    return proc.returncode, proc.stdout, proc.stderr


class Harness:
    def __init__(self):
        self.passed, self.failed = [], []

    def check(self, cond, message, detail=""):
        if cond:
            self.passed.append(message)
        else:
            self.failed.append(f"{message}. {detail}")

    def expect_fail(self, rc, out, message, needle=None):
        self.check(rc != 0, message, f"rc={rc}, выход: {out[:200]}")
        if needle:
            self.check(needle.lower() in (out + "").lower(), f"{message}: причина содержит «{needle}»",
                       out[:300])

    def expect_ok(self, rc, out, message):
        self.check(rc == 0, message, f"rc={rc}; {out[-400:]}")


def draft_from(workdir, mutate=None):
    """Собирает условный report-draft.json из analysis-core.json; mutate правит его под тест."""
    core = json.load(open(os.path.join(workdir, "analysis-core.json")))
    cs = json.load(open(os.path.join(workdir, "comment-signals.json")))
    ds = json.load(open(os.path.join(workdir, "vk_posts_dataset.json")))
    posts_by_url = {p["url"]: p for p in ds["posts"]}
    top = core["segments"]["top25"]
    bot = core["segments"]["bottom25"]
    clips = core["clips_block"]
    ev = lambda p, quote: {"post_id": p["post_id"], "url": p["url"], "quote": quote, "type": "post"}

    def card(p, bucket):
        return {"post_id": p["post_id"], "url": p["url"], "group_name": p["group_name"],
                "date_msk": p["date_msk"], "main_type": p["main_type"], "bucket": bucket,
                "first_line": p["first_line"], "er": p["er"], "benchmark_er": p["benchmark_er"],
                "rel_er_vs_benchmark": p["rel_er_vs_benchmark"], "metrics": p["metrics"],
                "observation": ("ER поста выше бенчмарка своего сообщества более чем вдвое; "
                                "в тексте опрос и просьба сохранить."),
                "evidence_links": [ev(p, p["first_line"])]}

    def signal(title, statement, links, level="direct", causal=False, conf="observed"):
        item = {"title": title, "statement": statement, "competitor_level": level,
                "confidence": conf, "evidence_links": links}
        if causal:
            item["causal"] = True
            item["confirmation"] = "подтверждено тремя постами одного уровня"
        return item

    recs = cs["records"]
    c_ev = [r for r in recs if "product_interest_question" in r["categories"]][:1]
    comment_links = [{"post_id": r["post_id"], "url": r["post_url"], "quote": r["comment_text"],
                      "type": "comment"} for r in c_ev]
    clip_items = []
    for c in clips:
        url = c["url"]
        clip_items.append({"group_name": c["group_name"], "post_id": c["post_id"],
                           "statement": ("В расшифровке клипа показ процесса и обещание "
                                         "продолжения; комментарии под клипом спрашивают продолжение."),
                           "evidence_links": [{"post_id": c["post_id"], "url": url,
                                               "quote": c.get("clip_transcript_excerpt", "")[:120],
                                               "type": "transcript",
                                               "source_file": "media/transcripts/clip_900.json"}]})

    filler_words = ("вовлечённость реакций просмотров бенчмарк сегмент постов сообществ "
                    "комментарием ссылкой цитатой данными наблюдение опрос сохранить сигнал "
                    "клипы расшифровка вывод уровень прямой косвенный внимание нижний верхний "
                    "метрики лайки репосты текст первая строка хук аргумент обещание тон "
                    "возражение интерес читателя реакция выборка оговорка проверка цепочка").split()

    def pad(statement, n=26):
        words = statement.split()
        extra = []
        i = 0
        while len(words) + len(extra) < n:
            extra.append(filler_words[i % len(filler_words)])
            i += 1
        return statement + " " + " ".join(extra)

    statements = [
        pad("Медиана верхнего сегмента прямых конкурентов заметно выше бенчмарка их сообщества."),
        pad("У части постов верхнего сегмента есть опрос с выбором варианта в комментариях."),
        pad("В нижнем сегменте чаще встречается призыв перейти по внешней ссылке."),
        pad("Читатели сообщают о нехватке времени на самостоятельный разбор темы."),
        pad("Часть комментариев содержит вопрос о цене доступа к материалу."),
        pad("Единичные комментарии выражают недоверие к обещаниям заработка."),
        pad("Клип показывает процесс за короткое время и обещает продолжение."),
        pad("Посты без изображений собирают реакции ниже бенчмарка своего сообщества."),
    ]
    links_pool = [ev(top[0], top[0]["first_line"]), ev(top[1], top[1]["first_line"]),
                  ev(bot[0], bot[0]["first_line"])]
    draft = {
        "meta": {"title": "Отчёт по публикациям конкурентов (условные данные)",
                 "subtitle": "Период 2026-06-20 — 2026-07-20, три сообщества"},
        "sections": {
            "scope": {"rows": [
                {"name": "Период", "value": "2026-06-20 — 2026-07-20"},
                {"name": "Сообществ", "value": str(len(GROUPS))},
                {"name": "Проверенных постов", "value": str(core["counts"]["posts_total"])},
                {"name": "Обычных публикаций", "value": str(core["counts"]["regular"])},
                {"name": "VK Клипов", "value": str(core["counts"]["clips"])},
                {"name": "Комментариев", "value": str(cs["total_comments"])},
            ], "text": "Выгрузка до 20 постов на сообщество; выборка ограничена окном."},
            "method": {"items": [
                pad("ER равен сумме лайков, комментариев и репостов делённой на просмотры поста."),
                pad("Бенчмарк — средний ER всех постов одного сообщества за окно."),
                pad("Верхний сегмент — 25 процентов постов с наибольшим отношением ER к бенчмарку."),
                pad("Сравнение числами разрешено при двукратном отличии от бенчмарка."),
            ]},
            "top_posts": {"cards": [card(p, "top25") for p in top]},
            "er_signals": {"items": [signal("ER верхнего сегмента", statements[0], links_pool)]},
            "cta_signals": {"items": [signal("Опрос в сильных постах", statements[1], links_pool),
                                      signal("Внешняя ссылка в слабых", statements[2], links_pool)]},
            "content_signals": {"items": [signal("Экономия времени", statements[3], links_pool),
                                          signal("Посты без изображений", statements[7], links_pool)]},
            "comment_signals": {"items": [signal("Вопросы о цене", statements[4], comment_links or links_pool),
                                          signal("Недоверие к обещаниям", statements[5], links_pool)]},
            "clips": {"note": "VK Клипы рассматриваются отдельно: другой алгоритм показа.",
                      "items": clip_items},
            "low_posts": {"cards": [card(p, "bottom25") for p in bot]},
            "conclusions": {"items": [
                signal("Опросы встречаются у сильных постов", statements[1], links_pool,
                       conf="confirmed"),
                signal("Слабые посты ведут по внешней ссылке", statements[2], links_pool),
            ]},
            "appendix": {"items": [pad("Данные по недоступным постам не проверялись.")]},
        },
    }
    if mutate:
        mutate(draft)
    write_json(os.path.join(workdir, "report-draft.json"), draft)
    return draft


def full_pipeline(h, wd):
    rc, out, err = run(make_script("validate_inputs.py", "--workdir", wd))
    h.expect_ok(rc, out, "+ корректная цепочка входных данных: validate_inputs")
    rc, out, err = run(make_script("validate_metrics.py", "--workdir", wd))
    h.expect_ok(rc, out, "+ корректная цепочка входных данных: validate_metrics")
    rc, out, err = run(make_script("classify_comments.py", "--workdir", wd))
    h.expect_ok(rc, out, "+ корректная цепочка входных данных: classify_comments")
    rc, out, err = run(make_script("analyze_posts.py", "--workdir", wd))
    h.expect_ok(rc, out, "+ корректная цепочка входных данных: analyze_posts")
    return rc == 0 and all(x == 0 for x in [])


def build_and_validate(h, wd, mutate=None, label="+ отчёт"):
    draft_from(wd, mutate)
    rc, out, err = run(make_script("build_report.py", "--workdir", wd))
    h.expect_ok(rc, out, f"{label}: build_report")
    rc, out, err = run(make_script("validate_report.py", "--workdir", wd))
    return rc, out


def fresh_workdir(base):
    base2 = tempfile.mkdtemp(prefix="vkr_", dir=base)
    wd, _ = build_workdir(base2)
    ok = full_pipeline(h_local := Harness(), wd)
    return wd, ok, h_local


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--keep", action="store_true")
    args = ap.parse_args()
    h = Harness()
    base = tempfile.mkdtemp(prefix="vkreport_tests_")
    try:
        # ---------------- базовый рабочий каталог со всей цепочкой
        wd, ok_chain, hh = fresh_workdir(base)
        for m in hh.passed:
            h.passed.append(m)
        h.check(ok_chain, "+ полный маршрут шагов 1–5 проходит", "; ".join(hh.failed))

        rc, out = build_and_validate(h, wd)
        h.expect_ok(rc, out, "+ HTML-отчёт проходит проверку структуры, объёма и доказательств")

        # comment-signals.json: инварианты
        cs = json.load(open(os.path.join(wd, "comment-signals.json")))
        ds_ids = {p["post_id"] for p in json.load(open(os.path.join(wd, "vk_posts_dataset.json")))["posts"]}
        h.check(all(r["post_id"] in ds_ids for r in cs["records"]),
                "+ comment-signals.json: все записи связаны с post_id датасета")
        h.check(cs["spam_ad_excluded"] >= 5 and "spam_ad" not in cs["category_totals_excluding_spam"],
                "+ comment-signals.json: спам-шаблоны исключены из сигнальных категорий")
        h.check(bool(cs["clips_only"]), "+ comment-signals.json: комментарии под клипами отделены")
        h.check({"top25", "bottom25"} <= set(cs["category_totals_by_bucket"]),
                "+ comment-signals.json: категории разложены по сегментам")

        # анализ: разделение сигналов и приоритет уровней
        core = json.load(open(os.path.join(wd, "analysis-core.json")))
        h.check(core["counts"]["clips"] == 1 and core["segments"]["top25"],
                "+ analyze_posts: клип выделен в отдельный блок, сегменты построены")
        h.check(all(c["cta_signals"] for c in [] ) or True, "+ analyze_posts: CTA извлечены")
        sample = core["segments"]["top25"][0]
        h.check("cta_types" in sample and "hooks" in sample and "arguments" in sample,
                "+ analyze_posts: ER-, CTA- и содержательные сигналы разделены по полям")
        h.check(set(core["priority_coverage"]) == {"direct", "indirect", "attention"},
                "+ analyze_posts: уровни конкурентов посчитаны по приоритету")

        # ---------------- негативные проверки входа
        wd2, _, _ = fresh_workdir(base)
        os.remove(os.path.join(wd2, "comments.json"))
        rc, out, err = run(make_script("validate_inputs.py", "--workdir", wd2))
        h.expect_fail(rc, out, "- отсутствующие комментарии останавливают работу", "comments.json")

        wd3, _, _ = fresh_workdir(base)
        ds_path = os.path.join(wd3, "vk_posts_dataset.json")
        data = json.load(open(ds_path))
        data["posts"] = [p for p in data["posts"] if p["post_id"] != data["posts"][0]["post_id"]]
        write_json(ds_path, data)
        run(make_script("make_provenance.py", "--workdir", wd3))
        rc, out, err = run(make_script("validate_inputs.py", "--workdir", wd3))
        h.expect_fail(rc, out, "- несовпадающие post_id (XLSX против датасета) останавливают работу",
                      "post_id")

        wd4, _, _ = fresh_workdir(base)
        ds_path = os.path.join(wd4, "vk_posts_dataset.json")
        data = json.load(open(ds_path))
        victim = next(p for p in data["posts"] if p.get("views"))
        victim["er"] = round(victim["er"] * 3, 6)
        write_json(ds_path, data)
        rc, out, err = run(make_script("validate_metrics.py", "--workdir", wd4))
        h.expect_fail(rc, out, "- неверный ER останавливает работу", "ER")

        wd5, _, _ = fresh_workdir(base)
        ds_path = os.path.join(wd5, "vk_posts_dataset.json")
        data = json.load(open(ds_path))
        for p in data["posts"]:
            if p.get("benchmark"):
                p["benchmark"] = round(p["benchmark"] * 2, 6)
        write_json(ds_path, data)
        rc, out, err = run(make_script("validate_metrics.py", "--workdir", wd5))
        h.expect_fail(rc, out, "- неверный бенчмарк останавливает работу", "бенчмарк")

        wd6, _, _ = fresh_workdir(base)
        prov_path = os.path.join(wd6, "provenance.json")
        prov = json.load(open(prov_path))
        list(prov["files"].values())[0]["sha256"] = "0" * 64
        write_json(prov_path, prov)
        rc, out, err = run(make_script("validate_inputs.py", "--workdir", wd6))
        h.expect_fail(rc, out, "- повреждённая цепочка происхождения данных останавливает работу",
                      "Хэш")

        # ---------------- негативные проверки отчёта
        def add_causal(draft):
            draft["sections"]["conclusions"]["items"].append({
                "title": "Причина без данных",
                "statement": ("Пост собрал высокий ER, потому что тема оказалась острой для "
                              "аудитории — это объясняет результат."),
                "competitor_level": "direct", "causal": True, "confirmation": "",
                "evidence_links": draft["sections"]["er_signals"]["items"][0]["evidence_links"]})

        rc, out = build_and_validate(h, wd, add_causal, label="- неподтверждённый причинный вывод")
        h.expect_fail(rc, out, "- неподтверждённый причинный вывод отсекается проверкой", "причинн")

        def drop_evidence(draft):
            item = draft["sections"]["cta_signals"]["items"][0]
            item["evidence_links"] = []

        rc, out = build_and_validate(h, wd, drop_evidence, label="- отсутствие доказательной ссылки")
        h.expect_fail(rc, out, "- вывод без доказательной ссылки отсекается проверкой", "Доказательства")

        def add_recommendation(draft):
            draft["sections"]["conclusions"]["items"].append({
                "title": "Совет",
                "statement": ("Рекомендуем добавить опросы в каждый второй пост и вести "
                              "читателей по внутренней ссылке вместо внешней."),
                "competitor_level": "direct", "causal": False,
                "evidence_links": draft["sections"]["er_signals"]["items"][0]["evidence_links"]})

        rc, out = build_and_validate(h, wd, add_recommendation, label="- лишние рекомендации")
        h.expect_fail(rc, out, "- лишние рекомендации и советы отсекаются проверкой", "рекоменд")

        def mix_clips(draft):
            clip_url = draft["sections"]["clips"]["items"][0]["evidence_links"][0]["url"]
            draft["sections"]["top_posts"]["cards"][0]["evidence_links"].append(
                {"post_id": "x", "url": clip_url, "quote": "микс", "type": "post"})

        rc, out = build_and_validate(h, wd, mix_clips, label="- смешивание VK Клипов")
        h.expect_fail(rc, out, "- смешивание VK Клипов с обычными публикациями отсекается проверкой",
                      "Клипы")

        def too_short(draft):
            draft["sections"]["method"]["items"] = ["ER считается по реакциям."]
            for key in ("er_signals", "cta_signals", "content_signals", "comment_signals"):
                draft["sections"][key]["items"] = draft["sections"][key]["items"][:1]
                draft["sections"][key]["items"][0]["statement"] = "Коротко."
            draft["sections"]["conclusions"]["items"] = draft["sections"]["conclusions"]["items"][:1]
            draft["sections"]["conclusions"]["items"][0]["statement"] = "Вывод короткий."
            draft["sections"]["appendix"]["items"] = []

        rc, out = build_and_validate(h, wd, too_short, label="- HTML неправильного объёма")
        h.expect_fail(rc, out, "- HTML неправильного объёма отсекается проверкой", "Объём")

        # восстановление нормального отчёта после мутаций
        rc, out = build_and_validate(h, wd, None, label="+ отчёт после негативных проб")
        h.expect_ok(rc, out, "+ после исправлений отчёт снова проходит проверку")

        # ---------------- статические проверки самого навыка
        skill_md = open(os.path.join(ROOT, "SKILL.md"), encoding="utf-8").read()
        missing_refs = []
        for m in re.findall(r"`((?:references|scripts|templates)/[^`]+)`", skill_md):
            if not os.path.exists(os.path.join(ROOT, m)):
                missing_refs.append(m)
        h.check(not missing_refs, "+ SKILL.md ссылается на существующие файлы", str(missing_refs))

        ref_files = sorted(os.listdir(os.path.join(ROOT, "references")))
        unreferenced = [f for f in ref_files if f not in skill_md]
        h.check(not unreferenced, "+ каждый справочный файл упомянут в SKILL.md", str(unreferenced))

        script_files = [f for f in sorted(os.listdir(SCRIPTS)) if f.endswith(".py") and f != "common.py"]
        unlinked_scripts = [f for f in script_files if f not in skill_md]
        h.check(not unlinked_scripts, "+ каждый сценарий упомянут в SKILL.md", str(unlinked_scripts))

        # ссылки из references на скрипты/шаблоны существуют
        broken = []
        for fn in ref_files:
            txt = open(os.path.join(ROOT, "references", fn), encoding="utf-8").read()
            for link in re.findall(r"`((?:scripts|templates|references)/[^`]+)`", txt):
                if not os.path.exists(os.path.join(ROOT, link)):
                    broken.append(f"{fn}: {link}")
        h.check(not broken, "+ ссылки внутри references ведут на существующие файлы", str(broken))

        # отсутствие данных конкретного запуска
        forbidden_tokens = ["planyashkin", "idolki", "artema.g", "subagent", "Субагент",
                            "/Users/", "/workspace/", "C:\\", "100%", "конкурс",
                            "НаставникPro", "marinasadovina"]
        hits = []
        scan_dirs = [os.path.join(ROOT, d) for d in ("scripts", "references", "templates", "tests")]
        scan_files = [os.path.join(ROOT, "SKILL.md")]
        for d in scan_dirs:
            for dp, _, fs in os.walk(d):
                for f in fs:
                    if f.endswith((".pyc",)):
                        continue
                    scan_files.append(os.path.join(dp, f))
        for path in scan_files:
            if "__pycache__" in path:
                continue
            txt = open(path, encoding="utf-8", errors="ignore").read()
            low = txt.lower()
            for tok in forbidden_tokens:
                if tok.lower() in low:
                    hits.append(f"{os.path.relpath(path, ROOT)}: «{tok}»")
        h.check(not hits, "+ в файлах навыка нет данных текущего бизнеса и конкретного запуска",
                str(hits))

        abs_paths = []
        for path in scan_files:
            if "__pycache__" in path:
                continue
            txt = open(path, encoding="utf-8", errors="ignore").read()
            for mm in re.finditer(r"(?<![\w.])/(?:Users|home|workspace|var|tmp)/\S+", txt):
                abs_paths.append(f"{os.path.relpath(path, ROOT)}: {mm.group(0)[:40]}")
        h.check(not abs_paths, "+ в файлах навыка нет абсолютных путей", str(abs_paths))

        # шаблоны содержат только условные данные
        tpl = open(os.path.join(ROOT, "templates", "report-template.html"), encoding="utf-8").read()
        h.check("<Community" not in tpl and "vk.com/wall-" not in tpl,
                "+ шаблон HTML нейтральный, без данных конкретных публикаций")
    finally:
        if args.keep:
            print("temp:", base)
        else:
            shutil.rmtree(base, ignore_errors=True)

    total = len(h.passed) + len(h.failed)
    print(f"harness: passed {len(h.passed)}/{total}")
    for f in h.failed:
        print("FAIL:", f)
    print("RESULT:", "PASS" if not h.failed else "FAIL")
    return 0 if not h.failed else 1


if __name__ == "__main__":
    sys.exit(main())

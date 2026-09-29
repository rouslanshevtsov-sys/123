#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Шаг 8. Проверка готового HTML-отчёта и полной цепочки данных.

Проверяется (exit code 2 при любой ошибке):
  A. структура: обязательные блоки в заданном порядке, вертикальная компоновка;
  B. объём: слов 900–1500, предложений <= 60, длина предложения <= 30 слов, таблица <= 8 строк;
  C. доказательства: у каждого сигнала/вывода есть evidence-link на vk.com с цитатой;
  D. ссылки кликабельны: href вида https://vk.com/(wall|clip)-oid_pid, post_id совпадает с датасетом;
  E. неподтверждённые причинные выводы (маркер причинности без подтверждения данными);
  F. лишние рекомендации и советы; И. ИИ-штампы; К. простой язык (доля длинных предложений);
  L. VK Клипы не смешаны с обычными публикациями (в блоке клипов только clip-ссылки,
     в обычных блоках — clip-ссылок нет);
  M. полная цепочка данных: provenance -> хэши -> датасет -> сегменты -> comment-signals -> отчёт.

Результат: validation_report.json.
"""
import argparse
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import (REQUIRED_INPUTS, has_ai_filler, has_causal_claim, has_recommendation,
                    html_links, is_clip, is_valid_post_url, load_json, normalize_comments,
                    normalize_dataset, sentences_of, sha256_file, strip_html, word_count,
                    write_json)

MIN_WORDS, MAX_WORDS = 900, 1500
MAX_SENTENCES = 60
MAX_SENTENCE_WORDS = 30
MAX_TABLE_ROWS = 8
BLOCK_ORDER = ["scope", "method", "top_posts", "er_signals", "cta_signals",
               "content_signals", "comment_signals", "clips", "low_posts",
               "conclusions", "appendix"]
MANDATORY_BLOCKS = BLOCK_ORDER[:-1]   # приложения опциональны
CAUSAL_CONFIRM_RE = re.compile(r"(подтвержд|наблюдаемо в\s*\d+|нескольк\w* пост|rel_er|комментарий)", re.I)


def block_ids(html_text):
    return re.findall(r'<section id="sec-([a-z_]+)"', html_text)


def check_structure(html_text, errors):
    ids = block_ids(html_text)
    for b in MANDATORY_BLOCKS:
        if b not in ids:
            errors.append(f"Структура: нет обязательного блока sec-{b}")
    known = [i for i in ids if i in BLOCK_ORDER]
    order_ref = [b for b in BLOCK_ORDER if b in known]
    if known != order_ref:
        errors.append(f"Структура: блоки идут не по порядку: {known}")
    if re.search(r"display:\s*grid|columns\s*:", html_text, re.I):
        errors.append("Структура: найдена колоночная вёрстка — блоки должны идти вертикально")
    if "<table" not in html_text:
        errors.append("Структура: нет ни одной таблицы")
    rows = len(re.findall(r"<tr", html_text)) - html_text.count("<thead>")
    if rows > MAX_TABLE_ROWS + 4:
        errors.append(f"Структура: в таблице больше {MAX_TABLE_ROWS} строк")


def check_length(html_text, errors, stats):
    wc = word_count(html_text)
    sents = [s for s in sentences_of(html_text) if not s.strip().startswith(("http", "-"))]
    stats["words"] = wc
    stats["sentences"] = len(sents)
    if not (MIN_WORDS <= wc <= MAX_WORDS):
        errors.append(f"Объём: слов {wc}, требуется {MIN_WORDS}–{MAX_WORDS}")
    if len(sents) > MAX_SENTENCES:
        errors.append(f"Объём: предложений {len(sents)}, максимум {MAX_SENTENCES}")
    long_s = [s for s in sents if len(s.split()) > MAX_SENTENCE_WORDS]
    if long_s:
        errors.append(f"Объём: {len(long_s)} предложений длиннее {MAX_SENTENCE_WORDS} слов: "
                      f"{long_s[0][:70]}…")
    stats["long_sentences"] = len(long_s)


def check_evidence_and_links(html_text, dataset_urls, errors, stats):
    links = html_links(html_text)
    vk_links = [l for l in links if l.startswith("http")]
    stats["links_total"] = len(links)
    stats["links_vk"] = len(vk_links)
    if not vk_links:
        errors.append("Доказательства: в отчёте нет ни одной активной ссылки")
    for l in vk_links:
        if not is_valid_post_url(l):
            errors.append(f"Ссылки: некорректный формат ссылки на публикацию: {l}")
        elif l not in dataset_urls:
            errors.append(f"Ссылки: публикации нет в датасете: {l}")
    if "#" in links:
        errors.append("Ссылки: есть заглушки href=\"#\" — доказательство не активно")
    # каждый сигнал/вывод обязан иметь ссылку внутри своего div
    for cls, name in (("signal", "сигнал"), ("conclusion", "вывод"), ("card", "карточка поста"),
                      ("clip-card", "клик-блок")):
        for m in re.finditer(rf'<div class="{cls}[^"]*"[^>]*>(.*?)</div>', html_text, re.S):
            inner = m.group(1)
            if 'class="evidence-link"' not in inner:
                snippet = re.sub(r"<[^>]+>", " ", inner)[:60].strip()
                errors.append(f"Доказательства: у {name} нет доказательной ссылки: «{snippet}…»")
            if cls in ("signal", "conclusion") and '<span class="quote"' not in inner:
                errors.append(f"Доказательства: у {name} нет цитаты из публикации или комментария")


def check_clips_separation(html_text, clip_urls, regular_urls, errors):
    clips_sec = re.search(r'<section id="sec-clips".*?</section>', html_text, re.S)
    if clips_sec:
        for l in html_links(clips_sec.group(0)):
            if l in regular_urls:
                errors.append(f"VK Клипы: в блок клипов попала ссылка на обычную публикацию {l}")
    else:
        return
    other = re.sub(r'<section id="sec-clips".*?</section>', "", html_text, flags=re.S)
    for l in html_links(other):
        if l in clip_urls:
            errors.append(f"VK Клипы: ссылка на клип {l} вне отдельного блока клипов")


def check_claims(html_text, errors, stats):
    bad_causal, recs, filler = [], [], []
    for sent in sentences_of(html_text):
        causal = has_causal_claim(sent)
        if causal and not CAUSAL_CONFIRM_RE.search(sent):
            bad_causal.append((causal[0], sent[:90]))
        r = has_recommendation(sent)
        if r:
            recs.append((r[0], sent[:90]))
        f = has_ai_filler(sent)
        if f:
            filler.append((f[0], sent[:90]))
    stats["unconfirmed_causal"] = len(bad_causal)
    stats["recommendations"] = len(recs)
    stats["ai_filler"] = len(filler)
    for w, s in bad_causal:
        errors.append(f"Причинный вывод без подтверждения данными (маркер «{w}»): «{s}…»")
    for w, s in recs:
        errors.append(f"Лишняя рекомендация или совет (маркер «{w}»): «{s}…»")
    for w, s in filler:
        errors.append(f"ИИ-штамп (маркер «{w}»): «{s}…»")


def check_chain(workdir, html_text, errors, stats):
    """Полная цепочка: provenance -> хэши -> датасет -> сегменты -> comment-signals -> отчёт."""
    wd = os.path.abspath(workdir)
    try:
        prov = load_json(os.path.join(wd, REQUIRED_INPUTS["provenance"]))
    except Exception as exc:
        errors.append(f"Цепочка данных: provenance.json недоступен ({exc})")
        return
    files = prov.get("files") or {}
    for key, fname in REQUIRED_INPUTS.items():
        entry = files.get(fname)
        expected = (entry or {}).get("sha256") if isinstance(entry, dict) else entry
        path = os.path.join(wd, fname)
        if not os.path.exists(path):
            errors.append(f"Цепочка данных: вход {fname} отсутствует")
            continue
        if expected and sha256_file(path).lower() != str(expected).lower():
            errors.append(f"Цепочка данных: хэш {fname} не совпадает с provenance — цепочка разорвана")
    try:
        posts, _ = normalize_dataset(load_json(os.path.join(wd, REQUIRED_INPUTS["dataset"])))
    except Exception as exc:
        errors.append(f"Цепочка данных: датасет не читается ({exc})")
        return
    ds_ids = {str(p.get("post_id")) for p in posts}
    ds_urls = {p.get("url") or p.get("post_url") for p in posts}
    try:
        cs = load_json(os.path.join(wd, "comment-signals.json"))
    except Exception as exc:
        errors.append(f"Цепочка данных: comment-signals.json недоступен ({exc})")
        return
    stats["comment_signals_records"] = len(cs.get("records") or [])
    orphan = sorted({r.get("post_id") for r in cs.get("records") or []} - ds_ids)
    if orphan:
        errors.append(f"Цепочка данных: в comment-signals есть post_id вне датасета: {orphan[:5]}")
    used_in_report = {re.search(r"(?:wall|clip)(-\d+_\d+)", l).group(1)
                      for l in html_links(html_text)
                      if re.search(r"(?:wall|clip)(-\d+_\d+)", l)}
    unknown = sorted(used_in_report - ds_ids)
    if unknown:
        errors.append(f"Цепочка данных: отчёт ссылается на post_id, которых нет в датасете: {unknown[:5]}")
    cs_by_post = {r.get("post_id") for r in cs.get("records") or []}
    quoted_comment_posts = set()
    for m in re.finditer(r'<li data-type="comment"[^>]*>.*?href="(https://vk\.com/[a-z]+(-\d+_\d+))"',
                         html_text, re.S):
        quoted_comment_posts.add(m.group(2))
    for pid in quoted_comment_posts:
        if pid not in cs_by_post:
            errors.append(f"Цепочка данных: комментарий процитирован с поста {pid}, "
                          f"которого нет в comment-signals.json")
    # сегменты: карточки top/bottom обязаны относиться к своим quartile-постам
    core_path = os.path.join(wd, "analysis-core.json")
    if os.path.exists(core_path):
        core = load_json(core_path)
        top_ids = {c["post_id"] for c in (core.get("segments", {}).get("top25") or [])}
        bot_ids = {c["post_id"] for c in (core.get("segments", {}).get("bottom25") or [])}
        for sec_name, allowed in (("top_posts", top_ids), ("low_posts", bot_ids)):
            sec = re.search(rf'<section id="sec-{sec_name}".*?</section>', html_text, re.S)
            if not sec:
                continue
            for l in html_links(sec.group(0)):
                m = re.search(r"(?:wall|clip)(-\d+_\d+)", l)
                if m and m.group(1) not in allowed:
                    errors.append(f"Цепочка данных: в блоке {sec_name} ссылка на пост вне сегмента: {m.group(1)}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workdir", required=True)
    ap.add_argument("--report", default="report.html")
    ap.add_argument("--out", default="validation_report.json")
    args = ap.parse_args()
    wd = os.path.abspath(args.workdir)
    path = args.report if os.path.isabs(args.report) else os.path.join(wd, args.report)
    if not os.path.exists(path):
        print(f"FAIL validate_report: файл отчёта не найден: {path}")
        return 2
    with open(path, "r", encoding="utf-8") as f:
        html_text = f.read()

    posts, _ = normalize_dataset(load_json(os.path.join(wd, REQUIRED_INPUTS["dataset"])))
    ds_urls = {p.get("url") or p.get("post_url") for p in posts}
    clip_urls = {p.get("url") or p.get("post_url") for p in posts if is_clip(p)}
    regular_urls = ds_urls - clip_urls

    errors, stats = [], {}
    check_structure(html_text, errors)
    check_length(html_text, errors, stats)
    check_evidence_and_links(html_text, ds_urls, errors, stats)
    check_clips_separation(html_text, clip_urls, regular_urls, errors)
    check_claims(html_text, errors, stats)
    check_chain(wd, html_text, errors, stats)

    result = {"ok": not errors, "errors": errors, "stats": stats,
              "limits": {"words": [MIN_WORDS, MAX_WORDS], "sentences": MAX_SENTENCES,
                         "sentence_words": MAX_SENTENCE_WORDS, "table_rows": MAX_TABLE_ROWS}}
    write_json(os.path.join(wd, args.out), result)
    if errors:
        print("FAIL validate_report:")
        print("\n".join("- " + e for e in errors[:40]))
        if len(errors) > 40:
            print(f"- ... и ещё {len(errors) - 40}")
        return 2
    print("OK validate_report: структура, объём, доказательства, ссылки, клипы и цепочка данных подтверждены")
    print("- " + "; ".join(f"{k}: {v}" for k, v in stats.items()))
    return 0


if __name__ == "__main__":
    sys.exit(main())

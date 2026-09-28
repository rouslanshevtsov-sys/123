#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Шаг 7. Сборка HTML-отчёта из report-draft.json по нейтральному шаблону.

Шаблон: templates/report-template.html — смысловые блоки идут вертикально сверху вниз,
без колонок и без горизонтальной прокрутки.
Draft-файл содержит выводы модели; каждая запись evidence_link обязана иметь post_id, url, quote.
Структура и правила объёма: references/html-structure.md, references/report-length.md.
"""
import argparse
import html as html_mod
import json
import os
import re
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import MSK, load_json

SECTION_ORDER = [
    "scope", "method", "top_posts", "er_signals", "cta_signals", "content_signals",
    "comment_signals", "clips", "low_posts", "conclusions", "appendix",
]
SECTION_TITLES = {
    "scope": "Масштаб анализа",
    "method": "Метод",
    "top_posts": "Сильные публикации (верхние 25%)",
    "er_signals": "ER-сигналы",
    "cta_signals": "CTA-сигналы",
    "content_signals": "Содержательные сигналы",
    "comment_signals": "Сигналы из комментариев",
    "clips": "VK Клипы (отдельно)",
    "low_posts": "Слабые публикации (нижние 25%)",
    "conclusions": "Выводы, подтверждённые данными",
    "appendix": "Приложения",
}


def esc(s):
    return html_mod.escape(str(s if s is not None else ""), quote=True)


def render_evidence(ev_list):
    parts = []
    for ev in ev_list or []:
        url = ev.get("url") or ""
        pid = ev.get("post_id") or ""
        quote = ev.get("quote") or ""
        typ = ev.get("type") or "post"
        src = ev.get("source_file")
        label = f"{pid}" if pid else url
        href = url if url.startswith("http") else "#"
        inner = f'<a class="evidence-link" href="{esc(href)}">{esc(label)}</a>'
        if quote:
            inner += f' <span class="quote">&laquo;{esc(quote[:160])}&raquo;</span>'
        if src:
            inner += f' <span class="src">[{esc(src)}]</span>'
        parts.append(f"<li data-type=\"{esc(typ)}\">{inner}</li>")
    return "<ul class=\"evidence\">" + "".join(parts) + "</ul>" if parts else ""


def render_section(key, sec):
    title = SECTION_TITLES[key]
    body = []
    if key == "scope":
        rows = sec.get("rows") or []
        body.append("<table><thead><tr><th>Показатель</th><th>Значение</th></tr></thead><tbody>")
        for r in rows:
            body.append(f"<tr><td>{esc(r.get('name'))}</td><td>{esc(r.get('value'))}</td></tr>")
        body.append("</tbody></table>")
        if sec.get("text"):
            body.append(f"<p>{esc(sec['text'])}</p>")
    elif key == "method":
        for item in sec.get("items") or []:
            body.append(f"<p>{esc(item)}</p>")
    elif key in ("top_posts", "low_posts"):
        for card in sec.get("cards") or []:
            cls = "card top" if key == "top_posts" else "card bottom"
            metrics = card.get("metrics") or {}
            mstr = ", ".join(f"{esc(k)}: {esc(v)}" for k, v in metrics.items())
            body.append(
                f"<div class=\"{cls}\" data-bucket=\"{esc(card.get('bucket', key))}\">"
                f"<h4>{esc(card.get('group_name'))} &middot; {esc(card.get('date_msk'))} &middot; "
                f"{esc(card.get('main_type'))}</h4>"
                f"<p class=\"first-line\">&laquo;{esc(card.get('first_line'))}&raquo;</p>"
                f"<p class=\"metrics\">ER {esc(card.get('er'))} при бенчмарке {esc(card.get('benchmark_er'))}; "
                f"rel {esc(card.get('rel_er_vs_benchmark'))}; {mstr}</p>"
                f"<p class=\"observation\">{esc(card.get('observation'))}</p>"
                f"{render_evidence(card.get('evidence_links'))}</div>")
    elif key in ("er_signals", "cta_signals", "content_signals", "comment_signals"):
        for item in sec.get("items") or []:
            conf = item.get("confidence") or item.get("level") or "observed"
            body.append(
                f"<div class=\"signal\" data-confidence=\"{esc(conf)}\""
                f" data-level=\"{esc(item.get('competitor_level', 'direct'))}\">"
                f"<h4>{esc(item.get('title'))}</h4>"
                f"<p>{esc(item.get('statement'))}</p>"
                f"{render_evidence(item.get('evidence_links'))}</div>")
    elif key == "clips":
        if sec.get("note"):
            body.append(f"<p class=\"note\">{esc(sec['note'])}</p>")
        for item in sec.get("items") or []:
            body.append(
                f"<div class=\"clip-card\" data-kind=\"clip\">"
                f"<h4>{esc(item.get('group_name'))} &middot; {esc(item.get('post_id'))}</h4>"
                f"<p>{esc(item.get('statement'))}</p>"
                f"{render_evidence(item.get('evidence_links'))}</div>")
    elif key == "conclusions":
        for item in sec.get("items") or []:
            causal = "true" if item.get("causal") else "false"
            body.append(
                f"<div class=\"conclusion\" data-causal=\"{causal}\">"
                f"<h4>{esc(item.get('title'))}</h4>"
                f"<p>{esc(item.get('statement'))}</p>"
                f"<p class=\"basis\">Опора: {esc(item.get('competitor_level'))}. "
                f"{esc(item.get('confirmation'))}</p>"
                f"{render_evidence(item.get('evidence_links'))}</div>")
    elif key == "appendix":
        for item in sec.get("items") or []:
            body.append(f"<p>{esc(item)}</p>")
    return (f"<section id=\"sec-{key}\" class=\"block\">\n<h2>{esc(title)}</h2>\n"
            + "\n".join(body) + "\n</section>")


def build(workdir, draft_name="report-draft.json", template_name=None, out_name="report.html"):
    wd = os.path.abspath(workdir)
    draft = load_json(os.path.join(wd, draft_name))
    tpl_path = template_name or os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                             "templates", "report-template.html")
    with open(tpl_path, "r", encoding="utf-8") as f:
        tpl = f.read()

    sections = draft.get("sections") or {}
    blocks = []
    for key in SECTION_ORDER:
        if key in sections:
            blocks.append(render_section(key, sections[key]))
    meta = draft.get("meta") or {}
    generated = datetime.now(MSK).strftime("%Y-%m-%d %H:%M")
    out = tpl.replace("<!--TITLE-->", esc(meta.get("title", "Отчёт"))) \
             .replace("<!--SUBTITLE-->", esc(meta.get("subtitle", ""))) \
             .replace("<!--GENERATED-->", esc(generated)) \
             .replace("<!--SECTIONS-->", "\n\n".join(blocks))
    dest = os.path.join(wd, out_name)
    with open(dest, "w", encoding="utf-8") as f:
        f.write(out)
    return dest, len(blocks)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workdir", required=True)
    ap.add_argument("--draft", default="report-draft.json")
    ap.add_argument("--template", default=None)
    ap.add_argument("--out", default="report.html")
    args = ap.parse_args()
    dest, n = build(args.workdir, args.draft, args.template, args.out)
    print(f"OK build_report: {dest}, блоков {n}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

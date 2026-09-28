#!/usr/bin/env python3
"""Блокирующий медиашлюз и валидатор итоговых результатов.

Завершение этапа запрещено (exit code 1), если:
- для лучших постов ожидались изображения, но не скачано ни одного;
- подтверждённый VK Клип не имеет статуса success или no_speech;
- медиапути повреждены (файл из dataset/XLSX-описания не существует);
- отсутствуют обязательные зависимости;
- подмена просмотров клипа просмотрами поста (views_source != 'clip' у поста типа
  'Клип' с доступными просмотрами клипа) — валидатор отклоняет;
- ER/бенчмарки не соответствуют формулам;
- дубли post_id; комментарии не связаны со строковым post_id;
- XLSX не открывается / нет 5 обязательных листов / неверные колонки;
- JSON невалидны;
- в итоговых материалах найдены секреты (токены vk1.a..., access_token).

Деградированный запуск разрешён только с --allow-degraded (явное согласие пользователя).

Использование: python media_gate.py [--workdir DIR] [--allow-degraded]
"""
import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import (BEST_POSTS_COLUMNS, EXCEL_SHEETS, UNAVAILABLE_COLUMNS,  # noqa: E402
                    VERIFIED_POSTS_COLUMNS, compute_er, load_json, path)

SECRET_RE = re.compile(r"vk1\.[a-zA-Z]\.[A-Za-z0-9_\-]{20,}|access_token\s*[=:]\s*\S+")


def check_dependencies():
    missing = []
    for mod in ("requests", "PIL", "openpyxl"):
        try:
            __import__(mod)
        except Exception:
            missing.append(mod)
    return missing


def validate(workdir):
    errors, warnings = [], []
    wd = workdir

    def jload(name):
        p = os.path.join(wd, name)
        if not os.path.exists(p):
            errors.append(f"Файл не найден: {name}")
            return None
        try:
            with open(p, encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            errors.append(f"Невалидный JSON {name}: {e}")
            return None

    meta = jload("run_meta.json")
    posts = jload("posts_analyzed.json")
    comments = jload("comments_replies.json")
    dataset = jload("vk_posts_dataset.json")
    clips = jload("clips_processing.json")
    unavailable = jload("unavailable.json")

    if meta is None or posts is None:
        return errors, warnings

    # временное окно
    from datetime import datetime
    try:
        ws_dt = datetime.fromisoformat(meta["window_start_msk"])
        we_dt = datetime.fromisoformat(meta["window_end_msk"])
        hours = (we_dt - ws_dt).total_seconds() / 3600
        if abs(hours - meta.get("window_hours", 168)) > 0.05:
            errors.append(f"Окно не 7×24 ч: {hours} ч")
    except Exception as e:
        errors.append(f"run_meta.json: окно нечитаемое: {e}")
        hours = None

    ids = [p["post_id"] for p in posts]
    if len(ids) != len(set(ids)):
        errors.append("Дубли post_id в posts_analyzed.json")

    benchmarks = {}
    for p in posts:
        if p.get("er") is not None:
            benchmarks.setdefault(str(p["owner_id"]), []).append(p["er"])
    bm = {k: sum(v) / len(v) for k, v in benchmarks.items()}

    for p in posts:
        # ER по формуле
        if p.get("views_for_er") and p["views_for_er"] > 0:
            expected = compute_er(p["likes"], p["comments"], p["reposts"], p["views_for_er"])
            if p.get("er") is None or abs(expected - p["er"]) > 1e-9:
                errors.append(f"{p['post_id']}: ER не соответствует формуле")
        elif p.get("er") is not None:
            errors.append(f"{p['post_id']}: ER рассчитан при нулевых просмотрах")
        else:
            if p.get("result") != "ER не рассчитан":
                errors.append(f"{p['post_id']}: статус без просмотров должен быть 'ER не рассчитан'")
        # бенчмарк
        b = bm.get(str(p["owner_id"]))
        if p.get("benchmark") is not None and b is not None and abs(p["benchmark"] - b) > 1e-9:
            errors.append(f"{p['post_id']}: бенчмарк сообщества неверен")
        # лучший пост
        if p.get("er") is not None and b is not None:
            should_best = p["er"] >= b
            if bool(p.get("is_best")) != should_best:
                errors.append(f"{p['post_id']}: is_best противоречит правилу ER >= бенчмарка")
        # клипы: просмотры самого клипа обязательны
        if p.get("main_type") == "Клип":
            cv = p.get("clip_views_at_collection")
            if cv:
                if p.get("views_source") != "clip":
                    errors.append(f"{p['post_id']}: у клипа views_source != 'clip' "
                                  "(подмена просмотрами поста запрещена)")
                if p.get("views_for_er") != cv:
                    errors.append(f"{p['post_id']}: ER клипа должен считаться по просмотрам клипа")
            else:
                warnings.append(f"{p['post_id']}: клип без просмотров клипа на момент сбора")

    # комментарии ↔ post_id
    post_ids = set(ids)
    for c in comments or []:
        if not isinstance(c.get("post_id"), str) or c["post_id"] not in post_ids:
            errors.append(f"Комментарий {c.get('comment_id')}: post_id не связан со списком постов")
            break

    # медиашлюз: изображения
    best = [p for p in posts if p.get("is_best")]
    expected_imgs = sum(1 for p in best if p.get("images"))
    have_imgs = sum(1 for p in best if p.get("image_files"))
    if expected_imgs > 0 and have_imgs == 0:
        errors.append("МЕДИАШЛЮЗ: для лучших постов ожидались изображения, "
                      "но не скачано ни одного")

    # медиашлюз: клипы
    unprocessed = [c for c in (clips or []) if c.get("status") not in ("success", "no_speech")]
    if unprocessed:
        errors.append("МЕДИАШЛЮЗ: необработанные подтверждённые клипы: "
                      + ", ".join(str(c["post_id"]) for c in unprocessed[:5]))
    # если в постах есть подтверждённые клипы, но clips_processing пуст — клипы не обработаны
    clip_posts = [p for p in posts if p.get("main_type") == "Клип"]
    if clip_posts and not clips:
        errors.append("МЕДИАШЛЮЗ: есть посты типа 'Клип', но clips_processing.json пуст — "
                      "ни один клип не скачан и не обработан")

    # медиапути существуют
    checked_paths = 0
    for p in posts:
        for f in (p.get("image_files") or []) + ([p["collage_file"]] if p.get("collage_file") else []):
            fp = f if os.path.isabs(f) else os.path.join(wd, f)
            if not os.path.exists(fp):
                errors.append(f"Медиапуть повреждён: {f}")
            else:
                checked_paths += 1
    for c in clips or []:
        f = c.get("file")
        if f:
            fp = f if os.path.isabs(f) else os.path.join(wd, f)
            if not os.path.exists(fp):
                errors.append(f"Медиапуть клипа повреждён: {f}")
            else:
                checked_paths += 1

    # dataset
    if dataset is not None:
        if len(dataset.get("posts", [])) != len(posts):
            errors.append("vk_posts_dataset.json: число постов не совпадает")
        ds_txt = json.dumps(dataset, ensure_ascii=False)
        if SECRET_RE.search(ds_txt):
            errors.append("СЕКРЕТЫ: в vk_posts_dataset.json найден токен/access_token")
        for dp in dataset.get("posts", []):
            if dp.get("main_type") == "Клип" and dp.get("views_source") == "clip":
                pass
        # расшифровки: каждый обработанный клип имеет transcript
        for c in clips or []:
            if c.get("status") == "success" and not c.get("transcript"):
                errors.append(f"Клип {c['post_id']}: status success без расшифровки")

    # XLSX
    xlsx = os.path.join(wd, "competitors_vk_report.xlsx")
    if not os.path.exists(xlsx):
        errors.append("XLSX не найден: competitors_vk_report.xlsx")
    else:
        try:
            from openpyxl import load_workbook
            wb = load_workbook(xlsx)
            for sh in EXCEL_SHEETS:
                if sh not in wb.sheetnames:
                    errors.append(f"XLSX: отсутствует лист '{sh}'")
            if "Лучшие посты" in wb.sheetnames:
                hdr = [c.value for c in wb["Лучшие посты"][1]]
                if hdr[:len(BEST_POSTS_COLUMNS)] != BEST_POSTS_COLUMNS:
                    errors.append("XLSX: колонки листа 'Лучшие посты' не соответствуют шаблону")
                ws = wb["Лучшие посты"]
                if ws.freeze_panes != "A2":
                    errors.append("XLSX: не закреплены заголовки на 'Лучшие посты'")
                if not ws.auto_filter.ref:
                    errors.append("XLSX: нет фильтров на 'Лучшие посты'")
                # формат ER
                for r in range(2, min(ws.max_row, 50) + 1):
                    cell = ws.cell(row=r, column=11)
                    if isinstance(cell.value, float) and cell.number_format != "0.00%":
                        errors.append(f"XLSX: ER в строке {r} не в формате 0.00%")
                        break
            if "Проверенные посты" in wb.sheetnames:
                hdr = [c.value for c in wb["Проверенные посты"][1]]
                if hdr[:len(VERIFIED_POSTS_COLUMNS)] != VERIFIED_POSTS_COLUMNS:
                    errors.append("XLSX: колонки листа 'Проверенные посты' не соответствуют шаблону")
            if "Недоступно" in wb.sheetnames:
                hdr = [c.value for c in wb["Недоступно"][1]]
                if hdr[:len(UNAVAILABLE_COLUMNS)] != UNAVAILABLE_COLUMNS:
                    errors.append("XLSX: колонки листа 'Недоступно' не соответствуют шаблону")
        except Exception as e:
            errors.append(f"XLSX не открывается: {e}")

    # секретные файлы не должны лежать в артефактах
    for name in ("competitors_vk_report.xlsx", "vk_posts_dataset.json",
                 "comments_replies.json", "media_summary_anonymized.json"):
        p = os.path.join(wd, name)
        if os.path.exists(p) and name.endswith(".json"):
            with open(p, encoding="utf-8") as f:
                if SECRET_RE.search(f.read()):
                    errors.append(f"СЕКРЕТЫ: токен найден в {name}")

    missing_deps = check_dependencies()
    if missing_deps:
        errors.append("Отсутствуют зависимости: " + ", ".join(missing_deps))

    return errors, warnings


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workdir", default=None)
    ap.add_argument("--allow-degraded", action="store_true",
                    help="Явное согласие пользователя на деградированный результат")
    args = ap.parse_args()
    wd = args.workdir or os.environ.get("VK_WORK_DIR") or os.getcwd()

    errors, warnings = validate(wd)
    for w in warnings:
        print(f"WARN: {w}")
    if errors:
        print("MEDIA GATE: FAIL")
        for e in errors:
            print(f"  ERROR: {e}")
        if args.allow_degraded:
            print("Деградированный запуск разрешён явным согласием пользователя (--allow-degraded).")
            return 0
        print("Завершение заблокировано. Деградированный результат возможен только "
              "после явного согласия пользователя.")
        return 1
    print("MEDIA GATE: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())

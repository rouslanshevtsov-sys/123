#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Шаг 1. Проверка происхождения входных файлов, хэшей и множеств post_id.

Останавливает работу (exit code 2) с конкретной причиной, если:
  - отсутствует или повреждён любой обязательный вход;
  - provenance.json не описывает все входы или хэш файла не совпадает;
  - множества post_id датасета, комментариев и XLSX не согласованы;
  - у записей датасета нет обязательных полей или ссылки имеют неверный формат.

Результат: validation_inputs.json (в workdir).
"""
import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import (REQUIRED_INPUTS, DATASET_REQUIRED_FIELDS, PROVENANCE_REQUIRED_FIELDS,
                   is_valid_post_url, load_json, normalize_comments, normalize_dataset,
                   read_xlsx_rows, sha256_file, write_json, excel_sheet_map,
                   find_post_id_in_row, parse_date_msk)


def check_existence(workdir):
    missing = []
    paths = {}
    for key, fname in REQUIRED_INPUTS.items():
        p = os.path.join(workdir, fname)
        paths[key] = p
        if not os.path.exists(p) or os.path.getsize(p) == 0:
            missing.append(f"Обязательный вход отсутствует или пуст: {fname}")
    return paths, missing


def check_provenance(paths, dataset_ids, comments_ids, xlsx_ids):
    """Возвращает (ok, errors, report). Происхождение + хэши + множества post_id."""
    errors, report = [], {"files": {}, "post_id_sets": {}, "provenance": None}
    prov_path = paths["provenance"]
    try:
        prov = load_json(prov_path)
    except Exception as exc:
        errors.append(f"provenance.json не читается: {exc}")
        return False, errors, report
    if not isinstance(prov, dict):
        errors.append("provenance.json должен быть JSON-объектом")
        return False, errors, report
    for field in PROVENANCE_REQUIRED_FIELDS:
        if field not in prov:
            errors.append(f"provenance.json: нет обязательного поля '{field}'")
    files = prov.get("files") or {}
    if not isinstance(files, dict) or not files:
        errors.append("provenance.json: поле 'files' пусто или имеет неверный тип")
        return False, errors, report

    # 1) каждый обязательный вход описан в provenance
    for key, path in paths.items():
        fname = os.path.basename(path)
        if fname not in files:
            errors.append(f"Происхождение не подтверждено: {fname} нет в provenance.json")
            continue
        entry = files[fname]
        expected = None
        if isinstance(entry, dict):
            expected = entry.get("sha256") or entry.get("hash")
        elif isinstance(entry, str):
            expected = entry
        if not expected:
            errors.append(f"provenance.json: для {fname} нет значения sha256")
            report["files"][fname] = {"status": "no_hash"}
            continue
        actual = sha256_file(path)
        ok = actual.lower() == str(expected).lower()
        report["files"][fname] = {"sha256_actual": actual, "sha256_expected": expected,
                                  "match": ok,
                                  "declared_by": (entry.get("produced_by") if isinstance(entry, dict) else None)}
        if not ok:
            errors.append(f"Хэш не совпадает: {fname} (файл изменён после выгрузки или из другого запуска)")

    # 2) посты, помеченные как проверенные, должны присутствовать в датасете
    checked = prov.get("checked_post_ids")
    if isinstance(checked, list) and checked:
        extra = [c for c in checked if c not in dataset_ids]
        if extra:
            errors.append(f"provenance заявляет проверенными {len(extra)} постов, которых нет в датасете: "
                          f"{extra[:5]}")
        report["checked_declared"] = len(checked)
        report["checked_missing_in_dataset"] = len(extra)

    # 3) сверка множеств post_id
    report["post_id_sets"] = {
        "dataset_n": len(dataset_ids),
        "comments_posts_n": len(comments_ids),
        "excel_posts_n": len(xlsx_ids),
    }
    if xlsx_ids:
        only_xlsx = sorted(xlsx_ids - dataset_ids)
        if only_xlsx:
            errors.append(f"post_id из XLSX отсутствуют в датасете ({len(only_xlsx)}): {only_xlsx[:5]}")
        report["excel_not_in_dataset"] = len(only_xlsx)
    orphan = sorted(comments_ids - dataset_ids)
    if orphan:
        errors.append(f"Комментарии ссылается на {len(orphan)} post_id, которых нет в датасете: {orphan[:5]}")
    report["comments_orphans"] = len(orphan)
    report["dataset_without_comments"] = len(dataset_ids - comments_ids)
    return not errors, errors, report


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workdir", required=True)
    ap.add_argument("--out", default="validation_inputs.json")
    ap.add_argument("--allow-missing-comments-link", action="store_true",
                    help="не прерывать работу, если комментарии есть только у части постов")
    args = ap.parse_args()

    wd = os.path.abspath(args.workdir)
    errors = []
    paths, missing = check_existence(wd)
    errors += missing
    if errors:
        write_json(os.path.join(wd, args.out), {"ok": False, "errors": errors})
        print("FAIL validate_inputs:\n- " + "\n- ".join(errors))
        return 2

    # читаем датасет
    try:
        ds_raw = load_json(paths["dataset"])
        posts, ds_meta = normalize_dataset(ds_raw)
    except Exception as exc:
        msg = f"vk_posts_dataset.json не читается или не содержит списка публикаций: {exc}"
        write_json(os.path.join(wd, args.out), {"ok": False, "errors": [msg]})
        print("FAIL validate_inputs:\n- " + msg)
        return 2

    dataset_ids = set()
    for i, p in enumerate(posts):
        pid = p.get("post_id")
        if not pid:
            errors.append(f"Запись датасета #{i}: нет post_id")
            continue
        dataset_ids.add(str(pid).strip())
        for field in DATASET_REQUIRED_FIELDS:
            if field in ("url",) :
                continue
            if field not in p:
                errors.append(f"post_id={pid}: нет обязательного поля '{field}'")
        url = p.get("url") or p.get("post_url") or ""
        if url and not is_valid_post_url(url):
            errors.append(f"post_id={pid}: ссылка неверного формата: {url[:60]}")
        d = parse_date_msk(p.get("date_msk"))
        if d is None:
            errors.append(f"post_id={pid}: дата не парсится: {p.get('date_msk')}")
    if not posts:
        errors.append("Датасет пуст: публикаций нет, анализ невозможен")
    dup = len(posts) - len(dataset_ids)
    if dup > 0:
        errors.append(f"В датасете {dup} дублей post_id")

    # комментарии
    try:
        cm_raw = load_json(paths["comments"])
        comments = normalize_comments(cm_raw)
    except Exception as exc:
        comments = []
        errors.append(f"comments.json не читается: {exc}")
    comments_ids = {c["post_id"] for c in comments if c.get("post_id")}
    if not comments:
        errors.append("comments.json не содержит ни одного комментария — сигналы аудитории недоступны")

    # XLSX
    xlsx_ids = set()
    sheets = {}
    try:
        rows_by_sheet = read_xlsx_rows(paths["excel"])
        sheets = excel_sheet_map(rows_by_sheet)
        for name, recs in rows_by_sheet.items():
            for row in recs:
                pid = find_post_id_in_row(row)
                if pid:
                    xlsx_ids.add(pid)
    except Exception as exc:
        errors.append(f"XLSX не читается: {exc}")
    if not xlsx_ids:
        errors.append("В XLSX не найдено ни одного post_id — сверка выгрузок невозможна")

    ok_prov, prov_errors, prov_report = check_provenance(paths, dataset_ids, comments_ids, xlsx_ids)
    errors += prov_errors

    result = {
        "ok": not errors,
        "errors": errors,
        "counts": {
            "dataset_posts": len(posts),
            "dataset_unique_post_ids": len(dataset_ids),
            "comments_total": len(comments),
            "posts_with_comments": len(comments_ids & dataset_ids),
            "excel_rows_with_post_id": len(xlsx_ids),
        },
        "sheets_detected": sheets,
        "provenance_report": prov_report,
        "inputs": {k: os.path.basename(v) for k, v in paths.items()},
        "dataset_meta_keys": sorted(list(ds_meta.keys()))[:20],
    }
    write_json(os.path.join(wd, args.out), result)
    if errors:
        print("FAIL validate_inputs:")
        print("\n".join("- " + e for e in errors[:40]))
        if len(errors) > 40:
            print(f"- ... и ещё {len(errors) - 40} ошибок")
        return 2
    print("OK validate_inputs: происхождение, хэши и множества post_id согласованы")
    print(json.dumps(result["counts"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())

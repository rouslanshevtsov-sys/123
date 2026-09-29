#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Служебный сценарий: зафиксировать происхождение входа (provenance.json).

Применяется один раз — когда результаты предыдущего этапа копируются в рабочую папку.
Записывает sha256 каждого входного файла, кто его создал и сколько постов помечено проверенными.
"""
import argparse
import json
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import MSK, REQUIRED_INPUTS, load_json, normalize_dataset, sha256_file, write_json


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workdir", required=True)
    ap.add_argument("--produced-by", default="analyze-vk-best-posts")
    ap.add_argument("--out", default="provenance.json")
    args = ap.parse_args()
    wd = os.path.abspath(args.workdir)
    files = {}
    # provenance.json — это выход самого сценария, он не является входом;
    # его хэш фиксируется отдельно, чтобы validate_inputs мог проверить неизменность цепочки
    for key, fname in REQUIRED_INPUTS.items():
        path = os.path.join(wd, fname)
        if key == "provenance":
            if os.path.exists(path) and os.path.getsize(path):
                files[fname] = {"sha256": sha256_file(path), "bytes": os.path.getsize(path),
                                "produced_by": args.produced_by}
            continue
        if not os.path.exists(path):
            print(f"FAIL make_provenance: нет входного файла {fname}")
            return 2
        files[fname] = {"sha256": sha256_file(path), "bytes": os.path.getsize(path),
                        "produced_by": args.produced_by}
    posts, _ = normalize_dataset(load_json(os.path.join(wd, REQUIRED_INPUTS["dataset"])))
    payload = {
        "produced_by": args.produced_by,
        "generated_at_msk": datetime.now(MSK).strftime("%Y-%m-%d %H:%M"),
        "files": files,
        "checked_post_ids": sorted({str(p.get("post_id")) for p in posts}),
    }
    write_json(os.path.join(wd, args.out), payload)
    print(f"OK make_provenance: зафиксировано файлов {len(files)}, постов {len(payload['checked_post_ids'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

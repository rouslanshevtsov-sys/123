#!/usr/bin/env python3
"""Поиск токенов и других секретов в файлах навыка и артефактах.

Использование:
    python detect_secrets.py <файл или каталог>...      # код 0 — чисто, 1 — найдено
Правила: VK-токены, JWT, длинные base64-строки, «секретные» ключи в присвоениях,
подписанные URL (X-Amz-Signature / sig= / token= в query).
"""
import os
import re
import sys

RULES = [
    ("vk_token", re.compile(r"\bvk[12]\.a\.[A-Za-z0-9_\-]{20,}|(?<![\w.])vk[0-9a-f]{32}(?![\w.])", re.I)),
    ("vk_api_token_assignment", re.compile(r"(access_token|VK_API_TOKEN)\s*[=:]\s*['\"]?[A-Za-z0-9._\-]{15,}")),
    ("jwt", re.compile(r"\beyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{5,}")),
    ("signed_url", re.compile(r"[?&](X-Amz-Signature|sig|signature|token)=[A-Za-z0-9%._\-]{8,}", re.I)),
    ("generic_secret_key", re.compile(r"(secret|password|passwd|api[_-]?key)\s*[=:]\s*['\"][^'\"]{12,}['\"]", re.I)),
    ("long_base64", re.compile(r"[A-Za-z0-9+/]{80,}={0,2}")),
]
SKIP_EXT = {".png", ".jpg", ".jpeg", ".gif", ".ico", ".woff", ".woff2", ".ttf",
            ".pdf", ".zip", ".xlsx"}  # xlsx сканируется отдельно через verify_results


def scan_text(text):
    hits = []
    for name, rx in RULES:
        m = rx.search(text)
        if m:
            frag = m.group(0)
            hits.append({"rule": name, "sample": frag[:12] + "…"})
    return hits


def iter_files(paths):
    for p in paths:
        if os.path.isfile(p):
            yield p
        elif os.path.isdir(p):
            for root, dirs, files in os.walk(p):
                dirs[:] = [d for d in dirs if d not in {".git", "__pycache__", "node_modules"}]
                for f in files:
                    if os.path.splitext(f)[1].lower() in SKIP_EXT:
                        continue
                    yield os.path.join(root, f)


def main():
    targets = sys.argv[1:] or ["."]
    found = 0
    for fp in iter_files(targets):
        try:
            text = open(fp, encoding="utf-8", errors="ignore").read()
        except OSError:
            continue
        for hit in scan_text(text):
            print(f"SECRET: {fp}: rule={hit['rule']} sample={hit['sample']}")
            found += 1
    if found:
        print(f"detect_secrets: FAIL ({found} findings)")
        sys.exit(1)
    print("detect_secrets: OK (секреты не найдены)")


if __name__ == "__main__":
    main()

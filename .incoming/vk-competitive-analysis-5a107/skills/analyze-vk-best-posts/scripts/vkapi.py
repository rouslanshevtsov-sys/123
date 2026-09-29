#!/usr/bin/env python3
"""Клиент официального VK API с повторными попытками при временных ошибках.

Токен: переменная окружения VK_TOKEN или файл .token в рабочей директории.
Содержимое токена никогда не попадает в логи и итоговые файлы.
Для тестов можно подменить транспорт: set_transport(fn(method, params) -> dict).
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import API_URL, API_VERSION, path  # noqa: E402

try:
    import requests
except Exception:  # pragma: no cover - окружение без requests
    requests = None

_session = None
_transport = None


def get_token():
    tok = os.environ.get("VK_TOKEN")
    if tok:
        return tok.strip()
    p = path(".token")
    if os.path.exists(p):
        with open(p, encoding="utf-8") as f:
            return f.read().strip()
    raise RuntimeError("Токен VK API не задан: VK_TOKEN или файл .token")


def set_transport(fn):
    """Инъекция транспорта для тестов (fn(method, params) -> dict ответа)."""
    global _transport
    _transport = fn


def _http_call(method, params):
    global _session
    if _session is None:
        _session = requests.Session()
        _session.headers["User-Agent"] = "Mozilla/5.0 (X11; Linux x86_64)"
    p = dict(params or {})
    p.update({"v": API_VERSION, "access_token": get_token()})
    r = _session.post(API_URL + method, data=p, timeout=45)
    try:
        return r.json()
    except ValueError:
        return {"error_code": -2, "error_msg": f"invalid json, http {r.status_code}"}


def call(method, params=None, max_retries=8, retry_pause=0.35):
    """Вызов метода API. Повторы: error 6 (rate limit), сетевые/TLS-ошибки.

    Возвращает dict ответа VK ('response' или 'error_code').
    После исчерпания попыток — {'error_code': -1, 'error_msg': ...}.
    """
    transport = _transport or _http_call
    last_err = None
    for attempt in range(max_retries):
        try:
            d = transport(method, dict(params or {}))
        except Exception as e:  # сеть / TLS / таймаут
            last_err = f"{type(e).__name__}: {e}"
            time.sleep(min(2 ** attempt, 10) * 0.1)
            continue
        code = d.get("error_code")
        if code == 6:  # too many requests
            time.sleep(retry_pause * (attempt + 1) * 2)
            continue
        if code in (29, 36):  # rate limit / action prohibited — мягкий ретрай
            time.sleep(retry_pause * (attempt + 2) * 3)
            if attempt >= max_retries - 2:
                return d
            continue
        if "response" in d or code is not None:
            return d
        return {"error_code": -2, "error_msg": str(d)[:200]}
    return {"error_code": -1, "error_msg": f"retries exhausted: {last_err or 'rate limit'}"}


def paginate(method, base_params, page_size=100, max_items=5000, deadline_ts=None,
             date_key="date", stop_when_before_deadline=True):
    """Полная пагинация wall.get-подобного метода.

    Собирает items до count; ранняя остановка, если страница ушла раньше окна
    (учитывая, что закреп может быть первым); удаляет дубли по (owner,id).
    Возвращает (items, error_or_None).
    """
    items, offset, err = [], 0, None
    seen = set()
    while True:
        p = dict(base_params)
        p.update({"count": page_size, "offset": offset})
        r = call(method, p)
        if "response" not in r:
            err = f"{method}: error {r.get('error_code')} {str(r.get('error_msg'))[:120]}"
            break
        resp = r["response"]
        page = resp.get("items", [])
        total = resp.get("count", 0)
        for it in page:
            key = (it.get("owner_id") or it.get("from_id"), it.get("id"))
            if key in seen:
                continue
            seen.add(key)
            items.append(it)
        offset += len(page)
        if not page or offset >= total:
            break
        if (deadline_ts and stop_when_before_deadline and date_key
                and len(page) >= page_size):
            oldest = min((x.get(date_key, 0) for x in page), default=0)
            if oldest < deadline_ts and offset > page_size:
                break
        time.sleep(0.3)
    return items, err

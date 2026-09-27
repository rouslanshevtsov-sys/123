#!/usr/bin/env python3
"""Клиент VK API: токен из файла проекта или переменной окружения, ретраи, пагинация.

Токен НЕ выводится в логи и результаты. Секретные значения маскируются.
Использование (как библиотека):
    from vk_client import VkClient
    vk = VkClient()            # токен: env VK_API_TOKEN или vk_token.txt
    resp = vk.call('groups.search', {'q': 'запрос', 'count': 1000})
"""
import json
import os
import sys
import time
import urllib.parse
import urllib.request
import urllib.error

API_URL = "https://api.vk.com/method/"
API_VERSION = "5.195"
TOKEN_FILENAME = "vk_token.txt"


class VkApiError(RuntimeError):
    def __init__(self, code, msg, method):
        super().__init__(f"VK API error {code} in {method}: {msg}")
        self.code = code
        self.msg = msg


def mask_token(text, token):
    """Заменяет вхождения токена на ***REDACTED*** (защита логов от секретов)."""
    if token and token in str(text):
        return str(text).replace(token, "***REDACTED***")
    return str(text)


class VkClient:
    def __init__(self, token=None, token_file=None, api_version=API_VERSION,
                 min_interval=0.42, logger=None):
        self.token = token or self._load_token(token_file)
        if not self.token:
            raise RuntimeError(
                "VK API token not found. Set env VK_API_TOKEN or create "
                f"{TOKEN_FILENAME} in the project root.")
        self.api_version = api_version
        self.min_interval = min_interval
        self._last_call_ts = 0.0
        self.logger = logger
        self.log = []  # компактный журнал вызовов без токенов

    @staticmethod
    def _load_token(token_file=None):
        env = os.environ.get("VK_API_TOKEN")
        if env:
            return env.strip()
        candidates = []
        if token_file:
            candidates.append(token_file)
        candidates.append(os.path.join(os.getcwd(), TOKEN_FILENAME))
        for path in candidates:
            if path and os.path.isfile(path):
                with open(path, "r", encoding="utf-8") as f:
                    val = f.read().strip()
                if val:
                    return val
        return None

    def call(self, method, params=None, retries=6):
        """Один вызов метода API с повторными попытками при временных ошибках."""
        p = dict(params or {})
        p["access_token"] = self.token
        p["v"] = self.api_version
        last_err = None
        for attempt in range(retries):
            wait = self.min_interval - (time.time() - self._last_call_ts)
            if wait > 0:
                time.sleep(wait)
            self._last_call_ts = time.time()
            try:
                data = self._request(method, p)
            except (urllib.error.URLError, OSError, TimeoutError) as e:
                last_err = f"network: {mask_token(e, self.token)}"
                time.sleep(min(2 ** attempt, 30))
                continue
            if "error" in data:
                err = data["error"]
                code = err.get("error_code")
                msg = mask_token(err.get("error_msg", ""), self.token)
                self.log.append({"method": method, "error_code": code,
                                 "attempt": attempt})
                # 6 — too many requests; 114/29 temporary issues -> retry
                if code in (6, 29, 114):
                    last_err = f"error_code={code}: {msg}"
                    time.sleep(max(err.get("retry_after", 0), min(2 ** attempt, 30)))
                    continue
                raise VkApiError(code, msg, method)
            self.log.append({"method": method, "ok": True})
            return data.get("response", data)
        raise VkApiError(-1, f"retries exhausted ({last_err})", method)

    def _request(self, method, params):
        url = API_URL + method + "?" + urllib.parse.urlencode(params)
        req = urllib.request.Request(url, headers={"User-Agent": "competitor-search-skill"})
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode("utf-8"))

    def search_groups(self, query, count=1000):
        """groups.search c count=1000; возвращает список групп."""
        resp = self.call("groups.search", {"q": query, "count": count,
                                           "type": "group,public,event"})
        items = resp.get("items", [])
        if self.logger:
            self.logger(f"search '{query}': {len(items)} groups (total={resp.get('count')})")
        return items

    def get_groups_batched(self, group_ids, fields=None, batch=500):
        """groups.getById пакетами до `batch` id за запрос."""
        fields = fields or ("members_count,city,place,description,site,"
                            "verified,type,is_closed,finish_date,start_date")
        out = {}
        ids = [str(g) for g in group_ids]
        for i in range(0, len(ids), batch):
            chunk = ids[i:i + batch]
            try:
                resp = self.call("groups.getById",
                                 {"group_id": ",".join(chunk), "fields": fields})
            except VkApiError as e:
                if self.logger:
                    self.logger(f"getById batch {i//batch} failed: {e}")
                continue
            for g in resp.get("groups", []):
                out[str(g["id"])] = g
            if self.logger:
                self.logger(f"getById batch {i//batch}: {len(resp.get('groups', []))} resolved")
        return out

    def wall_posts_window(self, owner_id, window_seconds=31 * 24 * 3600,
                          count=100, max_pages=20):
        """wall.get с пагинацией по offset; окно последних window_seconds.

        Возвращает dict:
          posts: {owner_id:post_id -> post} (дедупликация по owner_id+post_id)
          pages: число страниц
          covered: достигнута ли граница окна обычными постами
        Закреплённые посты сохраняются отдельно по флагу is_pinned.
        """
        now = int(time.time())
        start = now - window_seconds
        posts = {}
        offset = 0
        pages = 0
        covered = False
        while pages < max_pages:
            try:
                resp = self.call("wall.get", {"owner_id": owner_id, "count": count,
                                              "offset": offset, "filter": "owner"})
            except VkApiError:
                break
            items = resp.get("items", [])
            pages += 1
            if not items:
                covered = True
                break
            older = 0
            for p in items:
                key = f"{p.get('from_id', owner_id)}:{p.get('id')}"
                posts[key] = p
                if p.get("date", 0) < start and not p.get("is_pinned"):
                    older += 1
            if older == len(items):
                covered = True  # вся страница старше начала окна
                break
            offset += count
        return {"posts": posts, "pages": pages, "covered": covered,
                "window_start": start, "window_end": now}


if __name__ == "__main__":
    # smoke-test: проверка наличия токена без его вывода
    try:
        VkClient()
        print("token: OK (источник: env VK_API_TOKEN или vk_token.txt)")
    except RuntimeError as e:
        print("token: MISSING —", e)
        sys.exit(1)

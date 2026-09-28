import sys, json, time
from datetime import datetime, timezone, timedelta
sys.path.insert(0, '/workspace/vk_analysis')
from vkapi import call

MSK = timezone(timedelta(hours=3))
WINDOW_HOURS = 168
start_dt = datetime.now(MSK)
window_start_ts = int((start_dt - timedelta(hours=WINDOW_HOURS)).timestamp())
meta = {'run_started_at_msk': start_dt.isoformat(),
        'window_start_msk': datetime.fromtimestamp(window_start_ts, MSK).isoformat(),
        'window_hours': WINDOW_HOURS, 'timezone': 'Europe/Moscow'}
json.dump(meta, open('meta.json', 'w'), ensure_ascii=False, indent=2)
print("RUN START:", meta['run_started_at_msk'], "| WINDOW FROM:", meta['window_start_msk'])

groups = json.load(open('groups.json'))
FIELDS = 'attachments,likes,comments,reposts,views,copy_history,is_pinned,pole_ids'
all_posts = {}
unavailable = []

for g in groups:
    oid = g['id']
    if oid is None:
        unavailable.append({'object': f"Сообщество {g['name']} ({g['url']})", 'link': g['url'],
                            'reason': "Адрес сообщества возвращает HTTP 404; VK API не находит сообщество по group_id='advgods' (ошибка 100 'group_id not domain'). Публикации недоступны."})
        continue
    sn = g['screen_name']
    posts_raw = []
    offset = 0
    error_page = None
    while True:
        r = call('wall.get', {'owner_id': oid, 'count': 100, 'offset': offset, 'fields': FIELDS, 'filter': 'owner'})
        if 'response' not in r:
            error_page = str(r.get('error', r))[:200]
            break
        items = r['response']['items']
        posts_raw.extend(items)
        total = r['response']['count']
        offset += len(items)
        if not items or offset >= total:
            break
        # stop early if we already went before window by 3 days (pinned posts may be first though)
        oldest = min(p['date'] for p in posts_raw)
        if offset >= 500 and oldest < window_start_ts - 7*86400:
            break
        time.sleep(0.35)
    if error_page:
        unavailable.append({'object': f"Стена {g['name']}", 'link': g['url'], 'reason': f"wall.get ошибка: {error_page}"})
        continue
    seen = set()
    own_in_window = []
    excluded_pinned_old = 0
    for p in posts_raw:
        pid = (p['from_id'] if 'from_id' in p else oid, p['id'])
        key = f"{oid}_{p['id']}"
        if key in seen:
            continue
        seen.add(key)
        if p['date'] < window_start_ts:
            if p.get('is_pinned'):
                excluded_pinned_old += 1
            continue
        # own posts only: filter=owner should guarantee; double-check copy_history from other owner
        ch = p.get('copy_history')
        if ch and ch[0].get('from_id') != oid:
            continue
        own_in_window.append(p)
    all_posts[str(oid)] = {'group': g, 'posts': own_in_window, 'raw_fetched': len(posts_raw),
                           'excluded_pinned_before_window': excluded_pinned_old}
    print(f"{sn}: fetched={len(posts_raw)} own_in_window={len(own_in_window)} pinned_old_excl={excluded_pinned_old}")

json.dump(all_posts, open('raw_posts.json', 'w'), ensure_ascii=False)
json.dump(unavailable, open('unavailable.json', 'w'), ensure_ascii=False, indent=2)
print("TOTAL communities with data:", len(all_posts), "| unavailable:", len(unavailable))

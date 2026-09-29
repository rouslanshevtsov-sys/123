import sys, json, time
sys.path.insert(0,'scripts')
from vk_helpers import call, save

WINDOW = 31*24*3600
NOW = int(time.time())
START = NOW - WINDOW

qual = json.load(open('output/competitor-analysis/qualified.json'))
TOP = qual[:70]   # first semantic batch (<=200)

results = {}
for idx, r in enumerate(TOP):
    gid = r['gid']
    posts = {}
    offset = 0
    done = False
    pages = 0
    while not done and pages < 15:
        resp = call('wall.get', {'owner_id': -gid, 'count': 100, 'offset': offset, 'filter':'owner'})
        pages += 1
        if resp is None:
            done = True; break
        items = resp.get('items', [])
        if not items:
            done = True; break
        older = 0
        for p in items:
            key = (p.get('from_id') or -gid, p['id'])
            posts[key] = p
            if p.get('date', 0) < START and not p.get('is_pinned'):
                older += 1
        if older == len(items):
            done = True
        offset += 100
    # compute ER
    own = [p for p in posts.values() if p.get('date',0) >= START or p.get('is_pinned')]
    regular_in_window = [p for p in own if not p.get('is_pinned') and p.get('date',0) >= START]
    pinned = [p for p in own if p.get('is_pinned')]
    last_post_date = max([p['date'] for p in regular_in_window], default=None)
    ers, no_views = [], []
    for p in regular_in_window + pinned:
        v = (p.get('views') or {}).get('count', 0)
        l = (p.get('likes') or {}).get('count', 0)
        c = (p.get('comments') or {}).get('count', 0)
        rp = (p.get('reposts') or {}).get('count', 0)
        if v and v > 0:
            ers.append({'post_id': p['id'], 'owner_id': -(gid), 'date': p['date'], 'views': v, 'likes': l, 'comments': c, 'reposts': rp,
                        'er': (l+c+rp)/v, 'text': (p.get('text') or '')[:180], 'is_pinned': bool(p.get('is_pinned'))})
        else:
            no_views.append({'post_id': p['id'], 'date': p.get('date'), 'reason': 'no/zero views'})
    avg_er = sum(e['er'] for e in ers)/len(ers) if ers else None
    results[str(gid)] = {
        'members_count': r['mc'],
        'last_own_post_ts': last_post_date,
        'regular_posts_in_window': len(regular_in_window),
        'pinned_posts': len(pinned),
        'posts_with_views': len(ers),
        'posts_no_views': len(no_views),
        'avg_er': avg_er,
        'er_posts': sorted(ers, key=lambda x:-x['date']),
        'excluded_no_views': no_views,
        'pages_fetched': pages,
        'wall_total': resp.get('count') if resp else None,
    }
    lp = time.strftime('%Y-%m-%d', time.localtime(last_post_date)) if last_post_date else 'none'
    print(f"{idx+1}. gid={gid} mc={r['mc']} posts_win={len(regular_in_window)} er_posts={len(ers)} avgER={f'{avg_er:.4f}' if avg_er is not None else 'n/a'} last={lp}", flush=True)

save('posts_er.json', results)
json.dump(vk_log := __import__('vk_helpers').log, open('output/competitor-analysis/api_errors_posts.json','w'), ensure_ascii=False, indent=1)
print('saved. errors:', len(vk_log))

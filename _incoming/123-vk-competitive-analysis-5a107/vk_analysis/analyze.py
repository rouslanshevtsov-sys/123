import sys, json, re, time
from datetime import datetime, timezone, timedelta
sys.path.insert(0, '/workspace/vk_analysis')
from vkapi import call

MSK = timezone(timedelta(hours=3))
meta = json.load(open('meta.json'))
WS = int(datetime.fromisoformat(meta['window_start_msk']).timestamp())
groups_data = json.load(open('raw_posts.json'))
unavailable = json.load(open('unavailable.json'))

def is_clip_att(att):
    """Return clip dict if attachment is VK Clip (short_video/clip or inner type)."""
    t = att.get('type')
    if t == 'clip':
        return att['clip'] if 'clip' in att else {'id': None}
    if t == 'video':
        v = att.get('video', {})
        it = v.get('type')
        if it in ('short_video', 'clip'):
            return v
        if it is None:  # need video.get to check inner type
            return {'needs_check': True, **v}
        return None
    return None

TYPE_KEYWORDS = re.compile(r'(розыгрыш|конкурс|приз|победител|разыгрыва|giveaway|дарим бесплатно|в качестве приза)', re.I)
MECHANIC = re.compile(r'(подписк|лайк|репост|комментари|участн|услов|до \d|итога|рандом|счастливчик|выберем|определим|приз)', re.I)

def classify(text, attachments):
    has_poll = False
    imgs, vids, clips, carousel = [], [], [], False
    other_structured = []
    for a in attachments or []:
        t = a.get('type')
        if t == 'photo':
            imgs.append(a['photo'])
        elif t == 'album':
            imgs.extend([p for p in [a.get('album', {})]] )  # album cover counts as image-ish; keep as photo? treat album as images
        elif t == 'carousel':
            carousel = True
            for card in a.get('carousel', {}).get('cards', []):
                ph = card.get('photo')
                if ph: imgs.append(ph)
        elif t == 'poll':
            has_poll = True
        elif t == 'audio':
            other_structured.append('audio')
        elif t == 'doc':
            other_structured.append('doc')
        elif t == 'link':
            other_structured.append('link')
        elif t in ('video', 'clip'):
            c = is_clip_att(a)
            if c: clips.append(c)
            else: vids.append(a.get('video', {}))
    n_imgs = len(imgs)
    if clips:
        main = 'Клип'
    elif vids:
        main = 'Видео'
    elif carousel and (n_imgs >= 2 or True):
        main = 'Карусель'
    elif n_imgs == 1:
        main = 'Картинка'
    elif n_imgs >= 2:
        main = 'Карусель'
    elif text and text.strip():
        main = 'Текстовый пост'
    elif other_structured:
        main = 'Текстовый пост'  # no media at all besides structured non-visual
    else:
        main = 'Текстовый пост'
    roz = bool(TYPE_KEYWORDS.search(text or '')) and bool(MECHANIC.search(text or ''))
    return main, has_poll, roz, imgs, vids, clips, carousel

def best_photo_url(photo):
    sizes = photo.get('sizes', [])
    cand = [s for s in sizes if s.get('type') in ('w','x','y','z','q','r','s','m')]
    if not cand:
        return None, None
    # prefer size closest to ~1600 by width
    def score(s): 
        w = s.get('width') or 0; h = s.get('height') or 0
        return abs(max(w,h)-1600)
    cand.sort(key=score)
    return cand[0]['url'], (cand[0].get('width'), cand[0].get('height'))

posts_out = []
comments_out = []
clips_out = []

for oid_s, rec in groups_data.items():
    g = rec['group']; oid = g['id']; sn = g['screen_name']
    posts = rec['posts']
    valid_ers = []
    precords = []
    for p in posts:
        likes = p.get('likes', {}).get('count', 0)
        cm = p.get('comments', {})
        comments_cnt = cm.get('count', 0)
        reposts = p.get('reposts', {}).get('count', 0)
        views = p.get('views', {}).get('count')
        post_id = f"{oid}_{p['id']}"
        url = f"https://vk.com/wall{oid}_{p['id']}"
        main, poll, roz, imgs, vids, clips, car = classify(p.get('text',''), p.get('attachments'))
        er = None
        er_status = 'ok'
        if views and views > 0:
            er = (likes + comments_cnt + reposts) / views
        else:
            er_status = 'ER не рассчитан'
        recd = {'post_id': post_id, 'owner_id': oid, 'item_id': p['id'], 'group_name': g['name'],
                'group_type': g['type'], 'url': url, 'date_ts': p['date'],
                'date_msk': datetime.fromtimestamp(p['date'], MSK).strftime('%Y-%m-%d %H:%M'),
                'text': p.get('text',''), 'main_type': main, 'has_poll': poll, 'is_giveaway': roz,
                'likes': likes, 'comments': comments_cnt, 'reposts': reposts, 'views': views,
                'er': er, 'er_status': er_status, 'images': [best_photo_url(ph) for ph in imgs],
                'n_images': len(imgs), 'videos': vids, 'clips': clips, 'pinned': bool(p.get('is_pinned')),
                'data_status': 'ok'}
        if views and views > 0:
            valid_ers.append(er)
        precords.append(recd)
        # fetch comments with replies (only when count>0)
        if comments_cnt > 0:
            off = 0
            while True:
                r = call('wall.getComments', {'owner_id': oid, 'post_id': p['id'], 'need_likes': 1,
                                              'count': 100, 'offset': off, 'sort': 'nr'})
                if 'response' not in r:
                    recd['data_status'] = 'ok, комментарии частично недоступны: ' + str(r.get('error',{}).get('error_msg','network'))[:80]
                    unavailable.append({'object': f"Комментарии к посту {url}", 'link': url, 'reason': str(r.get('error', r))[:150]})
                    break
                cs = r['response']['items']
                for c in cs:
                    comments_out.append({'post_id': post_id, 'group': sn, 'comment_id': c['pid'],
                                         'parent_id': c.get('parent_id', 0), 'from_id': c.get('from_id'),
                                         'date': c.get('date'), 'text': c.get('text',''),
                                         'likes': c.get('likes',{}).get('count',0)})
                off += len(cs)
                total = r['response']['count']
                if not cs or off >= total or off >= 500:
                    break
                time.sleep(0.25)
            time.sleep(0.1)
    benchmark = sum(valid_ers)/len(valid_ers) if valid_ers else None
    for recd in precords:
        recd['benchmark'] = benchmark
        if recd['er'] is not None and benchmark is not None:
            recd['is_best'] = recd['er'] >= benchmark
            recd['result'] = 'Лучший' if recd['is_best'] else 'Обычный'
        else:
            recd['is_best'] = False
            recd['result'] = 'ER не рассчитан'
        posts_out.append(recd)
    print(sn, 'posts:', len(precords), 'valid ER:', len(valid_ers), 'benchmark:', round(benchmark*100,3) if benchmark else None, '%',
          'best:', sum(1 for x in precords if x['is_best']))

json.dump(posts_out, open('posts_analyzed.json','w'), ensure_ascii=False, indent=1)
json.dump(comments_out, open('comments.json','w'), ensure_ascii=False)
print('total posts:', len(posts_out), 'total comments rows:', len(comments_out))

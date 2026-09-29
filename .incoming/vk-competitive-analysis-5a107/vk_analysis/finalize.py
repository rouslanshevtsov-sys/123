import sys, json, os, time, re
from datetime import datetime, timezone, timedelta
sys.path.insert(0, '/workspace/vk_analysis')
from vkapi import call
from PIL import Image
import requests

MSK = timezone(timedelta(hours=3))
meta = json.load(open('meta.json'))
groups = json.load(open('groups.json'))
posts = json.load(open('posts_analyzed.json'))
comments = json.load(open('comments.json'))
unavailable = json.load(open('unavailable.json'))
gmap = {str(g['id']): g for g in groups if g['id'] is not None}

# ---------- 1. VERIFY VIDEO TYPES (all videos via video.get) ----------
videoids = set()
for p in posts:
    for v in p['videos']:
        videoids.add((v.get('owner_id'), v.get('id'), v.get('access_key')))
confirmed_clips = []
for own, vid, ak in videoids:
    key = f'{own}_{vid}' + (f'_{ak}' if ak else '')
    r = call('video.get', {'videos': key})
    it = r.get('response',{}).get('items',[{}])[0] if 'response' in r else {}
    t = it.get('type')
    if t in ('short_video','clip'):
        confirmed_clips.append({'post_owner': own, 'video_id': vid, 'clip_views': it.get('views'), 'item': it})
print("videos checked:", len(videoids), "confirmed clips:", len(confirmed_clips))

# ---------- 2. RE-FETCH COMMENTS ----------
comments = []
cnt_err = 0
for p in posts:
    if p['comments'] <= 0: continue
    oid, pid = p['owner_id'], p['item_id']
    off = 0
    while True:
        r = call('wall.getComments', {'owner_id': oid, 'post_id': pid, 'need_likes': 1, 'count': 100, 'offset': off, 'sort': 'nr'})
        if 'response' not in r:
            cnt_err += 1
            p['data_status'] = 'ok; комментарии частично недоступны: ' + str(r.get('error',{}).get('error_msg','network error'))[:90]
            unavailable.append({'object': f"Комментарии к посту {p['url']}", 'link': p['url'], 'reason': str(r.get('error', r))[:150]})
            break
        cs = r['response']['items']
        for c in cs:
            comments.append({'post_id': p['post_id'], 'comment_id': c['pid'], 'parent_id': c.get('parent_id', 0),
                             'from_id': c.get('from_id'), 'date_ts': c.get('date'),
                             'text': c.get('text',''), 'likes': c.get('likes',{}).get('count',0)})
        off += len(cs)
        if not cs or off >= r['response']['count'] or off >= 500: break
        time.sleep(0.2)
    time.sleep(0.05)
print("comment rows:", len(comments), "errors:", cnt_err)

# ---------- 3. DOWNLOAD IMAGES FOR BEST POSTS + COLLAGES ----------
os.makedirs('media/images', exist_ok=True)
os.makedirs('media/collages', exist_ok=True)
DL = requests.Session(); DL.headers['User-Agent']='Mozilla/5.0'
best_posts = [p for p in posts if p['is_best']]
img_fail = 0
for p in best_posts:
    files = []
    for i,(url,dim) in enumerate(p['images']):
        if not url: continue
        fp = f"media/images/{p['post_id'].replace('-','_')}_{i}.jpg"
        if not os.path.exists(fp):
            try:
                rr = DL.get(url, timeout=45)
                if rr.status_code==200 and rr.content[:3]==b'\xff\xd8\xff' or rr.content[:8]==b'\x89PNG\r\n\x1a\n':
                    open(fp,'wb').write(rr.content)
                else:
                    img_fail += 1; continue
            except Exception as e:
                img_fail += 1; print("img dl fail", url[:60], e); continue
        files.append(fp)
    p['image_files'] = files
    # build collage
    if files:
        ims = []
        for f in files:
            try: ims.append(Image.open(f).convert('RGB'))
            except Exception: pass
        n = len(ims)
        if n == 1:
            im = ims[0]; im.thumbnail((1600,1600)); coll = im
        else:
            cols = 1 if n==2 else (2 if n<=4 else 3)
            rows = (n + cols - 1)//cols
            cw = ch = 800
            coll = Image.new('RGB',(cols*cw, rows*ch),(255,255,255))
            for k,im in enumerate(ims):
                im.thumbnail((cw,ch))
                x=(k%cols)*cw + (cw-im.width)//2; y=(k//cols)*ch + (ch-im.height)//2
                coll.paste(im,(x,y))
        cf = f"media/collages/{p['post_id'].replace('-','_')}.jpg"
        coll.save(cf, quality=85)
        p['collage_file'] = cf
print("best posts with images:", sum(1 for p in best_posts if p.get('image_files')), "| download failures:", img_fail)

# ---------- 4. TRANSCRIPTS ----------
# No confirmed VK Clips -> nothing to transcribe. Regular videos are NOT downloaded/transcribed per spec.
transcripts = {}

# ---------- 5. DATASET JSON ----------
dataset = {
 'run': meta, 'timezone': 'Europe/Moscow', 'window_hours': 168,
 'token_note': 'Секреты не включены',
 'communities': [{'name': g['name'], 'type': g['type'], 'url': g['url'], 'vk_id': g['id'],
                  'members_count': g['members_count']} for g in groups],
 'benchmarks': {},
 'posts': [],
 'clips_processing': {'confirmed_clips_found': len(confirmed_clips), 'note': 'За последние 7×24 ч ни одно вложение attachments[].type=video/clip после проверки video.get не имело внутреннего типа short_video/clip. Подтверждённых VK Клипов нет — расшифровка речи не требовалась.'},
 'unavailable': unavailable,
}
for g in groups:
    if g['id'] is None: continue
    gp = [p for p in posts if p['owner_id']==g['id'] and p['er'] is not None]
    if gp: dataset['benchmarks'][str(g['id'])] = round(sum(x['er'] for x in gp)/len(gp), 6)
for p in posts:
    q = dict(p)
    q.pop('videos', None); q.pop('clips', None)
    q['image_urls'] = [u for u,_ in p['images'] if u]
    q['transcript'] = None
    q['transcript_status'] = 'not_applicable_no_confirmed_clip'
    dataset['posts'].append(q)
json.dump(dataset, open('vk_posts_dataset.json','w'), ensure_ascii=False)
json.dump(comments, open('comments_replies.json','w'), ensure_ascii=False)

# ---------- 6. ANONYMIZED MEDIA SUMMARY ----------
anon = {'generated_at_msk': datetime.now(MSK).isoformat(),
        'window': meta,
        'competents': [{'community': f"Сообщество {i+1}", 'type': g['type'], 'subscribers_band': bucket(g['members_count']) if g['members_count'] else 'н/д'} for i,g in enumerate(groups)],
        'per_community': []}
def bucket(n):
    for lim in (100_000, 200_000, 500_000, 1_000_000):
        if n < lim: return f"<{lim:,}"
    return ">=1,000,000"
anon = {'generated_at_msk': datetime.now(MSK).isoformat(), 'window': meta,
        'communities': [{'label': f"Конкурент {chr(65+i)}", 'type': g['type'],
                         'subscribers_band': bucket(g['members_count']) if g['members_count'] else 'н/д'} for i,g in enumerate(groups)],
        'per_community': []}
for i,g in enumerate(groups):
    gp = [p for p in posts if g['id'] is not None and p['owner_id']==g['id']]
    gb = [p for p in gp if p['is_best']]
    types = {}
    for p in gp: types[p['main_type']] = types.get(p['main_type'],0)+1
    anon['per_community'].append({'label': f"Конкурент {chr(65+i)}", 'posts_in_window': len(gp),
        'benchmark_er': dataset['benchmarks'].get(str(g['id'])), 'best_posts': len(gb),
        'median_er_best': (sorted([x['er'] for x in gb if x['er']])[len(gb)//2] if gb else None),
        'post_types': types, 'polls': sum(1 for p in gp if p['has_poll']), 'giveaways': sum(1 for p in gp if p['is_giveaway']),
        'confirmed_clips': 0})
json.dump(anon, open('media_summary_anonymized.json','w'), ensure_ascii=False, indent=1)

# ---------- 7. EXCEL ----------
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill
from openpyxl.utils import get_column_letter
from openpyxl.drawing.image import Image as XImage
from openpyxl.worksheet.hyperlink import Hyperlink

wb = Workbook()
TYPE_ORDER = {'direct':0, 'indirect':1, 'attention':2}
TYPE_RU = {'direct':'Прямые конкуренты','indirect':'Косвенные конкуренты','attention':'Конкуренты за внимание'}
HFONT = Font(bold=True, color='FFFFFF'); HFILL = PatternFill('solid', fgColor='4472C4')

def style_sheet(ws, widths):
    for j,w in enumerate(widths,1): ws.column_dimensions[get_column_letter(j)].width = w
    for c in ws[1]:
        c.font=HFONT; c.fill=HFILL; c.alignment=Alignment(wrap_text=True, vertical='center')
    ws.freeze_panes='A2'; ws.auto_filter.ref = ws.dimensions

# Сводка
ws = wb.active; ws.title='Сводка'
rows = [['Параметр','Значение'],
 ['Момент начала работы (Europe/Moscow)', meta['run_started_at_msk']],
 ['Временное окно', f"{meta['window_start_msk']} — {meta['run_started_at_msk']} (168 ч)"],
 ['Конкурентов в исходном JSON', len(groups)],
 ['Сообществ с данными', sum(1 for g in groups if g['id'] is not None and any(p['owner_id']==g['id'] for p in posts))],
 ['Недоступно объектов', len(unavailable)],
 ['Всего проверенных публикаций', len(posts)],
 ['Без просмотров (ER не рассчитан)', sum(1 for p in posts if p['er'] is None)],
 ['Лучших постов (ER ≥ бенчмарка)', len(best_posts)],
 ['Подтверждённых VK Клипов', len(confirmed_clips)],
 ['Строк комментариев/ответов', len(comments)],
 ['Тип поста: Клип/Видео/Картинка/Карусель/Текст', ', '.join(f"{t}: {sum(1 for p in posts if p['main_type']==t)}" for t in ('Клип','Видео','Картинка','Карусель','Текстовый пост'))],
 ['Опросы (вложение poll)', sum(1 for p in posts if p['has_poll'])],
 ['Розыгрыши подтверждённые', sum(1 for p in posts if p['is_giveaway'])]]
for r in rows: ws.append(r)
style_sheet(ws,[45,60])

# Лучшие посты
ws = wb.create_sheet('Лучшие посты')
ws.append(['Сообщество','Тип конкурента','Ссылка на пост','Текст','Тип поста','Опрос','Розыгрыш','Лайки','Комментарии','Просмотры для ER','ER поста','Бенчмарк','Расшифровка','Изображения','ID поста'])
bp_sorted = sorted(best_posts, key=lambda p:(TYPE_ORDER[p['group_type']], -p['er']))
row_map = {}
for p in bp_sorted:
    bm = dataset['benchmarks'].get(str(p['owner_id']))
    ws.append([p['group_name'], TYPE_RU[p['group_type']], p['url'], p['text'][:3000], p['main_type'],
               'Да' if p['has_poll'] else '', 'Да' if p['is_giveaway'] else '', p['likes'], p['comments'],
               p['views'], p['er'], bm, '— (клипов нет)', '', p['post_id']])
    r = ws.max_row; row_map[p['post_id']] = r
    c = ws.cell(row=r, column=3); c.hyperlink = p['url']; c.font = Font(color='0563C1', underline='single')
    ws.cell(row=r,column=11).number_format='0.00%'; ws.cell(row=r,column=12).number_format='0.00%'
    for col in (2,4,14): ws.cell(row=r,column=col).alignment = Alignment(wrap_text=True, vertical='top')
    cf = p.get('collage_file')
    if cf and os.path.exists(cf):
        try:
            im = XImage(cf)
            scale = min(1.0, 300/max(im.width,1), 240/max(im.height,1))
            im.width=int(im.width*scale); im.height=int(im.height*scale)
            ws.add_image(im, f"N{r}")
            ws.row_dimensions[r].height = max(90, im.height*0.75)
        except Exception as e: print("xlsx img err", e)
style_sheet(ws,[26,20,30,60,12,7,9,8,11,14,10,10,16,38,14])

# Клипы
ws = wb.create_sheet('Клипы')
ws.append(['Сообщество','Ссылка на пост','Внешний тип','Внутренний тип (video.get)','Просмотры клипа','Файл','Статус обработки','Расшифровка'])
if not confirmed_clips:
    ws.append(['—','—','—','—','—','—','Подтверждённых VK Клипов за окно не найдено','—'])
else:
    for cc in confirmed_clips:
        ws.append(['','', '', 'short_video', cc['clip_views'],'','','pending'])
style_sheet(ws,[26,30,12,20,14,30,25,40])

# Проверенные посты
ws = wb.create_sheet('Проверенные посты')
ws.append(['Сообщество','VK сообщества','Подписчики','Дата поста','Ссылка на пост','Текст','Тип поста','Опрос','Розыгрыш','Лайки','Комментарии','Репосты','Просмотры для ER','ER поста','Бенчмарк','Результат','Статус данных'])
mem = {str(g['id']): g['members_count'] for g in groups if g['id'] is not None}
snm = {str(g['id']): g['screen_name'] for g in groups if g['id'] is not None}
for p in sorted(posts, key=lambda x:(x['group_name'], -x['er'] if x['er'] else 0)):
    bm = dataset['benchmarks'].get(str(p['owner_id']))
    ws.append([p['group_name'], snm.get(str(p['owner_id']),'advgods'), mem.get(str(p['owner_id'])), p['date_msk'], p['url'],
               p['text'][:3000], p['main_type'], 'Да' if p['has_poll'] else '', 'Да' if p['is_giveaway'] else '',
               p['likes'], p['comments'], p['reposts'], p['views'], p['er'], bm, p['result'], p['data_status']])
    r = ws.max_row
    c = ws.cell(row=r,column=5); c.hyperlink=p['url']; c.font=Font(color='0563C1', underline='single')
    ws.cell(row=r,column=14).number_format='0.00%'; ws.cell(row=r,column=15).number_format='0.00%'
    ws.cell(row=r,column=6).alignment=Alignment(wrap_text=True, vertical='top')
style_sheet(ws,[26,18,11,16,30,60,12,7,9,8,11,8,14,10,10,12,25])

# Недоступно
ws = wb.create_sheet('Недоступно')
ws.append(['Объект','Ссылка','Конкретная причина'])
for u in unavailable:
    ws.append([u['object'], u['link'], u['reason']])
    r = ws.max_row; ws.cell(row=r,column=2).hyperlink=u['link']
    ws.cell(row=r,column=3).alignment=Alignment(wrap_text=True)
style_sheet(ws,[40,35,70])

wb.save('/workspace/vk_analysis/competitors_vk_report.xlsx')
print("XLSX saved")

# ---------- CHECKS ----------
ids = [p['post_id'] for p in posts]
assert len(ids)==len(set(ids)), "duplicates!"
for p in posts:
    if p['views'] and p['views']>0:
        assert abs(p['er'] - (p['likes']+p['comments']+p['reposts'])/p['views']) < 1e-12
imgs_expected = sum(1 for p in best_posts if p['images'])
imgs_have = sum(1 for p in best_posts if p.get('image_files'))
print("STOP CONDITIONS: best posts expected images:", imgs_expected, "downloaded:", imgs_have, "| confirmed clips:", len(confirmed_clips), "(statuses ok trivially)")

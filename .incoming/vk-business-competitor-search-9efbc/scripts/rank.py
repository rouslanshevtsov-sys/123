import json, re, sys
sys.path.insert(0,'scripts')
from vk_helpers import call, save

data = json.load(open('output/competitor-analysis/pool_raw.json'))
pool = data['pool']

def has_own_site(s):
    if not s: return False
    doms = set(re.findall(r'(?:https?://)?(?:www\.)?([a-z0-9][a-z0-9\-\.]*\.[a-z]{2,})', s.lower()))
    return bool(doms - {'vk.com','m.vk.com','vk.ru','m.vk.ru','vk.me'})

shortlist = {}
# own group (will be excluded at qualification stage)
shortlist[199452383] = dict(pool.get('199452383',{}).get('g', {'id':199452383}), reasons=['own group'])

NAMED = ['netology','skillbox','edupro','contented','geekbrains','madsuniversity','pruffme',
         'targetconf','getcourse','pandasedu','complito','skillfactory','tuturu_ru',
         'marketchanger','neiro_academy','smm_school','targeting_school','edu_skol']
resp = call('groups.getById', {'group_id': ','.join(NAMED), 'fields':'members_count,city,place,description,site,verified'})
if resp:
    for g in resp['groups']:
        gid = g['id']
        gg = {k: g.get(k) for k in ('id','name','screen_name','members_count','city','place','description','site','verified','type','is_closed','photo_200')}
        if gid in shortlist:
            shortlist[gid] = dict(gg, reasons=shortlist[gid].get('reasons',[])+['named player'])
        else:
            shortlist[gid] = dict(gg, reasons=['named player'])
    print('named resolved:', len(resp['groups']))

BANNED_NAME = re.compile(r'(скид|акци|купон|барахол|подслуш|мем|юмор|новост|ваканси|афиш|здоровь|рецепт|эзотер|астролог|таро)', re.I)

def score(g):
    name = (g.get('name') or '')
    desc = (g.get('description') or '')
    t = (name + ' ' + desc).lower()
    if BANNED_NAME.search(name): return None
    nl = name.lower()
    bucket_target = any(k in nl for k in ['маркетинг','маркетолог','таргет','smm','смм','продвижен','реклам'])
    bucket_desc = any(k in t for k in ['таргет','обучен','курс','наставник','ментор','практикум','тренинг','професси','школ'])
    edu_signal = any(k in t for k in ['обучен','курс','наставник','ментор','тренинг','практикум','професси','школ','образоват'])
    if not (bucket_target and bucket_desc and edu_signal): return None
    s = 3 if all(k in nl for k in ['маркетин','обучен'] ) or ('школа' in nl and 'маркетин' in nl) else 2
    if any(k in nl for k in ['таргет','smm','смм']): s += 1
    if has_own_site(g.get('site')): s += 1
    mc = g.get('members_count') or 0
    if 1000 <= mc <= 3_000_000: s += 1
    return s

cands = []
for k,v in pool.items():
    sc = score(v['g'])
    if sc is not None:
        cands.append((sc, v['g'].get('members_count') or 0, v))
cands.sort(key=lambda x:(-x[0], -x[1]))
print('scored:', len(cands))
for sc, mc, v in cands[:40]:
    g=v['g']; print(sc, mc, g['id'], g.get('screen_name'), g['name'][:55])

for sc, mc, v in cands[:300]:
    gid = v['g']['id']
    if gid not in shortlist:
        shortlist[gid] = dict(v['g'], matched_queries=v['queries'], reasons=[f'rank score={sc}'])

save('shortlist.json', {str(k):v for k,v in shortlist.items()})
print('SHORTLIST:', len(shortlist))

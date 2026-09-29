import requests, time, json

TOKEN = open('/workspace/vk_token.txt').read().strip()
API = 'https://api.vk.com/method/'
V = '5.195'
_session = requests.Session()
log = []

def call(method, params=None, retries=6):
    p = dict(params or {})
    p['access_token'] = TOKEN
    p['v'] = V
    for attempt in range(retries):
        try:
            r = _session.get(API + method, params=p, timeout=30)
            d = r.json()
            if 'error' in d:
                code = d['error']['error_code']
                log.append({'method': method, 'error_code': code, 'msg': d['error'].get('error_msg','')[:200], 'params': {k:v for k,v in (params or {}).items()}})
                if code == 6:
                    time.sleep(2.8 * (attempt + 1)); continue
                return None
            time.sleep(1.2)
            return d['response']
        except Exception as e:
            log.append({'method': method, 'error_code': 'NET', 'msg': str(e)[:200], 'params': {k:v for k,v in (params or {}).items()}})
            time.sleep(2.0 * (attempt + 1))
    return None

def save(name, obj):
    with open('/workspace/output/competitor-analysis/' + name, 'w', encoding='utf-8') as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)

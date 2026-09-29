import requests, json, time

TOKEN = open('/workspace/vk_analysis/.token').read().strip()
API = 'https://api.vk.com/method/'
V = '5.199'
S = requests.Session()
S.headers['User-Agent'] = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36'

def call(method, params=None, max_retries=8):
    p = dict(params or {})
    p.update({'v': V, 'access_token': TOKEN})
    for attempt in range(max_retries):
        try:
            r = S.post(API + method, data=p, timeout=45)
            d = r.json()
            if 'error' in d:
                code = d.get('error_code')
                if code == 6:
                    time.sleep(1.5 * (attempt + 1)); continue
                return d
            if 'response' in d:
                return d
            return {'error_code': -2, 'error_msg': 'no response key', 'raw': str(d)[:200]}
        except Exception as e:
            time.sleep(min(2 ** attempt, 10))
    return {'error_code': -1, 'error_msg': 'network retries exhausted'}

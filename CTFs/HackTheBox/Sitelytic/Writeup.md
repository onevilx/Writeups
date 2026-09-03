# HTB Sitelytic — SSRF to Redis RCE

> **Challenge:** HackTheBox — *Sitelytic* (Web, Hard, 1000 pts)  
> **Flag:** `HTB{n3w_r0u73_t0_D_r3d1sl4nD_w0rk3r_g3t5_y0u_1n!}`  
> **Given:** the full Symfony 6.1 source and a live instance  
> **Goal:** run `/readflag` (a program that prints the flag, owned by root)  
> **Class:** SSRF + CRLF Injection → PHP Object Injection → Twig Template Injection → Remote Code Execution  
> **Audience:** written to be followed from zero — every prerequisite is explained inline

---

## The idea in plain terms

Somewhere in this app there is a spot that runs a **template** built from user input — a classic "template injection" bug that normally means code execution. But the front door to it filters out the exact characters the attack needs, so it looks dead.

The trick of this challenge is that the same dangerous code can be reached by a **completely different route**. The app keeps a background job queue in **Redis** (a fast in-memory database). Jobs are stored as *serialized PHP objects*, and when the worker picks one up it rebuilds the object — and rebuilding a malicious object is itself an attack (PHP object injection). Redis is only reachable from inside the server, so I use an **SSRF** (I trick the server into making a request for me) plus a **header-injection trick** to write my malicious job straight into the queue. The worker eats it and I get command execution.

We'll build it in five moves: find the sink, see why the front door fails, find the back route, get the SSRF to talk to Redis, and fight through the protocol quirks that make it actually land.

> **Quick glossary (skim now, refer back later):**
> **SSTI (Server-Side Template Injection)** — a template engine turns a template string into output; if attacker input becomes part of the *template* rather than the *data*, the attacker's expressions get executed on the server.
> **Serialization / `unserialize`** — turning an object into a string to store it, and back again. In PHP, rebuilding an object can trigger the object's own methods, which is where the danger is.
> **SSRF (Server-Side Request Forgery)** — you make the *server* send an HTTP request of your choosing, often to things you couldn't reach yourself (like an internal-only service).
> **CRLF** — the two invisible characters `\r\n` that separate lines in HTTP and many text protocols. If you can inject them into a value, you can forge extra lines.
> **RCE (Remote Code Execution)** — running your own commands on the server. The end goal.

## 1. The sink: a template built from user input

Here is the dangerous code (`src/MessageHandler/SubscribeNotificationHandler.php`):

```php
public function __destruct()
{
    $this->twig = new \Twig\Environment(new FilesystemLoader(__DIR__ . '/../../templates'));
    $this->body = $this->twig->createTemplate(
        ...'&email='.$this->email.'">'...
    )->render();
}
```

`createTemplate()` compiles a string into a Twig template and runs it. Notice `$this->email` is glued **into the template source itself**, not passed in as a safe variable. So whatever is in `email` is treated as *template code* and executed. That's textbook SSTI. (A "sandbox" that would neuter this exists in the config file `services.yaml` — but it's commented out.)

> **Why is this method called `__destruct`?** In PHP, `__destruct()` is a "magic method": it runs automatically when an object is destroyed (garbage-collected). Remember that — it's the reason the attack works even when nobody deliberately "calls" anything. Just *creating* this object and letting it go is enough to fire the sink.

## 2. Why the front door doesn't work

You can reach that handler through `POST /subscribe`, but the email first passes a validator, `Assert\Email`. By trying a bunch of addresses against the live site, I can map out exactly which characters it allows:

| local part I tried | result |
|---|---|
| `{{7*7}}@a.com`, `a\|b@a.com`, `a'b@a.com`, `` a!#$%&*+/=?^_`{\|}~-@a.com `` | 200 (accepted) |
| `a(b)@a.com`, `a[b]@a.com`, `a b@a.com`, `a,b@a.com`, `a:b@a.com`, `"a b"@test.com`, `a@localhost` | 401 (rejected) |

That pattern is Symfony's "HTML5" email mode. Curly braces `{}`, pipes `|`, and quotes survive — but **parentheses, brackets, spaces, and commas are rejected**, and a proper domain is required.

Why does that kill the attack? Twig needs **parentheses** to call any function or pass any argument — `system('...')`, `map('system')`, and so on. Without parentheses, the only Twig you can write is basic tags and no-argument operations, and because this template runs in a bare, stripped-down Twig environment (no Symfony helpers like `app` or `dump`), there's nothing to pivot through. So through the front door there is genuinely **no way to reach code execution**. That dead end is the whole point of the challenge — the intended solution goes *around* the validator entirely.

## 3. The back route: a poisoned job in the queue

> **How background jobs work here.** Slow work (like sending a notification) isn't done during the web request. Instead the app drops a "message" onto a queue and a separate **worker** process handles it later. This app's queue is Redis: `MESSENGER_TRANSPORT_DSN=redis://localhost:6379/messages`. The messages are stored as **serialized PHP**, and Symfony's default decoder does this when the worker reads one:

```php
$envelope = $this->safelyUnserialize(stripslashes($encodedEnvelope['body']));
```

`unserialize()` is called on whatever bytes are in the queue. And `unserialize()` **rebuilds objects** — including our dangerous `SubscribeNotificationHandler`. Here's the beautiful part: the rebuilt object doesn't even need to be a valid queue message. The worker constructs it, notices "this isn't a real Envelope," throws it away — and when PHP throws it away, the object's `__destruct()` runs, firing the SSTI sink. And because this path never touches `Assert\Email`, **parentheses are allowed again**.

So the payload I want sitting in the Redis queue is a serialized object whose `email` field is a full Twig expression:

```php
O:47:"App\MessageHandler\SubscribeNotificationHandler":2:{
  s:5:"email";s:N:"{{['/readflag > /www/public/static/exports/f1337.txt 2>&1']|map('system')|join(',')}}";
  s:5:"token";s:1:"x";}
```

Read the email value in plain English: "run the command `/readflag` and save its output to a file in the site's public folder." When the worker rebuilds and discards this object, Twig executes that, and `/readflag`'s output — the flag — lands in a web-readable file I can then just download.

The only problem: Redis only listens on `127.0.0.1` (localhost). I can't connect to it from outside. I need the *server* to write to it for me — an SSRF.

## 4. Getting an SSRF to talk to Redis

There's an admin feature that fetches a URL to check if a service is up (`src/Service/ServiceChecker.php`):

```php
$parsedHeaders[strtolower(trim($hKey))] = trim($hVal);
...
array_walk($this->headers, static function(&$v, $k) { $v = $k.': '.$v; });
$context = stream_context_create(["http" => ["header" => implode("\r\n", $this->headers), ...]]);
$response = @file_get_contents($this->host, false, $context);
```

Two gifts here:

- The URL scheme check is only `preg_match("/^https?/i", ...)`, so `http://127.0.0.1:6379/` (Redis's port) passes. That's the SSRF — I can point the server's request at internal Redis.
- The header values are only cleaned with `trim()`, which strips whitespace from the **ends** of a string. It does **not** remove `\r\n` from the **middle**. So if I put a CRLF inside a header value, I forge extra lines into the outgoing request — this is CRLF injection, and it lets me write raw Redis commands into the connection.

> **Wait — why does writing HTTP headers let me send Redis commands?** Redis doesn't speak HTTP; it just reads whatever bytes arrive on the socket, line by line. When the server "makes an HTTP request" to Redis, Redis simply sees a stream of text. If I can control lines in that stream (via CRLF injection), I can make some of those lines be valid Redis commands. This general move — abusing one protocol's request to smuggle another protocol's commands — is why SSRF to internal services is so dangerous.

Getting to this feature needs a login, and the credentials `admin:admin` are sitting right in `migrations/db.sql`. I also confirmed the CRLF injection really works before trusting it: injecting a fake `Content-Length: 10` header into a request to the site's own Apache made the call hang for 20 seconds (Apache waiting for a request body that never came) instead of the normal 0.6 seconds. That stall proved my injected line was landing in the real request.

## 5. The part that actually costs hours: Redis keeps hanging up

Early attempts did… nothing. Silent failure. The cause is two security features colliding:

- PHP's HTTP client always adds its **own** `Host:` line to the request, before any of my headers.
- Redis has a cross-protocol guard: if the first word of a line it reads is exactly `post` or `host:`, it assumes something is trying to smuggle web traffic into it and **slams the connection shut with no reply**.

So Redis was killing the socket the moment it hit PHP's automatic `Host:` line — before ever reaching my injected commands. The total silence is exactly what you'd expect from a connection closed early.

The fix is a single clever line. PHP will skip adding its own `Host:` **if my headers already contain one**, but PHP only recognizes a `Host:` that sits at the very start of a line:

```c
if (s == headers || *(s-1) == '\n') return 1;   // only counts a match at a line start
```

So I inject the line `host:zzz` — note: **no space after the colon**. This one line does double duty:

- To **PHP** it looks like a `Host:` header at the start of a line, so PHP suppresses its own — Redis never sees the poisonous `host:` word.
- To **Redis** it splits on whitespace into the single word `host:zzz`, which is *not* the banned `host:`, so the guard stays quiet and Redis just treats it as an unknown command and moves on.

The full crafted header value looks like:

```
X-A: z\r\nhost:zzz\r\n<Redis XADD command>\r\nX-B: 1
```

The tell that it finally worked: the request stopped returning instantly and started **stalling** for the full socket timeout — meaning Redis was now holding the connection open and reading, instead of hanging up. I send the actual Redis commands in Redis's binary "RESP" format (rather than plain text) so that the quotes and spaces inside my PHP payload never get mangled by Redis's text-parsing rules.

## 6. Two dead ends worth recording

- **Trying to use Redis's `DEBUG SLEEP` as a timing signal.** Modern Redis ships with `DEBUG` disabled by default, so "no delay = no injection" was measuring nothing at all. Don't build an oracle on a command that might be turned off.
- **Trusting the app's own "service is up/down" message.** That check reported "down" *both* for a refused connection and for a successful connection that returned non-HTTP data — so it never actually distinguished reachable from unreachable. Every reliable signal had to be an out-of-band side effect (a stalled connection, a file appearing), never the app's own response text.

## 7. The whole chain in order

```
POST /admin/login              admin:admin   (found in migrations/db.sql)
POST /api/service/check        host = http://127.0.0.1:6379/
                               headers = {"X-A": "z\r\nhost:zzz\r\n<XADD ...>\r\nX-B: 1"}
   -> CRLF injection writes my lines into the request to Redis
   -> "host:zzz" hides PHP's own Host: line without tripping Redis's guard
   -> XADD drops my serialized PHP object onto the "messages" queue
the worker runs messenger:consume -> unserialize() rebuilds my object
   -> the object is discarded -> __destruct() runs -> Twig executes -> system('/readflag ...')
GET /static/exports/f1337.txt  -> read the flag out of the web-served file
```

One escaping detail: Symfony's encoder runs `addslashes()` on the message body and the decoder runs `stripslashes()`, so my serialized payload has to be pre-escaped to survive that round trip. And why write the flag to a file instead of getting it in a response? Because this SSRF is **blind** — the worker runs in the background with nowhere to send output — so I use a file in Apache's public folder as the delivery channel. The worker runs as root, so `system()` can do anything. Full script in [`solve.py`](./solve.py).

## 8. How the developers should have fixed it

- Never concatenate input into `Twig::createTemplate()` — render a real template file and pass the data as variables. And enable the sandbox that's already written (but disabled) in `services.yaml`.
- Don't use PHP's object serializer for a queue an attacker might reach; use the JSON serializer, and treat the message broker as untrusted.
- Validate the SSRF target against an allowlist, and **reject** header values that contain `\r` or `\n` instead of merely trimming their ends.
- Don't ship real credentials like `admin:admin` in migration files.

The thread running through this solve: never trust a single signal. The CRLF injection, the `Host:`-suppression trick, and the Redis write were each proven by an independent, out-of-band effect *before* the next step was built on top of it. On a blind, multi-stage chain like this, that discipline is the difference between progress and staring at silence.

## Further reading

If any concept above was new, these are solid starting points:

- [SSTI — PortSwigger Web Security Academy](https://portswigger.net/web-security/server-side-template-injection)
- [SSRF — PortSwigger Web Security Academy](https://portswigger.net/web-security/ssrf)
- [Insecure deserialization — PortSwigger](https://portswigger.net/web-security/deserialization)
- [PHP object injection — OWASP](https://owasp.org/www-community/vulnerabilities/PHP_Object_Injection)
- [PHP magic methods (`__destruct` etc.)](https://www.php.net/manual/en/language.oop5.magic.php)
- [CRLF injection / HTTP response splitting — OWASP](https://owasp.org/www-community/attacks/HTTP_Response_Splitting)
- [Redis serialization protocol (RESP)](https://redis.io/docs/latest/develop/reference/protocol-spec/)
- [Symfony Messenger component](https://symfony.com/doc/current/messenger.html)
- [Twig template documentation](https://twig.symfony.com/doc/3.x/)

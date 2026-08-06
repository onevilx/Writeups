# SSRF Denylist Bypass in ip-range-check via Abbreviated IPv4 Notation

**Advisory:** [GHSA-87xc-4hwr-pxf6](https://github.com/danielcompton/ip-range-check/security/advisories/GHSA-87xc-4hwr-pxf6) — **Published**
**CVE:** Requested by the maintainer, pending assignment
**Package:** [`ip-range-check`](https://www.npmjs.com/package/ip-range-check) (npm, ~390k downloads/week)
**Fixed in:** `v0.2.1`
**Class:** CWE-918 — Server-Side Request Forgery (validator/connector disagreement)
**Affected:** `<= 0.2.0`
**Status:** Reported → independently re-verified → patched → published.

## How I got here

This finding came out of a broader hunt for SSRF-guard bypasses, prompted by a simple observation: the `ip` npm package — one of the most widely used IP-utility libraries in the ecosystem — had already taken two separate CVEs (CVE-2023-42282, CVE-2024-29415) for the exact same shape of bug: an "is this a private IP" check that alternate representations of an address could slip past. If that bug class was real and had happened *twice* in the most popular library of its kind, the obvious next question was: which other, less-audited libraries doing the same job have the same gap and just haven't been looked at yet?

That's a search problem, not a guess. I started pulling in every mid-tier IP-range/SSRF-guard package I could find and testing them against the same style of payload.

## The sweep — what I ruled out first

Before landing on `ip-range-check`, I worked through several other candidates, and it's worth being honest about the ones that turned out to be dead ends, because ruling them out correctly is what made the eventual finding credible rather than a lucky first guess:

- **`request-filtering-agent`** and **`ssrf-req-filter`** (both high-download, well-designed) — these resist the entire class of bypass I was testing, because they don't validate the string the caller supplies. They **resolve the hostname first** (via `dns.lookup`) and then check the *resolved* address. Feeding them `2130706433` or `127.1` doesn't help an attacker, because by the time the check runs, the library is looking at the canonical `127.0.0.1` either way. Good design, nothing to find there.
- **`is-private-ip`** — this one *did* have a real, connect-verified bypass (several abbreviated forms slipped past its `isNonPublicIp` check). But it had roughly 28 downloads a week. A real bug in a library nobody uses isn't a useful CVE for anyone, so I didn't pursue it further.
- **`ip`, `private-ip`, `netmask`** — already carried the CVEs that started this whole search. Nothing new to report.

That left a gap: I wanted a library that was (a) popular enough to matter, (b) not already carrying an advisory, and (c) actually validating the raw string rather than resolving first.

## Landing on `ip-range-check`

`ip-range-check` fit all three: ~390,000 downloads/week, last published in 2022 with no existing security advisory, and — the detail that mattered — it doesn't resolve anything. It takes the caller's string directly and parses it itself, by delegating to `ipaddr.js`. Critically, it bundles its **own** copy of that dependency rather than relying on whatever version the host project has installed, which meant the parsing behavior wasn't necessarily current.

## Reading the source

The actual check is small:

```js
function check_single_cidr(addr, cidr) {
    try {
        var parsed_addr = ipaddr.process(addr)
        // ... match parsed_addr against the CIDR ...
    }
    catch (e) {
        return false   // "not in range" == allowed, for a denylist
    }
}
```

That `catch` block is the whole bug, once you see it in context. `ipRangeCheck(host, denylist)` is meant to be used like this:

```js
if (ipRangeCheck(host, PRIVATE_RANGES)) throw new Error('blocked')
```

`false` means "not in a private range" — which, for a *denylist*, means "allowed through." So any input the parser can't handle is treated the same as an input that's definitely public. That's backwards for a security check: an unparseable input should be the *more* suspicious case, not the safer one.

## Building a test corpus, not just a guess

Rather than hand-pick one weird string and hope, I built a small corpus of the classic IPv4 alternate-representation tricks and ran all of them through the library, with a canonical control (`127.0.0.1`, which must always be blocked) as a sanity check:

- Full decimal integer: `2130706433`
- Full hex integer: `0x7f000001`
- Full octal integer: `017700000001`
- Abbreviated dotted forms: `127.1`, `127.0.1`
- Mixed-radix forms: `0177.1`, `127.0x1`

The result was a genuine mix, which is what made it interesting rather than a blanket failure: the full decimal/hex/octal integer forms were **correctly blocked**. Only the abbreviated and mixed-radix forms slipped through:

```
127.1      -> ALLOWED (bypass)
127.0.1    -> ALLOWED (bypass)
0177.1     -> ALLOWED (bypass)
127.0x1    -> ALLOWED (bypass)
```

That split told me this wasn't a wholesale "the library doesn't work" situation — it was a specific parsing gap in the bundled `ipaddr.js`, which meant I needed to go verify what these strings actually *do* at the network layer, not just what the library thought of them.

## Confirming these are real, routable addresses

A string a validator rejects is only interesting if something downstream still accepts it. I checked each bypassing form against Node's own resolver (`dns.lookup`) to confirm they weren't just malformed noise:

```
127.1      -> 127.0.0.1
127.0.1    -> 127.0.0.1
0177.1     -> 127.0.0.1
127.0x1    -> 127.0.0.1
```

All four resolve to loopback via the OS's own `inet_aton`-style parsing rules — the same rules `http.get()` and friends rely on. So the validator and the connector genuinely disagreed: the library said "can't parse this, must not be private," while the network stack said "this is definitely 127.0.0.1."

## Making it undeniable: a connect-verified PoC

A mismatch between a parser and a resolver is suggestive, but the thing that actually proves SSRF is a real socket connection reaching somewhere it shouldn't. I built a small harness that binds a real HTTP server to loopback, builds the exact kind of denylist guard a real application would write, and then drives real `http.get()` calls through the bypassing hosts:

```js
const internal = http.createServer((_req, res) => res.end('INTERNAL-SECRET-DATA'))
await new Promise((r) => internal.listen(0, '127.0.0.1', r))

const guardAllows = (host) => !ipRangeCheck(host, PRIVATE_RANGES)

for (const host of ['127.1', '127.0.1', '0177.1', '127.0x1']) {
  if (!guardAllows(host)) continue   // would print "guard=BLOCKED"
  const body = await fetchVia(host, port)
  // body === "INTERNAL-SECRET-DATA"
}
```

Output:

```
Control - guard on canonical 127.0.0.1: allows=false (correctly blocked)
127.1      guard=ALLOWED  ->  fetch returned "INTERNAL-SECRET-DATA"   <== SSRF: reached internal service
127.0.1    guard=ALLOWED  ->  fetch returned "INTERNAL-SECRET-DATA"   <== SSRF: reached internal service
0177.1     guard=ALLOWED  ->  fetch returned "INTERNAL-SECRET-DATA"   <== SSRF: reached internal service
127.0x1    guard=ALLOWED  ->  fetch returned "INTERNAL-SECRET-DATA"   <== SSRF: reached internal service
```

The control (`127.0.0.1`) is correctly blocked in the same run, which matters — it proves the harness itself works and the bypass isn't an artifact of a broken test.

## Being honest about the limits of the bug

Before writing anything up, I checked how this behaves against the modern URL parser, because it directly determines how exploitable this actually is in a real application. The WHATWG `new URL()` parser **canonicalizes** `127.1` to `127.0.0.1` before an application would ever hand it to the guard — at which point the guard correctly blocks it. The bug only matters when the **raw** host string reaches both the guard and the connector unmodified: a raw user-supplied "host" field, or the legacy `url.parse().hostname`, which preserves `127.1` verbatim.

I put that limitation directly in the report rather than let it surface later. Understating a finding's practical reach costs nothing and buys credibility; overclaiming costs credibility the first time someone checks it themselves.

## Precedent, one more time

The last thing I did before writing the report was confirm this was the same bug *class*, not just a similar-looking one, as the two prior `ip` package CVEs (CVE-2023-42282, CVE-2024-29415) — both were about alternate IPv4 representations being misclassified as public. That precedent is what turns "I found a parsing quirk" into "this is a recognized, previously-paid vulnerability class that happens to have a fresh, unaudited instance here."

## Writing and sending the report

`ip-range-check` had no `SECURITY.md` and no private vulnerability reporting enabled on GitHub, so I emailed the maintainer directly, with the full technical writeup — root cause, the four bypasses, the `dns.lookup` confirmation, the honest scope caveat about `new URL()`, the `ip`-package precedent, and the complete PoC script pasted inline (since I wasn't able to attach the `.mjs` file directly).

## The response

Daniel Compton didn't just take the report at face value — he **independently re-verified every one of the four bypasses against Node's own `dns.lookup()`** himself before doing anything else, confirming the resolution mismatch was real rather than trusting my numbers. Only then did he move to the fix.

## The fix

`ip-range-check@0.2.1` upgrades the bundled `ipaddr.js` from `1.9.1` to `2.5.0`, which parses these abbreviated and mixed-radix forms using the same `inet_aton`-style rules the OS resolver applies — closing the exact gap between validator and connector that caused the bypass. He also added a dedicated regression test suite covering this input class, and re-ran my original PoC against the patched version to confirm all four forms are now correctly blocked before publishing.

## Disclosure timeline

- **Reported** privately by email (no `SECURITY.md` / private reporting available on the repo).
- **Maintainer replied**, independently reproduced all four bypasses against `dns.lookup()`, confirmed the root cause in `check_single_cidr()`.
- **Fix shipped** as `v0.2.1` with a dedicated regression suite; my PoC re-run and confirmed blocked against the patch.
- **Advisory published**: [GHSA-87xc-4hwr-pxf6](https://github.com/danielcompton/ip-range-check/security/advisories/GHSA-87xc-4hwr-pxf6), crediting "Youssef Aboukir (onevilx)."
- **CVE requested** by the maintainer, pending assignment.

A fast, careful, independently-verified response — notable given this is a solo-maintained package with no dedicated security process, not a company with a security team on call.

## Takeaways

- **A validator/connector disagreement is a durable, re-findable bug class.** The specific strings change, but the shape — "the OS resolver accepts input the security check's parser rejects" — repeats across libraries, and precedent (the `ip` package's two prior CVEs) is a legitimate map for where to look next.
- **Ruling things out is part of the work.** `request-filtering-agent` and `ssrf-req-filter` weren't vulnerable, and knowing *why* (resolve-then-check design) sharpened what to look for in the next candidate rather than wasting more time on already-hardened libraries.
- **A partial bypass is more convincing than a blanket one.** The fact that full decimal/hex/octal forms were correctly blocked, while only the abbreviated forms leaked through, showed this was a specific, fixable parsing gap rather than "the whole library doesn't work" — which is both more credible and more useful to the maintainer trying to fix it.
- **State your own finding's limits before someone else does.** Being upfront that this doesn't work through `new URL()` normalization didn't weaken the report — it's what made the parts that genuinely are exploitable land as credible rather than oversold.

## References

- [GHSA-87xc-4hwr-pxf6](https://github.com/danielcompton/ip-range-check/security/advisories/GHSA-87xc-4hwr-pxf6) — this advisory
- CWE-918 — Server-Side Request Forgery
- CVE-2023-42282, CVE-2024-29415 — the identical bug class in the `ip` package

---

*Reported by Youssef Aboukir (onevilx). Thanks to Daniel Compton for the careful, independent verification and fast fix on a project he's maintained solo for years.*

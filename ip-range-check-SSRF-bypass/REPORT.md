# SSRF denylist bypass in `ip-range-check` via abbreviated / alternate IPv4 notation

**Package:** `ip-range-check` (npm)
**Affected version:** `0.2.0` (latest; last published 2022-06-19)
**Downloads:** ~390k/week
**Class:** CWE-918 (SSRF) / CWE-1286 (improper validation of IP address syntax) — improper IP address canonicalization
**Existing advisory:** none found (`npm audit` reports 0 vulnerabilities for a project whose only dependency is this package; not present in GitHub Advisory DB or Snyk as of 2026-08-03)
**Status:** confirmed, connect-verified PoC; not yet disclosed

## Summary

`ip-range-check(addr, ranges)` returns whether `addr` falls within one or more
CIDR ranges. It is widely used as an SSRF guard — an application builds a denylist
of private/internal CIDR ranges and rejects any user-supplied host that matches:

```js
const PRIVATE = ['127.0.0.0/8','10.0.0.0/8','172.16.0.0/12','192.168.0.0/16','169.254.0.0/16', ...]
if (ipRangeCheck(host, PRIVATE)) throw new Error('blocked')   // reject internal targets
await fetch(host)                                             // otherwise proceed
```

Several **abbreviated / alternate IPv4 representations that the operating system's
socket layer routes to a private address** are not recognised by `ip-range-check`.
For these inputs the function returns `false` ("not within any private range"), the
guard treats the host as public, and the subsequent connection reaches the internal
service — a Server-Side Request Forgery bypass.

Confirmed bypass inputs (each routes to `127.0.0.1`, guard returns `false`):

| Input      | OS routes to | `ipRangeCheck(input, ['127.0.0.0/8'])` |
|------------|--------------|-----------------------------------------|
| `127.1`    | 127.0.0.1    | `false`  (bypass)                       |
| `127.0.1`  | 127.0.0.1    | `false`  (bypass)                       |
| `0177.1`   | 127.0.0.1    | `false`  (bypass)                       |
| `127.0x1`  | 127.0.0.1    | `false`  (bypass)                       |
| `127.0.0.1`| 127.0.0.1    | `true`   (correctly blocked — control)  |

The same class of abbreviated forms also evades the RFC1918 ranges (`10.1` →
10.0.0.1, `192.168.257` → 192.168.1.1, etc.); the four above are additionally
verified end-to-end against a live loopback HTTP service in the PoC.

## Root cause

`ip-range-check@0.2.0` bundles `ipaddr.js@1.9.1` and is implemented as:

```js
function check_single_cidr(addr, cidr) {
    try {
        var parsed_addr = ipaddr.process(addr);
        // ... match parsed_addr against the CIDR ...
    }
    catch (e) {
        return false           // <-- any parse failure == "not in range" == allowed
    }
}
```

Two facts combine:

1. **`ipaddr.js@1.9.1` throws on abbreviated IPv4 forms.** It parses full decimal,
   hex, and octal integer forms (`2130706433`, `0x7f000001`, `017700000001` — these
   are therefore correctly blocked), but throws on the classic BSD/`inet_aton`
   shorthands: `a.b`, `a.b.c`, and mixed-radix parts such as `127.0x1` and `0177.1`.
   Verified directly against the exact nested copy the package loads.

2. **`ip-range-check` treats a parse failure as "not in range" (`return false`).**
   For an allowlist this is merely a false negative; for an SSRF **denylist** it is
   fail-open: an unparseable-but-routable host is reported as *not* private and is
   allowed through.

Meanwhile the platform resolver (`getaddrinfo`/`inet_aton`, used by Node's
`net.connect` / `http.get`) *does* accept these shorthands and routes them to the
private address. The validator and the connector disagree — the defining shape of
an SSRF filter bypass.

## Proof of concept

See [`poc/poc.mjs`](poc/poc.mjs). It binds an internal HTTP service to
`127.0.0.1`, builds the denylist guard above, and shows each attacker host passing
the guard and then returning `INTERNAL-SECRET-DATA`:

```
Control — guard on canonical 127.0.0.1: allows=false (correctly blocked)

  127.1      guard=ALLOWED  ->  fetch returned "INTERNAL-SECRET-DATA"   <== SSRF: reached internal service
  127.0.1    guard=ALLOWED  ->  fetch returned "INTERNAL-SECRET-DATA"   <== SSRF: reached internal service
  0177.1     guard=ALLOWED  ->  fetch returned "INTERNAL-SECRET-DATA"   <== SSRF: reached internal service
  127.0x1    guard=ALLOWED  ->  fetch returned "INTERNAL-SECRET-DATA"   <== SSRF: reached internal service
```

Reproduce:

```sh
cd poc && npm install && node poc.mjs
```

## Impact and realistic attack surface (honest scoping)

Impact: an application that uses `ip-range-check` to block internal address ranges
before making an outbound request can be induced to connect to loopback / RFC1918 /
link-local (incl. `169.254.169.254` cloud metadata) targets by supplying an
abbreviated IPv4 host — the standard consequence of an SSRF filter bypass.

This requires the **raw host string** to reach both the guard and the connector.
That is the case when:

- the host comes from a raw user field (e.g. a "server address" / webhook host input), or
- the URL is parsed with Node's legacy `url.parse()`, whose `.hostname` preserves
  `127.1` verbatim (confirmed).

It is **not** exploitable when the application first normalises through the WHATWG
`new URL()` parser, which canonicalises `127.1` → `127.0.0.1` (that normalised value
*is* then blocked by `ip-range-check`). This limitation is stated plainly so the
severity is not overstated: the bug is a genuine, fail-open validation flaw in a
security-relevant library, exploitable in the common raw-host / legacy-parse
patterns, not a universal remote exploit against every consumer.

## Precedent (this class is CVE-worthy)

The identical bug class in the sibling `ip` package received two CVEs:

- **CVE-2023-42282** — `ip.isPublic()` misidentifies alternate forms such as
  `0x7F.1` as public, leading to SSRF.
- **CVE-2024-29415** — incomplete fix for the above; canonicalization still
  incomplete.

`ip-range-check` performs the same category of check and has no advisory.

## Suggested fix

- Do not `return false` on parse failure in a function used for denial decisions;
  distinguish "not in range" from "unparseable". Prefer rejecting/canonicalising
  unparseable input, or upgrade the IP parser so abbreviated forms are canonicalised
  before comparison.
- Upgrade the bundled `ipaddr.js`, and/or canonicalise the address (e.g. via the
  platform resolver or a spec-accurate `inet_aton`) prior to range comparison so the
  validator agrees with the connector.
- Document that the library must be given already-canonicalised input and is not by
  itself an SSRF-safe filter for raw user input.

## Disclosure plan

- No `SECURITY.md` on the repo (`danielcompton/ip-range-check`); package last
  published 2022 and may be lightly maintained.
- Recommended: submit via **huntr.com** (validates and routes OSS reports to CVE
  IDs, and does not depend on maintainer responsiveness), and in parallel open a
  private GitHub Security Advisory on the repo. This report + `poc/` are ready to
  attach.
- Do not open a public issue or publish before coordinated disclosure completes.

## Files

- `poc/poc.mjs` — self-contained, connect-verified PoC (fresh `npm install`)
- `poc/package.json` — pins `ip-range-check@0.2.0`

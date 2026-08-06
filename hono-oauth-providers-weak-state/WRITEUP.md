# OAuth State and PKCE Code Verifier Generated with Math.random() in @hono/oauth-providers

**Advisory:** [GHSA-6833-cxmv-fqjf](https://github.com/honojs/middleware/security/advisories/GHSA-6833-cxmv-fqjf) — **Published**
**CVE:** No known CVE
**Package:** `@hono/oauth-providers` (npm)
**Fixed in:** `v0.8.7`
**Class:** CWE-338 — Use of Cryptographically Weak PRNG
**Severity:** Moderate (CVSS 3.1 — `AV:N/AC:H/PR:N/UI:R/S:U/C:L/I:L/A:N`)
**Affected:** `<= 0.8.6`
**Status:** Reported → confirmed → patched → published.

## How I found it

OAuth libraries implement two values that are supposed to carry real cryptographic weight but are easy to generate carelessly if you're not thinking about it as a security primitive rather than "just a random string": the `state` parameter (the flow's anti-CSRF token) and, for providers using PKCE, the `code_verifier`. Both have hard requirements in their respective specs — `state` must be unguessable, and RFC 7636 explicitly requires the PKCE verifier to come from a cryptographically secure generator. Auditing how a library actually produces these values is a direct, mechanical way to check whether it's meeting that bar.

`@hono/oauth-providers` generates both in two small utility files, `src/utils/getRandomState.ts` and `src/utils/getCodeChallenge.ts`:

```ts
// getRandomState.ts — used by every provider
const rand = () => Math.random().toString(36).substr(2)
export function getRandomState() {
  return `${rand()}-${rand()}-${rand()}`
}

// getCodeChallenge.ts — X/Twitter provider's PKCE code_verifier
const length = Math.floor(Math.random() * (128 - 43 + 1)) + 43
// ...characters.charAt(Math.floor(Math.random() * characters.length))...
```

Both are built entirely on `Math.random()`. I confirmed this was present in the shipped 0.8.6 artifact across the following affected providers: **google, github, discord, facebook, twitch, x, linkedin, msentra**.

## Why that's a real problem, not a style nitpick

`Math.random()` is not a cryptographically secure PRNG, and the gap isn't theoretical. V8 implements it as xorshift128+ — a fast, high-quality PRNG for simulations and games, but one whose internal 128-bit state is recoverable from a small number of observed outputs. Once that state is recovered, every subsequent output is deterministic, not random.

Two details make this specific to OAuth flows rather than a generic "don't use Math.random for security" note:

- The generator is a single stream shared across every request handled by the same isolate — it isn't reseeded or scoped per-request.
- Each authorization request leaks a fresh state value directly in the redirect URL — which is, by design, visible to whoever initiated that request.

Put together: an attacker able to sample enough outputs of the shared stream (by initiating their own OAuth flows against the same app and reading the state values they get back) can, in principle, predict state values issued to other concurrent requests on the same instance — defeating the exact protection the parameter exists to provide. On the X/Twitter provider, the identical weakness applies to the `code_verifier`, which is what would otherwise bind a callback to the browser that actually started the flow.

## Confirming it wasn't just a description

Rather than argue this from the source alone, I built a small, self-contained proof that captures the exact `Math.random()` draws a single `getRandomState()` call consumes, and reconstructs the same token from nothing but those draws:

```js
const rand = () => Math.random().toString(36).slice(2)
const getRandomState = () => `${rand()}-${rand()}-${rand()}`

const draws = []
const real = Math.random
Math.random = () => { const v = real(); draws.push(v); return v }

const token = getRandomState()
Math.random = real

const rebuilt = draws.map((d) => d.toString(36).slice(2)).join('-')

console.log('issued state token: ', token)
console.log('rebuilt from draws: ', rebuilt)
console.log('identical:', token === rebuilt)  // -> true
```

The token is a pure function of exactly three `Math.random()` outputs — no hidden entropy, nothing beyond what those three draws determine. That's the concrete demonstration that the value carries no more unpredictability than V8's PRNG state itself, which is the thing that's recoverable.

## Honest scope

Two things worth stating plainly, both of which ended up in the maintainer's own published advisory:

- Applications that supply their own state through the `state` option — available on googleAuth, msentraAuth, and twitchAuth — never reach the affected code path for that value. This is a library-default issue, not a universal one across every possible configuration.
- Full exploitation is intricate. Recovering the generator's internal state and aligning that recovery with a concurrent request in time is a real, non-trivial attack, not a one-line exploit. The severity here comes from the weakness being unconditional (CWE-338 doesn't require proving a live attack to be real), and from the PKCE `code_verifier` case being a direct, unambiguous spec violation on its own — that half doesn't need a timing argument at all.

I'd rather a report undersell exploitability slightly than have someone else find the gap in a claim later; both of those caveats went into the original disclosure exactly as written above.

## Suggested fix

```ts
export function getRandomState() {
  return crypto.randomUUID() + crypto.randomUUID()
}

function generateRandomString() {
  const bytes = crypto.getRandomValues(new Uint8Array(64))
  return base64URLEncode(String.fromCharCode(...bytes))
}
```

`crypto.getRandomValues()` and `crypto.randomUUID()` are available across every runtime this library targets — Workers, Deno, Bun, and Node 18+ — so there's no platform reason the weak generator was necessary.

## Reporting it

`honojs/middleware` had no `SECURITY.md` and no private vulnerability reporting enabled at the time, so I emailed the maintainer, Yusuke Wada, directly with the technical breakdown, the affected code, the deterministic-reconstruction PoC, and the suggested fix — plus one smaller, secondary note: the X provider was setting its state and code-verifier cookies without the Secure attribute (commented out in the source), which would allow them to be transmitted over plaintext HTTP.

Before submitting this report, I explicitly checked if this overlapped with Yusuke's recent advisory on the same repo (GHSA-fm3f-ch8h-qw8q: "state check fails open on omitted state"). In the email, I made a point of distinguishing the two: while the prior advisory dealt with the check failing when `state` was omitted, my report was strictly about the cryptographic weakness of the generated randomness itself, which was still fully present in version 0.8.6.

## The response

Yusuke replied quickly, asked for my GitHub username so he could credit me directly as reporter, and published [GHSA-6833-cxmv-fqjf](https://github.com/honojs/middleware/security/advisories/GHSA-6833-cxmv-fqjf) shortly after — Moderate severity, CWE-338, fixed in 0.8.7. The published advisory's language on impact and the exploitation caveat matches what was in the original report closely, which is a good sign the technical substance came through cleanly rather than getting compressed or softened in translation.

## Disclosure timeline

- **Reported by email** — no `SECURITY.md` on the repo at the time.
- **Same-day reply** from Yusuke; GitHub username exchanged for credit.
- **Advisory published**: GHSA-6833-cxmv-fqjf, fixed in v0.8.7.
- **CVE**: Unassigned. The vulnerability was published exclusively as a GitHub Security Advisory (GHSA), consistent with the maintainer's approach to prior advisories on this project.

## Takeaways

- **Randomness generation is worth auditing directly, not just trusting.** `getRandomState` / `getCodeChallenge`-style utility functions are exactly the kind of small, easy-to-overlook file where "just use `Math.random()`, it's just a string" slips in, even in an otherwise well-built library.
- **A deterministic-reconstruction PoC is a clean way to prove weak entropy** without needing to build out the full state-recovery attack — showing a token is a pure function of a handful of `Math.random()` outputs is enough to demonstrate the weakness is real, even while being honest that the full attack chain is more involved.
- **A CVE is not the only metric of impact.** A published, credited advisory (like a GHSA) provides concrete evidence of the vulnerability and the research, regardless of whether a CVE ID is assigned.

## References

- [GHSA-6833-cxmv-fqjf](https://github.com/honojs/middleware/security/advisories/GHSA-6833-cxmv-fqjf) — this advisory
- RFC 6749 §10.12 — the state parameter and CSRF
- RFC 7636 §7.1 — PKCE `code_verifier` generation requirements
- CWE-338 — Use of Cryptographically Weak PRNG

---

*Reported by Youssef Aboukir (onevilx). Thanks to Yusuke Wada for the fast response and for approving this writeup.*

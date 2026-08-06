# GHSA submission fields — @hono/oauth-providers weak randomness

Paste these into the honojs/middleware "Report a vulnerability" form.

---

**Title:**
Insecure randomness (CWE-338): OAuth `state` and PKCE `code_verifier` generated with `Math.random()` in @hono/oauth-providers

**Ecosystem:** npm
**Package name:** @hono/oauth-providers
**Affected versions:** <= 0.8.6 (all published versions; latest at time of report)
**Patched versions:** none yet

**Severity (suggested):** Moderate
**CVSS 3.1 vector (suggested):** `CVSS:3.1/AV:N/AC:H/PR:N/UI:R/S:U/C:L/I:L/A:N`  (≈ 4.2, Medium)
> Rationale for AC:H and UI:R: exploitation requires recovering V8's shared
> `Math.random()` stream and timing-aligning with the victim's draw, plus victim
> interaction for the CSRF. The underlying weakness (CWE-338) is unconditional;
> the CVSS reflects practical exploitation honestly rather than worst-case.

**CWE:** CWE-338 (Use of Cryptographically Weak PRNG); CWE-330; leads to CWE-352 (CSRF)

---

**Relationship to GHSA-fm3f-ch8h-qw8q (already fixed in 0.8.6)**

This is a *separate* root cause from your recent advisory GHSA-fm3f-ch8h-qw8q
("state check fails open on omitted state", fixed in 0.8.6). That advisory
explicitly scoped itself to the omission of the state parameter and noted it does
*not* concern weak randomness. This report covers the randomness of the generated
`state` (and PKCE `code_verifier`), which is still present in 0.8.6. The two are
independent and both weaken the same CSRF protection.

**Request:** please consider requesting a CVE ID via GitHub when publishing this
advisory — happy to provide any additional detail needed for that.

**Summary**

`@hono/oauth-providers` generates the OAuth 2.0 `state` parameter — the anti-CSRF
token — with `Math.random()`, a non-cryptographic PRNG. The X/Twitter provider
additionally generates its PKCE `code_verifier` with `Math.random()`.

The PKCE `code_verifier` case is a direct violation of RFC 7636 §7.1, which
requires the verifier to be produced by a cryptographically secure RNG. The
`state` case defeats the CSRF protection the middleware exists to provide (the
code comments it as "Avoid CSRF attack by checking state").

**Vulnerable code**

```ts
// src/utils/getRandomState.ts  — used by ALL providers
const rand = () => Math.random().toString(36).substr(2)
export function getRandomState() { return `${rand()}-${rand()}-${rand()}` }

// src/utils/getCodeChallenge.ts — used by the X/Twitter provider (PKCE)
function generateRandomString() {
  const length = Math.floor(Math.random() * (128 - 43 + 1)) + 43
  return Array.from({ length }, () =>
    chars.charAt(Math.floor(Math.random() * chars.length))).join('')
}
```

Confirmed present in the shipped `0.8.6` artifact (`dist/objectToQuery-*.mjs`,
`dist/x/index.mjs`).

**Affected providers:** google, github, discord, facebook, twitch, x, linkedin,
msentra (all use `getRandomState`). X additionally uses the weak PKCE verifier.

**Why Math.random() is unsafe**

V8's `Math.random()` is `xorshift128+` with a 128-bit state that is recoverable
from a few observed outputs; thereafter all outputs are deterministic. It is a
single per-isolate stream shared across all requests, and each OAuth initiation
leaks a fresh `state` in the redirect URL — so an attacker can sample the very
stream that produces other users' tokens.

**Impact**

- CSRF in the OAuth login flow (login CSRF / forced login / account linking) via
  a predictable `state`.
- Weakened PKCE for the X provider (predictable `code_verifier` undermines the
  protection against authorization-code interception).

**Proof of concept**

(attach `poc/poc_weak_state.mjs`) It reproduces `getRandomState()` verbatim and,
using V8's exact `xorshift128+`, shows the token stream is fully deterministic
given the recoverable PRNG state. It does not reproduce live end-to-end state
recovery (a documented SMT-based technique) — the defect is established from the
source; the recovery step is cited.

**Fix**

```ts
export function getRandomState() {
  return crypto.randomUUID() + crypto.randomUUID()
}
function generateRandomString() {
  const bytes = crypto.getRandomValues(new Uint8Array(64))
  return base64URLEncode(String.fromCharCode(...bytes))
}
```
`crypto.getRandomValues` / `crypto.randomUUID` are available on all of the
library's runtime targets (Workers, Deno, Bun, Node 18+).

**Secondary (mention, not headline):** the X provider sets the `state` and
`code-verifier` cookies without the `Secure` attribute (commented out in
`xAuth.ts`), allowing transmission over plaintext HTTP.

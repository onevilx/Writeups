# Insecure randomness (CWE-338) in `@hono/oauth-providers`: OAuth `state` (anti-CSRF) and PKCE `code_verifier` generated with `Math.random()`

**Package:** `@hono/oauth-providers` (npm), part of the `honojs/middleware` monorepo
**Affected version:** `0.8.6` (latest at time of writing)
**Downloads:** ~15.5k/week
**Class:** CWE-338 (Use of Cryptographically Weak PRNG) / CWE-330 (Use of Insufficiently Random Values); leads to CWE-352 (CSRF) in the OAuth flow
**Existing advisory:** none found for this issue (checked GitHub Advisory DB / web, 2026-08-03)
**Status:** confirmed by code inspection + PoC; not yet disclosed

## Summary

`@hono/oauth-providers` implements OAuth 2.0 login middleware for eight identity
providers (Google, GitHub, Discord, Facebook, Twitch, X/Twitter, LinkedIn,
Microsoft Entra). For CSRF protection it issues an OAuth `state` parameter, stores
it in a cookie, and validates it on the callback — the code explicitly comments
*"Avoid CSRF attack by checking state"*.

That `state` value is generated with **`Math.random()`**, a non-cryptographic PRNG:

```ts
// src/utils/getRandomState.ts
const rand = () => {
  return Math.random().toString(36).substr(2)
}
export function getRandomState() {
  return `${rand()}-${rand()}-${rand()}`
}
```

The X/Twitter provider additionally derives the **PKCE `code_verifier`** from
`Math.random()`:

```ts
// src/utils/getCodeChallenge.ts
function generateRandomString() {
  const characters = 'ABC...xyz0123456789-._~'
  const length = Math.floor(Math.random() * (128 - 43 + 1)) + 43
  const randomString = Array.from({ length }, () =>
    characters.charAt(Math.floor(Math.random() * characters.length))
  ).join('')
  return randomString
}
```

Both values are security-critical and both are required by their specifications to
be unpredictable:

- The OAuth `state` parameter is the CSRF token that binds the authorization
  response to the user agent that started the flow (RFC 6749 §10.12).
- The PKCE `code_verifier` **MUST** be generated with a cryptographically secure
  random number generator with sufficient entropy (RFC 7636 §7.1).

`Math.random()` satisfies neither requirement.

## Affected code paths

All eight providers generate `state` via `getRandomState()`:

```
src/providers/{google,github,discord,facebook,twitch,x,linkedin,msentra}/*Auth.ts
```

The X/Twitter provider additionally uses `getCodeChallenge()` (PKCE) built on the
same `Math.random()` source.

## Why `Math.random()` is unsafe here

V8's `Math.random()` is the `xorshift128+` PRNG with a 128-bit internal state. It
is **not** a CSPRNG:

- Its 128-bit state is recoverable from a small number of observed outputs
  (well-documented; e.g. solving the truncated-mantissa relation with an SMT
  solver). Once recovered, all past and future outputs — and therefore all
  `state` / `code_verifier` values — are deterministic.
- `Math.random()` is a single per-isolate stream shared by every request handled
  in the server process. An attacker can *sample* that stream directly, because
  each OAuth initiation returns a fresh `state` in the redirect URL (`?state=...`).
  By initiating their own OAuth flows, the attacker observes consecutive outputs
  of the very stream that also produces other users' `state` values.

## Proof of concept

See [`poc/poc_weak_state.mjs`](poc/poc_weak_state.mjs). It (1) reproduces the
library's `getRandomState()` verbatim, and (2) implements V8's exact
`xorshift128+` transform to show that, given a recovered 128-bit state, the token
stream is fully deterministic — i.e. the tokens carry no entropy beyond the
recoverable PRNG state:

```
Predicted token from a fixed (recovered) RNG state, run #1: 2jr5j0hsqqs-snmgefpl7ss-bvtv4kn7k7v
Predicted token from the same recovered RNG state, run #2: 2jr5j0hsqqs-snmgefpl7ss-bvtv4kn7k7v
Deterministic (identical) => true
```

Run: `node poc/poc_weak_state.mjs`

**Honest scope of the PoC:** it proves the generator is non-cryptographic and its
output is fully determined by the recoverable `xorshift128+` state. It does *not*
re-implement the end-to-end state-recovery from live observed outputs (that step
uses a published SMT-based technique and is cited, not reproduced). The core
defect — a security token generated with a non-CSPRNG — is established directly
from the source and does not depend on the recovery being reproduced here.

## Impact

- **CSRF in the OAuth login flow (login CSRF / forced login / account linking).**
  The `state` CSRF token is predictable. Following the standard predictable-CSRF-
  token pattern, an attacker who recovers the shared `Math.random()` stream can
  predict the `state` a victim's flow will use and craft a cross-site callback
  that passes the `state === storedState` check, defeating the protection the
  middleware exists to provide. Practical exploitation requires RNG-state recovery
  and timing alignment of the victim's RNG draw, so this is intricate rather than
  one-click — but it follows a recognized, documented attack pattern and the
  underlying weakness (CWE-338) is unconditional.
- **Weakened PKCE (X/Twitter provider).** A predictable `code_verifier` undermines
  PKCE's protection against authorization-code interception (RFC 7636), the exact
  threat PKCE exists to mitigate.

## Suggested fix

Generate both values with a CSPRNG available in all Hono runtimes via WebCrypto:

```ts
// state
export function getRandomState() {
  return crypto.randomUUID() + crypto.randomUUID()
}

// PKCE code_verifier
function generateRandomString() {
  const bytes = crypto.getRandomValues(new Uint8Array(64))
  return base64URLEncode(String.fromCharCode(...bytes)) // -> 43..128 unreserved chars
}
```

`crypto.getRandomValues` / `crypto.randomUUID` are available on Workers, Deno,
Bun, and Node (18+), matching the library's runtime targets.

## Disclosure plan

- Report privately via the `honojs/middleware` repository's **Security** tab
  ("Report a vulnerability" / GitHub Security Advisory). The Hono org actively
  publishes GHSAs (e.g. GHSA-m732-5p4w-x69g, GHSA-r354-f388-2fhh), so this is the
  correct channel and mints a CVE on acceptance.
- Reference all eight affected providers and the X/Twitter PKCE path. This report
  and `poc/` are ready to attach.
- Coordinated disclosure; no public issue until a fix ships.

## Files

- `poc/poc_weak_state.mjs` — reproduces the generator + V8 xorshift128+ determinism demo

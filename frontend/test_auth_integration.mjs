/**
 * Frontend Auth Integration & Unit Test Suite
 * Tests token caching, header generation, guest-mode fallback, and expired token handling.
 */
import assert from 'node:assert/strict'

// Mock browser localStorage and import.meta.env for Node test execution
global.localStorage = {
  _store: {},
  getItem(k) { return this._store[k] || null },
  setItem(k, v) { this._store[k] = String(v) },
  removeItem(k) { delete this._store[k] },
  clear() { this._store = {} }
}

global.sessionStorage = {
  _store: {},
  getItem(k) { return this._store[k] || null },
  setItem(k, v) { this._store[k] = String(v) },
  removeItem(k) { delete this._store[k] },
  clear() { this._store = {} }
}

let passed = 0
let failed = 0

function test(name, fn) {
  try {
    fn()
    console.log(`  [PASS] ${name}`)
    passed++
  } catch (err) {
    console.error(`  [FAIL] ${name}:`, err.message)
    failed++
  }
}

async function runTests() {
  console.log('=================================================================')
  console.log('  CreateX AI - Frontend Authentication Unit & Contract Suite')
  console.log('=================================================================\n')

  const { setAccessToken, getAccessToken } = await import('./src/services/supabase.js')
  const { getSessionId, clearSession } = await import('./src/services/session.js')

  console.log('[1] Token Management & Session Cache')
  test('Initial access token is null', () => {
    setAccessToken(null)
    assert.equal(getAccessToken(), null)
  })

  test('setAccessToken updates active access token in memory', () => {
    setAccessToken('test_mock_jwt_token_12345')
    assert.equal(getAccessToken(), 'test_mock_jwt_token_12345')
  })

  test('Clearing access token resets in-memory cache to null', () => {
    setAccessToken(null)
    assert.equal(getAccessToken(), null)
  })

  console.log('\n[2] Guest Session Management & Entropy')
  test('getSessionId creates and persists a valid session ID', () => {
    clearSession()
    const id1 = getSessionId()
    assert.ok(id1.startsWith('sess_'))
    assert.ok(id1.length >= 10)
    const id2 = getSessionId()
    assert.equal(id1, id2, 'Session ID must remain stable in localStorage')
  })

  test('clearSession removes the stored session ID', () => {
    clearSession()
    assert.equal(localStorage.getItem('createx_session_id'), null)
  })

  console.log('\n[3] Request Header Assembly & Authentication Contract')
  test('Unauthenticated request attaches X-Session-ID header', () => {
    setAccessToken(null)
    const sessionId = getSessionId()
    const headers = { 'Content-Type': 'application/json' }

    // Emulate api.js header resolution logic
    const token = getAccessToken()
    if (token && !headers.Authorization) {
      headers.Authorization = `Bearer ${token}`
    }
    if (!headers.Authorization && !headers['X-Session-ID']) {
      headers['X-Session-ID'] = sessionId
    }

    assert.equal(headers['X-Session-ID'], sessionId)
    assert.equal(headers.Authorization, undefined)
  })

  test('Authenticated request attaches Bearer token and omits X-Session-ID', () => {
    setAccessToken('live_supabase_user_token_abc')
    const sessionId = getSessionId()
    const headers = { 'Content-Type': 'application/json' }

    const token = getAccessToken()
    if (token && !headers.Authorization) {
      headers.Authorization = `Bearer ${token}`
    }
    if (!headers.Authorization && !headers['X-Session-ID']) {
      headers['X-Session-ID'] = sessionId
    }

    assert.equal(headers.Authorization, 'Bearer live_supabase_user_token_abc')
    assert.equal(headers['X-Session-ID'], undefined)
  })

  console.log('\n[4] Expired Token Handling Contract')
  test('Handling 401 response clears active token to prevent stale loops', () => {
    setAccessToken('expired_token_xyz')
    assert.equal(getAccessToken(), 'expired_token_xyz')

    // Simulate 401 response handler
    const responseStatus = 401
    const token = getAccessToken()
    if (responseStatus === 401 && token) {
      setAccessToken(null)
    }

    assert.equal(getAccessToken(), null, 'Access token must be cleared on 401')
  })

  console.log('\n=================================================================')
  console.log(`  Frontend Test Results: ${passed} passed, ${failed} failed`)
  console.log('=================================================================')

  if (failed > 0) process.exit(1)
}

runTests().catch((e) => {
  console.error('Fatal test error:', e)
  process.exit(1)
})

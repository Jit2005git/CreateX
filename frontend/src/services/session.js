/**
 * Demo Session Management
 * Generates and persists a session ID in localStorage.
 * No authentication required for the MVP.
 */

const SESSION_KEY = 'createx_session_id'

function generateSessionId() {
  if (typeof crypto !== 'undefined' && crypto.randomUUID) {
    return 'sess_' + crypto.randomUUID().replace(/-/g, '')
  }
  return 'sess_' + Math.random().toString(36).substring(2, 15) + Date.now().toString(36)
}

export function getSessionId() {
  let sessionId = localStorage.getItem(SESSION_KEY)
  if (!sessionId) {
    sessionId = generateSessionId()
    localStorage.setItem(SESSION_KEY, sessionId)
  }
  return sessionId
}

export function clearSession() {
  localStorage.removeItem(SESSION_KEY)
}

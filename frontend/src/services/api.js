/**
 * API service layer — all fetch calls to the CreateX AI backend.
 * Base URL is configured via VITE_API_BASE_URL environment variable.
 */

import { getSessionId } from './session'
import { getAccessToken, setAccessToken, supabase } from './supabase'

const BASE_URL = (typeof import.meta !== 'undefined' && import.meta.env?.VITE_API_BASE_URL) || (typeof process !== 'undefined' && process.env?.VITE_API_BASE_URL) || 'http://localhost:8000'

async function request(endpoint, options = {}) {
  const url = `${BASE_URL}${endpoint}`
  const headers = { 'Content-Type': 'application/json', ...options.headers }

  // 1. Check for authenticated user access token
  const token = getAccessToken()
  if (token && !headers.Authorization) {
    headers.Authorization = `Bearer ${token}`
  }

  // 2. If unauthenticated, attach X-Session-ID for guest session isolation
  if (!headers.Authorization && !headers['X-Session-ID']) {
    const sessionId = getSessionId()
    if (sessionId) {
      headers['X-Session-ID'] = sessionId
    }
  }

  const config = {
    headers,
    ...options,
  }

  const response = await fetch(url, config)

  if (!response.ok) {
    // 3. Handle expired session safely
    if (response.status === 401 && token) {
      setAccessToken(null)
      if (supabase) {
        supabase.auth.refreshSession().catch(() => {
          supabase.auth.signOut().catch(() => {})
        })
      }
    }

    let errorMessage = `Request failed: ${response.status} ${response.statusText}`
    try {
      const errorData = await response.json()
      errorMessage = errorData.detail || errorMessage
    } catch {}
    throw new Error(errorMessage)
  }

  return response.json()
}

// ─── Health ───────────────────────────────────────────────────────────────────
export const checkHealth = () => request('/api/health')

// ─── Campaign ─────────────────────────────────────────────────────────────────
export const generateCampaign = (payload) =>
  request('/api/campaign/generate', { method: 'POST', body: JSON.stringify(payload) })

// ─── Visual / Poster ──────────────────────────────────────────────────────────
export const generatePoster = (payload) =>
  request('/api/visual/generate', { method: 'POST', body: JSON.stringify(payload) })

// ─── Storyboard ───────────────────────────────────────────────────────────────
export const generateStoryboard = (payload) =>
  request('/api/storyboard/generate', { method: 'POST', body: JSON.stringify(payload) })

// ─── Social Media ─────────────────────────────────────────────────────────────
export const generateSocial = (payload) =>
  request('/api/social/generate', { method: 'POST', body: JSON.stringify(payload) })

// ─── Projects ─────────────────────────────────────────────────────────────────
export const saveProject = (payload) =>
  request('/api/projects/save', { method: 'POST', body: JSON.stringify(payload) })

export const getProjects = (sessionId, limit = 20) =>
  request(`/api/projects?session_id=${encodeURIComponent(sessionId)}&limit=${limit}`)

export const getProject = (projectId) =>
  request(`/api/projects/${projectId}`)

export const saveAsset = (projectId, payload) =>
  request(`/api/projects/${encodeURIComponent(projectId)}/assets`, {
    method: 'POST',
    body: JSON.stringify(payload),
  })

export const getProjectAssets = (projectId) =>
  request(`/api/projects/${encodeURIComponent(projectId)}/assets`)

export const deleteProject = (projectId) =>
  request(`/api/projects/${projectId}`, { method: 'DELETE' })

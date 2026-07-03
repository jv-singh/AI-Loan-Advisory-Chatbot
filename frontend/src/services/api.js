/**
 * api.js — Oryn API client
 * All calls to the FastAPI backend (http://localhost:8000)
 *
 * User identity:
 *   A browser-generated UUID is stored in localStorage under
 *   "oryn_user_id" on first visit. An axios request interceptor
 *   attaches it as the `X-User-Id` header on every request, so
 *   the backend can scope RAG retrieval and document storage
 *   to this visitor.
 */

import axios from 'axios'
import { v4 as uuidv4 } from 'uuid'

const BASE_URL = 'http://localhost:8000'
const USER_ID_KEY = 'oryn_user_id'

// ── User identity ──────────────────────────────────────────────────────────────

/**
 * Returns the persistent UUID for this browser. Creates and stores one
 * the first time it's called. Safe to call from anywhere.
 */
export function getOrCreateUserId() {
  let id = localStorage.getItem(USER_ID_KEY)
  if (!id) {
    id = uuidv4()
    localStorage.setItem(USER_ID_KEY, id)
  }
  return id
}

// ── Client + interceptor ─────────────────────────────────────────────────────

const client = axios.create({
  baseURL: BASE_URL,
  timeout: 180_000, // 3 min — first request warms up models
})

// Attach X-User-Id to every outgoing request so the backend can scope
// retrieval and per-user document storage. Skip the header for /health
// so smoke tests don't carry a stale UUID.
client.interceptors.request.use((config) => {
  const url = config.url || ''
  if (url.includes('/health')) return config
  config.headers = config.headers || {}
  config.headers['X-User-Id'] = getOrCreateUserId()
  return config
})

// ── Chat ──────────────────────────────────────────────────────────────────────

/**
 * POST /api/chat
 * Send a query through the multi-agent pipeline
 */
export async function sendChatMessage({ query, sessionId, applicantId = null }) {
  const { data } = await client.post('/api/chat', {
    query,
    session_id: sessionId,
    applicant_id: applicantId,
  })
  return data
}

// ── Applicants ────────────────────────────────────────────────────────────────

/**
 * GET /api/applicants
 */
export async function fetchApplicants() {
  try {
    const { data } = await client.get('/api/applicants')
    return data.applicants || []
  } catch {
    return []
  }
}

/**
 * GET /api/applicants/:id/summary
 */
export async function fetchApplicantSummary(id) {
  const { data } = await client.get(`/api/applicants/${id}/summary`)
  return data
}

// ── User document library ─────────────────────────────────────────────────────

/**
 * POST /api/documents/upload (multipart)
 * Ingest a file into the caller's user_docs library.
 */
export async function uploadDocument(file, onUploadProgress) {
  const form = new FormData()
  form.append('file', file)
  const { data } = await client.post('/api/documents/upload', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
    onUploadProgress,
  })
  return data
}

/**
 * GET /api/documents/list
 * Fetch this user's uploaded documents.
 */
export async function fetchUserDocuments() {
  const { data } = await client.get('/api/documents/list')
  return data
}

/**
 * DELETE /api/documents/{doc_id}
 * Remove a document from the caller's library. Server verifies ownership.
 */
export async function deleteUserDocument(docId) {
  const { data } = await client.delete(`/api/documents/${docId}`)
  return data
}

// ── Health ────────────────────────────────────────────────────────────────────

/**
 * GET /health
 */
export async function checkHealth() {
  const { data } = await client.get('/health')
  return data
}

export default client

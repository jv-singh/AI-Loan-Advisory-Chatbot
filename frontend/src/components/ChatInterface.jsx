import React, { useState, useRef, useEffect, useCallback } from 'react'
import { v4 as uuidv4 } from 'uuid'
import ReactMarkdown from 'react-markdown'
import {
  sendChatMessage,
  fetchApplicants,
  uploadDocument,
  fetchUserDocuments,
  deleteUserDocument,
  getOrCreateUserId,
} from '../services/api'
import './ChatInterface.css'

const QUICK_PROMPTS = [
  { label: 'Credit Score', text: 'What is the minimum credit score for a home loan?' },
  { label: 'EMI Calc', text: 'Calculate EMI for ₹50 lakh at 8.5% for 20 years' },
  { label: 'Documents', text: 'What documents are required for a personal loan?' },
  { label: 'Eligibility', text: 'Am I eligible for a home loan?' },
  { label: 'Max Amount', text: 'What is the maximum loan amount I can get?' },
  { label: 'DTI Ratio', text: 'Explain the debt-to-income ratio limit' },
]

const ALLOWED_EXTS = ['.pdf', '.docx', '.txt', '.md']

function ConfidenceBadge({ score }) {
  const pct = Math.round(score * 100)
  const cls = score >= 0.7 ? 'badge-high' : score >= 0.45 ? 'badge-medium' : 'badge-low'
  return <span className={`badge ${cls}`}>● {pct}% Confidence</span>
}

/**
 * SourceChips renders the cited sources for an assistant message.
 * `policySources` → global loan_policies pool (📄 icon, default look)
 * `userSources`   → caller's own uploaded docs (📎 icon, accent color)
 *
 * `userSources` is the new shape: list of {filename, doc_id, chunk_excerpt, score}.
 */
function SourceChips({ policySources, userSources }) {
  const policy = policySources || []
  const user = userSources || []
  if (!policy.length && !user.length) return null
  return (
    <div className="source-chips">
      {policy.map((s, i) => (
        <span key={`p-${i}`} className="source-chip source-chip--policy">📄 {s}</span>
      ))}
      {user.map((u, i) => (
        <span
          key={`u-${i}`}
          className="source-chip source-chip--user"
          title={u.chunk_excerpt}
        >
          📎 Your doc: {u.filename}
        </span>
      ))}
    </div>
  )
}

function AgentPipelineDetails({ meta }) {
  const [expanded, setExpanded] = useState(false)
  if (!meta?.query_type) return null

  return (
    <div className="agent-details">
      <button
        className="agent-details__toggle"
        onClick={() => setExpanded(e => !e)}
        aria-expanded={expanded}
        id={`agent-details-${Math.random().toString(36).slice(2)}`}
      >
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/>
        </svg>
        Agent Pipeline
        <span className={`toggle-chevron ${expanded ? 'toggle-chevron--open' : ''}`}>▾</span>
      </button>
      {expanded && (
        <div className="agent-details__content">
          <div className="detail-grid">
            <div className="detail-item">
              <div className="detail-label">Query Type</div>
              <div className="detail-value">{meta.query_type?.replace('_', ' ')}</div>
            </div>
            <div className="detail-item">
              <div className="detail-label">Hallucination Risk</div>
              <div className={`detail-value detail-value--${meta.hallucination_risk}`}>
                {meta.hallucination_risk}
              </div>
            </div>
            <div className="detail-item">
              <div className="detail-label">Fallback</div>
              <div className="detail-value">{meta.fallback_triggered ? 'Yes' : 'No'}</div>
            </div>
          </div>
          {meta.agents_invoked?.length > 0 && (
            <div className="detail-agents">
              <span className="detail-label">Pipeline: </span>
              {meta.agents_invoked.map((a, i) => (
                <React.Fragment key={a}>
                  <span className="agent-chip">{a.replace(/_/g, ' ')}</span>
                  {i < meta.agents_invoked.length - 1 && <span className="agent-arrow">→</span>}
                </React.Fragment>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

function TypingIndicator() {
  return (
    <div className="msg msg--agent">
      <div className="msg__header">
        <div className="agent-avatar">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
            <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/>
          </svg>
        </div>
        <span className="msg__sender">Oryn AI</span>
      </div>
      <div className="typing-indicator">
        <span /><span /><span />
      </div>
    </div>
  )
}

export default function ChatInterface({ applicantId }) {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [sessionId] = useState(() => uuidv4())
  const [userDocs, setUserDocs] = useState([])
  const [docsOpen, setDocsOpen] = useState(false)
  const [uploadStatus, setUploadStatus] = useState(null) // {kind: 'pending'|'ok'|'err', text}
  const [uploading, setUploading] = useState(false)
  const fileInputRef = useRef()
  const bottomRef = useRef()

  // Eagerly create the persistent user_id so it shows up in localStorage
  // on the very first render — makes the isolation test trivial to reason about.
  useEffect(() => {
    getOrCreateUserId()
  }, [])

  const refreshDocs = useCallback(async () => {
    try {
      const data = await fetchUserDocuments()
      setUserDocs(data.user_documents || [])
    } catch (err) {
      // Non-fatal — the panel just shows empty.
      console.warn('fetchUserDocuments failed', err)
    }
  }, [])

  useEffect(() => { refreshDocs() }, [refreshDocs])

  const scrollToBottom = useCallback(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [])

  useEffect(() => { scrollToBottom() }, [messages, loading, scrollToBottom])

  const handleSend = useCallback(async (queryText) => {
    const query = (queryText || input).trim()
    if (!query || loading) return

    setInput('')
    setMessages(prev => [...prev, { role: 'user', content: query }])
    setLoading(true)

    try {
      const data = await sendChatMessage({
        query,
        sessionId,
        applicantId,
      })
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: data.response || 'No response received.',
        // New: split citations. Fall back to legacy `sources` for any
        // path that still emits the combined list.
        policySources: data.policy_sources?.length ? data.policy_sources : (data.sources || []),
        userSources: data.user_sources || [],
        confidence_score: data.confidence_score || 0,
        agent_metadata: data.agent_metadata || null,
      }])
    } catch (err) {
      const isConnErr = err.code === 'ECONNREFUSED' || err.message?.includes('Network')
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: isConnErr
          ? '⚠️ **Cannot connect to backend.** Is the FastAPI server running?\n\nStart it with:\n```\nuvicorn backend.main:app --reload\n```'
          : `⚠️ **Error:** ${err.message}`,
        policySources: [],
        userSources: [],
        confidence_score: 0,
        agent_metadata: null,
      }])
    } finally {
      setLoading(false)
    }
  }, [input, loading, sessionId, applicantId])

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const clearChat = () => {
    setMessages([])
  }

  // ── File upload ──────────────────────────────────────────────────────────
  const triggerFilePicker = () => fileInputRef.current?.click()

  const handleFileSelected = async (e) => {
    const file = e.target.files?.[0]
    // Reset the input so picking the same file twice fires onChange again.
    e.target.value = ''
    if (!file) return

    const ext = '.' + (file.name.split('.').pop() || '').toLowerCase()
    if (!ALLOWED_EXTS.includes(ext)) {
      setUploadStatus({
        kind: 'err',
        text: `Unsupported file type ${ext}. Allowed: ${ALLOWED_EXTS.join(', ')}`,
      })
      return
    }
    if (file.size > 20 * 1024 * 1024) {
      setUploadStatus({ kind: 'err', text: `File too large (${(file.size/1024/1024).toFixed(1)}MB). Max 20MB.` })
      return
    }

    setUploading(true)
    setUploadStatus({ kind: 'pending', text: `Uploading ${file.name}…` })

    try {
      const data = await uploadDocument(file)
      setUploadStatus({
        kind: 'ok',
        text: `✓ Indexed ${data.chunks_indexed ?? data.chunks} chunks from ${data.filename}`,
      })
      await refreshDocs()
    } catch (err) {
      const detail = err.response?.data?.detail || err.message
      setUploadStatus({ kind: 'err', text: `Upload failed: ${detail}` })
    } finally {
      setUploading(false)
      // Auto-clear the toast after a few seconds so it doesn't linger.
      setTimeout(() => setUploadStatus(null), 5000)
    }
  }

  const handleDeleteDoc = async (doc) => {
    const ok = window.confirm(`Delete "${doc.filename}"? The agent will no longer reference it.`)
    if (!ok) return
    try {
      await deleteUserDocument(doc.doc_id)
      await refreshDocs()
    } catch (err) {
      const detail = err.response?.data?.detail || err.message
      setUploadStatus({ kind: 'err', text: `Delete failed: ${detail}` })
      setTimeout(() => setUploadStatus(null), 5000)
    }
  }

  return (
    <div className="chat-interface">
      {/* ── Header ── */}
      <div className="chat-header">
        <div className="chat-header__left">
          <div className="chat-status-dot" />
          <span className="chat-title">Oryn Advisory</span>
          <span className="chat-subtitle">Multi-agent AI Pipeline</span>
        </div>
        <div className="chat-header__right">
          {/* Documents panel toggle */}
          <button
            className="docs-toggle"
            onClick={() => setDocsOpen(o => !o)}
            aria-expanded={docsOpen}
            id="toggle-docs-panel"
            title="View your uploaded documents"
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
              <polyline points="14 2 14 8 20 8"/>
            </svg>
            My documents ({userDocs.length})
          </button>
          <div className="session-tag">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <rect x="3" y="11" width="18" height="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/>
            </svg>
            {sessionId.slice(0, 8)}...
          </div>
          <button className="clear-btn" onClick={clearChat} title="New conversation" id="clear-chat-btn">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <polyline points="1 4 1 10 7 10"/><path d="M3.51 15a9 9 0 1 0 .49-3.5"/>
            </svg>
            New Chat
          </button>
        </div>
      </div>

      {/* ── My documents panel (collapsible) ── */}
      {docsOpen && (
        <div className="docs-panel" id="docs-panel">
          <div className="docs-panel__header">
            <span className="docs-panel__title">My uploaded documents</span>
            <button
              className="docs-panel__close"
              onClick={() => setDocsOpen(false)}
              aria-label="Close"
            >×</button>
          </div>
          {userDocs.length === 0 ? (
            <div className="docs-panel__empty">
              No documents uploaded yet. Click 📎 in the input to add a PDF, DOCX, TXT, or MD file.
            </div>
          ) : (
            <ul className="docs-panel__list">
              {userDocs.map(doc => (
                <li key={doc.doc_id} className="doc-row">
                  <div className="doc-row__main">
                    <div className="doc-row__icon">
                      {doc.file_type === '.pdf' ? '📕' :
                       doc.file_type === '.docx' ? '📘' :
                       doc.file_type === '.md' ? '📝' : '📄'}
                    </div>
                    <div className="doc-row__meta">
                      <div className="doc-row__name" title={doc.filename}>{doc.filename}</div>
                      <div className="doc-row__sub">
                        {doc.chunks} chunks · {new Date(doc.uploaded_at).toLocaleString()}
                      </div>
                    </div>
                  </div>
                  <button
                    className="doc-row__delete"
                    onClick={() => handleDeleteDoc(doc)}
                    title="Delete this document"
                    aria-label={`Delete ${doc.filename}`}
                    id={`delete-doc-${doc.doc_id}`}
                  >
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <polyline points="3 6 5 6 21 6"/>
                      <path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/>
                      <path d="M10 11v6M14 11v6"/>
                    </svg>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}

      {/* ── Quick prompts ── */}
      <div className="quick-prompts">
        {QUICK_PROMPTS.map(p => (
          <button
            key={p.label}
            className="quick-prompt"
            onClick={() => handleSend(p.text)}
            disabled={loading}
            id={`quick-prompt-${p.label.toLowerCase().replace(/\s/g,'-')}`}
          >
            {p.label}
          </button>
        ))}
      </div>

      {/* ── Messages ── */}
      <div className="chat-messages" role="log" aria-live="polite">
        {messages.length === 0 && (
          <div className="chat-empty">
            <div className="empty-icon">
              <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
              </svg>
            </div>
            <h3>Ask Oryn anything about loans</h3>
            <p>Eligibility checks, EMI calculations, document requirements, policy questions — I handle it all.</p>
            <p className="chat-empty__hint">
              Tip: click 📎 below to upload your own sanction letter, payslip, or bank T&amp;C and ask questions about it.
            </p>
          </div>
        )}

        {messages.map((msg, i) => (
          <div key={i} className={`msg msg--${msg.role}`}>
            {msg.role === 'user' ? (
              <>
                <div className="msg__header">
                  <span className="msg__sender">You</span>
                </div>
                <div className="msg__body msg__body--user">{msg.content}</div>
              </>
            ) : (
              <>
                <div className="msg__header">
                  <div className="agent-avatar">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
                      <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/>
                    </svg>
                  </div>
                  <span className="msg__sender">Oryn AI</span>
                  {msg.confidence_score > 0 && (
                    <ConfidenceBadge score={msg.confidence_score} />
                  )}
                </div>
                <div className="msg__body msg__body--agent">
                  <ReactMarkdown>{msg.content}</ReactMarkdown>
                </div>
                <SourceChips
                  policySources={msg.policySources}
                  userSources={msg.userSources}
                />
                <AgentPipelineDetails meta={msg.agent_metadata} />
              </>
            )}
          </div>
        ))}

        {loading && <TypingIndicator />}
        <div ref={bottomRef} />
      </div>

      {/* ── Upload status line ── */}
      {uploadStatus && (
        <div
          className={`upload-status upload-status--${uploadStatus.kind}`}
          role="status"
          id="upload-status"
        >
          {uploadStatus.kind === 'pending' && <span className="upload-spinner" />}
          {uploadStatus.text}
        </div>
      )}

      {/* ── Input ── */}
      <div className="chat-input-wrap">
        <div className="chat-input-row">
          <textarea
            className="chat-input"
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask about loan eligibility, EMI, documents... (Enter to send)"
            rows={1}
            disabled={loading}
            id="chat-input-field"
          />
          <button
            className="upload-btn"
            onClick={triggerFilePicker}
            disabled={loading || uploading}
            aria-label="Upload document"
            title="Upload a PDF, DOCX, TXT, or MD file"
            id="upload-doc-btn"
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48"/>
            </svg>
          </button>
          <input
            ref={fileInputRef}
            type="file"
            accept={ALLOWED_EXTS.join(',')}
            onChange={handleFileSelected}
            style={{ display: 'none' }}
            aria-hidden="true"
          />
          <button
            className={`send-btn ${loading ? 'send-btn--loading' : ''}`}
            onClick={() => handleSend()}
            disabled={loading || !input.trim()}
            aria-label="Send message"
            id="send-message-btn"
          >
            {loading ? (
              <div className="send-spinner" />
            ) : (
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                <line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/>
              </svg>
            )}
          </button>
        </div>
        <div className="chat-input-hint">
          <span>Shift+Enter for new line</span>
          <span>·</span>
          <span>Session: {sessionId.slice(0, 8)}</span>
        </div>
      </div>
    </div>
  )
}

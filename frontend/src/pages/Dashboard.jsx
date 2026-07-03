import React, { useState, useEffect } from 'react'
import ChatInterface from '../components/ChatInterface'
import { fetchApplicants } from '../services/api'
import './Dashboard.css'

const METRICS = [
  { label: 'Loan Types Supported', value: '12+', icon: '🏠', color: 'blue' },
  { label: 'Agent Pipeline Steps', value: '6', icon: '⚡', color: 'gold' },
  { label: 'Response Accuracy', value: '99%', icon: '🎯', color: 'green' },
  { label: 'Avg Response Time', value: '<3s', icon: '⏱', color: 'cyan' },
]

export default function Dashboard() {
  const [applicants, setApplicants] = useState([])
  const [selectedApplicant, setSelectedApplicant] = useState(null)
  const [backendStatus, setBackendStatus] = useState('checking')

  useEffect(() => {
    fetchApplicants()
      .then(data => {
        setApplicants(data)
        setBackendStatus(data.length > 0 ? 'online' : 'partial')
      })
      .catch(() => setBackendStatus('offline'))
  }, [])

  const selectedApplicantData = applicants.find(a => a.id === selectedApplicant)

  return (
    <div className="dashboard">
      {/* ── Page header ── */}
      <div className="dashboard-header">
        <div className="container">
          <div className="dash-header-inner">
            <div>
              <div className="section-label">Dashboard</div>
              <h1 className="section-title">
                Your Loan Advisory <span className="gradient-text">Command Center</span>
              </h1>
              <p className="section-subtitle">
                Ask Oryn anything about loans, EMI calculations, eligibility checks, and financial guidance.
              </p>
            </div>
            <div className={`backend-status backend-status--${backendStatus}`}>
              <span className="status-dot" />
              <span className="status-label">
                {backendStatus === 'online' ? 'Backend Online'
                  : backendStatus === 'partial' ? 'Partial Connection'
                  : backendStatus === 'offline' ? 'Backend Offline'
                  : 'Connecting...'}
              </span>
            </div>
          </div>

          {/* Metrics strip */}
          <div className="metrics-strip">
            {METRICS.map(m => (
              <div key={m.label} className={`metric-card metric-card--${m.color}`}>
                <span className="metric-icon">{m.icon}</span>
                <span className="metric-value">{m.value}</span>
                <span className="metric-label">{m.label}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* ── Main grid ── */}
      <div className="container">
        <div className="dashboard-grid">
          {/* Sidebar */}
          <aside className="dashboard-sidebar">
            {/* Applicant selector */}
            <div className="sidebar-card">
              <div className="sidebar-card__header">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/>
                  <circle cx="12" cy="7" r="4"/>
                </svg>
                <span>Applicant Context</span>
              </div>
              <p className="sidebar-card__desc">
                Optional — link a profile for eligibility & fraud analysis
              </p>
              <select
                className="applicant-select"
                value={selectedApplicant || ''}
                onChange={e => setSelectedApplicant(e.target.value || null)}
                id="applicant-selector"
              >
                <option value="">— No applicant (policy query) —</option>
                {applicants.map(a => (
                  <option key={a.id} value={a.id}>
                    {a.full_name} ({a.city})
                  </option>
                ))}
              </select>

              {selectedApplicantData && (
                <div className="applicant-profile">
                  <div className="profile-row">
                    <span className="profile-label">Monthly Income</span>
                    <span className="profile-value">
                      ₹{selectedApplicantData.monthly_income?.toLocaleString('en-IN')}
                    </span>
                  </div>
                  <div className="profile-row">
                    <span className="profile-label">Employment</span>
                    <span className="profile-value">
                      {selectedApplicantData.employment_type?.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())}
                    </span>
                  </div>
                  <div className="profile-row">
                    <span className="profile-label">City</span>
                    <span className="profile-value">{selectedApplicantData.city}</span>
                  </div>
                </div>
              )}
            </div>

            {/* Info card */}
            <div className="sidebar-card sidebar-card--info">
              <div className="sidebar-card__header">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <circle cx="12" cy="12" r="10"/>
                  <line x1="12" y1="8" x2="12" y2="12"/>
                  <line x1="12" y1="16" x2="12.01" y2="16"/>
                </svg>
                <span>How It Works</span>
              </div>
              <div className="pipeline-steps">
                {[
                  { step: '01', label: 'Query Classification', desc: 'Intent + entity extraction' },
                  { step: '02', label: 'RAG Retrieval', desc: 'Policy document search' },
                  { step: '03', label: 'Specialist Agents', desc: 'Credit / EMI / Fraud' },
                  { step: '04', label: 'Response Synthesis', desc: 'Grounded answer + citations' },
                ].map(s => (
                  <div key={s.step} className="pipeline-step">
                    <span className="step-num">{s.step}</span>
                    <div>
                      <div className="step-label">{s.label}</div>
                      <div className="step-desc">{s.desc}</div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </aside>

          {/* Chat */}
          <div className="chat-container">
            <ChatInterface applicantId={selectedApplicant} />
          </div>
        </div>
      </div>
    </div>
  )
}

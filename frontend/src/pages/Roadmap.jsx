import React from 'react'
import './InfoPage.css'

const ROADMAP = [
  {
    phase: 'Phase 1',
    label: 'Current',
    status: 'done',
    quarter: 'Q4 2024',
    items: [
      { title: 'Multi-agent LangGraph architecture', done: true },
      { title: 'RAG over loan policy documents', done: true },
      { title: 'EMI calculation engine', done: true },
      { title: 'Fraud detection agent', done: true },
      { title: 'FastAPI backend + Supabase integration', done: true },
      { title: 'React + Three.js frontend', done: true },
      { title: 'Confidence scoring & source citations', done: true },
    ],
  },
  {
    phase: 'Phase 2',
    label: 'In Progress',
    status: 'active',
    quarter: 'Q1 2025',
    items: [
      { title: 'Streaming SSE responses (real-time text)', done: false },
      { title: 'Real bank rate API integration', done: false },
      { title: 'Applicant self-onboarding flow', done: false },
      { title: 'Multi-bank comparison engine', done: false },
      { title: 'Export chat as PDF report', done: false },
      { title: 'Session persistence (cross-device)', done: false },
    ],
  },
  {
    phase: 'Phase 3',
    label: 'Planned',
    status: 'planned',
    quarter: 'Q2 2025',
    items: [
      { title: 'Hindi & regional language support', done: false },
      { title: 'Voice input / speech-to-text', done: false },
      { title: 'Bank branch locator integration', done: false },
      { title: 'Loan application pre-fill assistant', done: false },
      { title: 'Credit score improvement advisor', done: false },
      { title: 'WhatsApp / Telegram bot interface', done: false },
    ],
  },
  {
    phase: 'Phase 4',
    label: 'Vision',
    status: 'vision',
    quarter: 'H2 2025',
    items: [
      { title: 'Direct bank API integration for pre-approval', done: false },
      { title: 'Insurance advisory add-on', done: false },
      { title: 'Investment portfolio correlation analysis', done: false },
      { title: 'AI-powered loan restructuring advisor', done: false },
      { title: 'Enterprise white-label SaaS version', done: false },
      { title: 'Regulatory compliance audit assistant', done: false },
    ],
  },
]

const STATUS_CONFIG = {
  done: { label: 'Completed', color: '#34d399', bg: 'rgba(16, 185, 129, 0.1)', border: 'rgba(16, 185, 129, 0.3)' },
  active: { label: 'In Progress', color: '#3b82f6', bg: 'rgba(37, 99, 235, 0.1)', border: 'rgba(37, 99, 235, 0.3)' },
  planned: { label: 'Planned', color: '#fbbf24', bg: 'rgba(245, 158, 11, 0.1)', border: 'rgba(245, 158, 11, 0.3)' },
  vision: { label: 'Vision', color: '#c084fc', bg: 'rgba(168, 85, 247, 0.1)', border: 'rgba(168, 85, 247, 0.3)' },
}

const UPCOMING_HIGHLIGHTS = [
  {
    icon: '🚀',
    title: 'Streaming Responses',
    desc: 'Real-time text streaming using Server-Sent Events so you see Oryn\'s reasoning as it generates.',
    eta: 'Q1 2025',
  },
  {
    icon: '🌍',
    title: 'Multilingual Support',
    desc: 'Full Hindi interface and support for 8 additional Indian regional languages.',
    eta: 'Q2 2025',
  },
  {
    icon: '🏦',
    title: 'Live Bank Rates',
    desc: 'Real-time interest rate feeds from top Indian banks — always accurate, never stale.',
    eta: 'Q1 2025',
  },
  {
    icon: '🎤',
    title: 'Voice Advisory',
    desc: 'Speak your loan questions and hear Oryn\'s answers — hands-free financial guidance.',
    eta: 'Q2 2025',
  },
]

export default function Roadmap() {
  return (
    <div className="info-page">
      <div className="info-hero">
        <div className="container">
          <div className="section-label">Future</div>
          <h1 className="section-title">
            What's <span className="gradient-text">Coming Next</span>
          </h1>
          <p className="section-subtitle">
            Oryn is actively evolving. Here's a transparent view of what's been built, what's in progress, and where we're heading — with no vague promises.
          </p>
        </div>
      </div>

      <div className="container">
        {/* Upcoming highlights */}
        <section className="page-section">
          <div className="section-label">Highlights</div>
          <h2 className="section-title">Coming Soon</h2>
          <div className="upcoming-grid">
            {UPCOMING_HIGHLIGHTS.map(u => (
              <div key={u.title} className="upcoming-card">
                <div className="upcoming-icon">{u.icon}</div>
                <div className="upcoming-eta">{u.eta}</div>
                <h3 className="upcoming-title">{u.title}</h3>
                <p className="upcoming-desc">{u.desc}</p>
              </div>
            ))}
          </div>
        </section>

        {/* Full roadmap timeline */}
        <section className="page-section">
          <div className="section-label">Roadmap</div>
          <h2 className="section-title">Full Development Timeline</h2>
          <div className="roadmap-timeline">
            {ROADMAP.map(phase => {
              const cfg = STATUS_CONFIG[phase.status]
              return (
                <div key={phase.phase} className={`roadmap-phase roadmap-phase--${phase.status}`}>
                  <div className="phase-header">
                    <div className="phase-left">
                      <span className="phase-number">{phase.phase}</span>
                      <div>
                        <span className="phase-quarter">{phase.quarter}</span>
                        <div className="phase-status" style={{ background: cfg.bg, color: cfg.color, border: `1px solid ${cfg.border}` }}>
                          {cfg.label}
                        </div>
                      </div>
                    </div>
                  </div>
                  <ul className="phase-items">
                    {phase.items.map(item => (
                      <li key={item.title} className={`phase-item ${item.done ? 'phase-item--done' : ''}`}>
                        <span className="phase-item__check">
                          {item.done ? (
                            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><polyline points="20 6 9 17 4 12"/></svg>
                          ) : (
                            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="9"/></svg>
                          )}
                        </span>
                        {item.title}
                      </li>
                    ))}
                  </ul>
                </div>
              )
            })}
          </div>
        </section>
      </div>
    </div>
  )
}

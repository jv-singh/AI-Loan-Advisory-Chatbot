import React from 'react'
import './InfoPage.css'

const LIMITATIONS = [
  {
    icon: '🔮',
    title: 'Not Real-Time Data',
    severity: 'high',
    desc: 'Oryn\'s knowledge is based on pre-ingested policy documents. Interest rates, bank policies, and eligibility criteria change frequently. Always verify current rates and terms directly with your bank before making financial decisions.',
    workaround: 'Use Oryn for understanding loan concepts and rough estimates. Cross-check all rates with official bank sources.',
  },
  {
    icon: '📜',
    title: 'Synthetic Applicant Data',
    severity: 'high',
    desc: 'All applicant profiles in this prototype are synthetically generated for demonstration purposes. No real personal financial data is used or stored. Eligibility assessments on these profiles are illustrative only.',
    workaround: 'This is a technical prototype. In a production system, real applicant data with proper consent and security would be used.',
  },
  {
    icon: '⚖️',
    title: 'Not Financial Advice',
    severity: 'critical',
    desc: 'Oryn is an educational and informational tool — it is not a licensed financial advisor. Responses should not be interpreted as professional financial advice, legal guidance, or official loan pre-approval.',
    workaround: 'Consult a licensed financial advisor, chartered accountant, or bank relationship manager before making any loan application decisions.',
  },
  {
    icon: '🌐',
    title: 'India-Specific Policies',
    severity: 'medium',
    desc: 'Oryn\'s policy documents are currently scoped to Indian banking regulations and loan products. It has limited knowledge of international loan products, foreign currency loans, or non-Indian banking systems.',
    workaround: 'For international loan queries, use country-specific resources. Oryn will indicate when a question is outside its knowledge domain.',
  },
  {
    icon: '🔢',
    title: 'EMI Calculations Are Estimates',
    severity: 'medium',
    desc: 'EMI calculations use standard actuarial formulas (reducing balance method). Actual EMIs from banks may vary based on processing fees, GST, prepayment clauses, floating rate adjustments, and bank-specific calculation methods.',
    workaround: 'Use Oryn\'s EMI calculations for budgeting and planning. Get final EMI confirmation from your bank\'s official loan calculator or relationship manager.',
  },
  {
    icon: '🤖',
    title: 'AI Hallucination Risk',
    severity: 'medium',
    desc: 'Despite RAG grounding and multi-agent verification, there remains a residual risk of AI-generated inaccuracies. Oryn\'s confidence scores and hallucination risk indicators help quantify but cannot eliminate this risk entirely.',
    workaround: 'Pay attention to confidence badges. Low confidence (red) responses have higher uncertainty. Always verify important policy details with primary sources.',
  },
  {
    icon: '💬',
    title: 'No Streaming Responses',
    severity: 'low',
    desc: 'The current implementation uses synchronous response delivery — you wait for the full agent pipeline to complete before seeing the answer. For complex queries, this can take 10-30 seconds on first use (model warmup).',
    workaround: 'This is a known technical limitation being addressed in the roadmap. Streaming SSE responses will reduce perceived latency significantly.',
  },
  {
    icon: '📱',
    title: 'Limited Mobile Optimization',
    severity: 'low',
    desc: 'While the interface is responsive, the chat experience is optimized for desktop and tablet. Some complex table-formatted responses may render suboptimally on small mobile screens.',
    workaround: 'For the best experience, use Oryn on a desktop or tablet browser. Mobile support is on the roadmap.',
  },
]

const SEVERITY_CONFIG = {
  critical: { label: 'Critical', color: '#f87171', bg: 'rgba(239, 68, 68, 0.1)', border: 'rgba(239, 68, 68, 0.3)' },
  high: { label: 'Important', color: '#fb923c', bg: 'rgba(249, 115, 22, 0.1)', border: 'rgba(249, 115, 22, 0.3)' },
  medium: { label: 'Moderate', color: '#fbbf24', bg: 'rgba(245, 158, 11, 0.1)', border: 'rgba(245, 158, 11, 0.3)' },
  low: { label: 'Minor', color: '#34d399', bg: 'rgba(16, 185, 129, 0.1)', border: 'rgba(16, 185, 129, 0.3)' },
}

export default function Limitations() {
  return (
    <div className="info-page">
      <div className="info-hero">
        <div className="container">
          <div className="section-label">Transparency</div>
          <h1 className="section-title">
            Known <span className="gradient-text">Limitations</span>
          </h1>
          <p className="section-subtitle">
            Oryn is built on a principle of radical transparency. Here's an honest breakdown of what Oryn cannot do, the risks involved, and how to work around them.
          </p>
        </div>
      </div>

      <div className="container">
        {/* Critical disclaimer */}
        <div className="critical-notice">
          <div className="critical-notice__icon">⚠️</div>
          <div>
            <div className="critical-notice__title">Important Disclaimer</div>
            <p className="critical-notice__text">
              Oryn is a <strong>prototype</strong> using synthetic data and pre-trained AI models. It is designed for demonstration and educational purposes only. <strong>Do not make real financial decisions based on Oryn's responses.</strong> Always consult licensed financial professionals and verify all information with official bank sources.
            </p>
          </div>
        </div>

        {/* Limitations grid */}
        <section className="page-section">
          <div className="limitations-grid">
            {LIMITATIONS.map(lim => {
              const cfg = SEVERITY_CONFIG[lim.severity]
              return (
                <div key={lim.title} className="limitation-card" style={{ '--sev-color': cfg.color, '--sev-bg': cfg.bg, '--sev-border': cfg.border }}>
                  <div className="limitation-header">
                    <span className="limitation-icon">{lim.icon}</span>
                    <div>
                      <h3 className="limitation-title">{lim.title}</h3>
                      <span className="severity-badge" style={{ background: cfg.bg, color: cfg.color, border: `1px solid ${cfg.border}` }}>
                        {cfg.label}
                      </span>
                    </div>
                  </div>
                  <p className="limitation-desc">{lim.desc}</p>
                  <div className="limitation-workaround">
                    <div className="workaround-label">
                      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/></svg>
                      Workaround
                    </div>
                    <p>{lim.workaround}</p>
                  </div>
                </div>
              )
            })}
          </div>
        </section>
      </div>
    </div>
  )
}

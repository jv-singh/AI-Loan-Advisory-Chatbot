import React from 'react'
import './InfoPage.css'

const FEATURES = [
  {
    icon: '🏠',
    title: 'Loan Eligibility Assessment',
    desc: 'Oryn evaluates your complete financial profile — income, credit score, employment type, and existing liabilities — against multi-bank loan policies to give you an accurate eligibility verdict.',
    details: ['Multi-bank policy comparison', 'Credit score analysis', 'Employment type validation', 'Debt-to-income ratio check'],
    color: 'blue',
  },
  {
    icon: '🧮',
    title: 'EMI Calculator & Projections',
    desc: 'Get precise EMI calculations using actuarial formulas. Compare different loan amounts, tenures, and interest rates to find the payment structure that works for your budget.',
    details: ['Monthly EMI calculation', 'Total interest outflow', 'Amortization breakdown', 'Multi-scenario comparison'],
    color: 'gold',
  },
  {
    icon: '📋',
    title: 'Document Guidance',
    desc: 'Know exactly which documents you need for any loan application. Oryn provides comprehensive, bank-specific document checklists based on your employment type and loan category.',
    details: ['Employment-based document lists', 'Bank-specific requirements', 'KYC document guidance', 'Income proof requirements'],
    color: 'green',
  },
  {
    icon: '🛡️',
    title: 'Fraud Risk Detection',
    desc: 'Oryn\'s fraud agent cross-references applicant profiles against behavioral red flags and anomaly patterns, flagging high-risk applications before they reach underwriting.',
    details: ['Income anomaly detection', 'Employment inconsistency flags', 'Credit history analysis', 'Risk scoring engine'],
    color: 'red',
  },
  {
    icon: '📚',
    title: 'Policy Q&A (RAG)',
    desc: 'Powered by Retrieval-Augmented Generation, Oryn answers policy questions by searching through actual loan policy documents — not hallucinated knowledge. Every answer is grounded and cited.',
    details: ['Semantic document search', 'Citation-backed answers', 'Confidence scoring', 'Multi-document synthesis'],
    color: 'cyan',
  },
  {
    icon: '💬',
    title: 'Conversational Context',
    desc: 'Unlike simple chatbots, Oryn maintains full conversation memory within a session. Ask follow-ups, refine your question, and explore scenarios — Oryn remembers everything you\'ve discussed.',
    details: ['Session-level memory', 'Context-aware follow-ups', 'Multi-turn dialogue', 'Entity tracking across turns'],
    color: 'purple',
  },
]

const TECH_STACK = [
  { name: 'LangGraph', desc: 'Multi-agent orchestration with stateful pipelines', badge: 'Core' },
  { name: 'FastAPI', desc: 'High-performance async REST API backend', badge: 'Backend' },
  { name: 'ChromaDB', desc: 'Vector database for semantic document retrieval', badge: 'RAG' },
  { name: 'Groq LLM', desc: 'Ultra-fast Llama inference (8B instant)', badge: 'AI' },
  { name: 'Sentence Transformers', desc: 'Local embedding model (all-MiniLM-L6-v2)', badge: 'Embeddings' },
  { name: 'Supabase', desc: 'Postgres + applicant data management', badge: 'Database' },
]

export default function Features() {
  return (
    <div className="info-page">
      <div className="info-hero">
        <div className="container">
          <div className="section-label">Capabilities</div>
          <h1 className="section-title">
            What <span className="gradient-text">Oryn</span> Can Do
          </h1>
          <p className="section-subtitle">
            A comprehensive breakdown of Oryn's AI-powered loan advisory capabilities, built on a multi-agent architecture designed for accuracy and transparency.
          </p>
        </div>
      </div>

      <div className="container">
        {/* Features grid */}
        <section className="page-section">
          <div className="features-grid">
            {FEATURES.map(f => (
              <div key={f.title} className={`feature-card feature-card--${f.color}`}>
                <div className="feature-card__icon">{f.icon}</div>
                <h3 className="feature-card__title">{f.title}</h3>
                <p className="feature-card__desc">{f.desc}</p>
                <ul className="feature-details">
                  {f.details.map(d => (
                    <li key={d}>
                      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><polyline points="20 6 9 17 4 12"/></svg>
                      {d}
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </section>

        {/* Tech stack */}
        <section className="page-section tech-section">
          <div className="section-label">Tech Stack</div>
          <h2 className="section-title">Built With</h2>
          <p className="section-subtitle">The technology powering Oryn's intelligence.</p>
          <div className="tech-grid">
            {TECH_STACK.map(t => (
              <div key={t.name} className="tech-card">
                <div className="tech-card__top">
                  <span className="tech-name">{t.name}</span>
                  <span className="tech-badge">{t.badge}</span>
                </div>
                <p className="tech-desc">{t.desc}</p>
              </div>
            ))}
          </div>
        </section>
      </div>
    </div>
  )
}

import React from 'react'
import './InfoPage.css'

const STEPS = [
  {
    number: '01',
    title: 'Start a Conversation',
    desc: 'Open the Dashboard and type your loan-related question in the chat input. You can ask about anything from eligibility criteria to EMI calculations — no specific format required.',
    tip: 'Be specific: include loan amounts, tenure, and your income for the best results.',
    icon: '💬',
  },
  {
    number: '02',
    title: 'Optional: Select an Applicant',
    desc: 'For personalized eligibility checks and fraud risk analysis, select a saved applicant profile from the sidebar dropdown. This gives Oryn your financial context for tailored responses.',
    tip: 'Without an applicant, Oryn answers general policy questions. With one, it gives personalized assessments.',
    icon: '👤',
  },
  {
    number: '03',
    title: 'Ask Your Question',
    desc: 'Type your query and press Enter (or click the send button). Oryn\'s multi-agent pipeline processes your request through classification, RAG retrieval, and specialist agents in real time.',
    tip: 'Use the quick-prompt chips at the top of the chat for common questions.',
    icon: '⚡',
  },
  {
    number: '04',
    title: 'Review the Response',
    desc: 'Oryn returns a grounded, citation-backed answer with a confidence badge. Expand the Agent Pipeline Details to see which agents were invoked and the hallucination risk assessment.',
    tip: 'Higher confidence badges (green ≥ 70%) mean the answer is strongly supported by policy documents.',
    icon: '📊',
  },
  {
    number: '05',
    title: 'Continue the Conversation',
    desc: 'Oryn maintains conversation context across messages within a session. You can ask follow-up questions without re-providing context. Start a "New Chat" to reset the session.',
    tip: 'Session ID is shown in the top-right of the chat panel. Each browser session gets a unique ID.',
    icon: '🔄',
  },
]

const EXAMPLES = [
  { category: 'Eligibility', queries: ['Am I eligible for a home loan?', 'What credit score do I need for a personal loan?', 'Can a self-employed person get a home loan?'] },
  { category: 'EMI & Finance', queries: ['Calculate EMI for ₹30L at 8.5% for 20 years', 'What is the maximum loan amount based on my income?', 'How does debt-to-income ratio affect eligibility?'] },
  { category: 'Documents', queries: ['What documents do I need for a home loan?', 'Is a PAN card mandatory for a personal loan?', 'What income proof is required for a business loan?'] },
  { category: 'Policy & Rules', queries: ['What is the maximum LTV ratio for a home loan?', 'What is the processing fee for personal loans?', 'Can NRIs apply for home loans in India?'] },
]

export default function HowToUse() {
  return (
    <div className="info-page">
      {/* Hero */}
      <div className="info-hero">
        <div className="container">
          <div className="section-label">Guide</div>
          <h1 className="section-title">
            How to Use <span className="gradient-text">Oryn</span>
          </h1>
          <p className="section-subtitle">
            Get started with Oryn's AI-powered loan advisory in under a minute. Follow this simple guide to make the most of every conversation.
          </p>
        </div>
      </div>

      <div className="container">
        {/* Steps */}
        <section className="page-section">
          <div className="steps-list">
            {STEPS.map((step, i) => (
              <div key={step.number} className="step-card">
                <div className="step-card__number">{step.number}</div>
                <div className="step-card__icon">{step.icon}</div>
                <div className="step-card__body">
                  <h3 className="step-card__title">{step.title}</h3>
                  <p className="step-card__desc">{step.desc}</p>
                  <div className="step-tip">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/>
                    </svg>
                    {step.tip}
                  </div>
                </div>
                {i < STEPS.length - 1 && <div className="step-connector" />}
              </div>
            ))}
          </div>
        </section>

        {/* Example queries */}
        <section className="page-section">
          <div className="section-label">Examples</div>
          <h2 className="section-title">Questions You Can Ask</h2>
          <p className="section-subtitle">Try any of these example queries to explore Oryn's capabilities.</p>

          <div className="examples-grid">
            {EXAMPLES.map(cat => (
              <div key={cat.category} className="feature-card">
                <div className="example-category">{cat.category}</div>
                <ul className="example-list">
                  {cat.queries.map(q => (
                    <li key={q} className="example-query">
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                        <polyline points="9 18 15 12 9 6"/>
                      </svg>
                      {q}
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </section>
      </div>
    </div>
  )
}

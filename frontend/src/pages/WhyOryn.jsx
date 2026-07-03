import React from 'react'
import './InfoPage.css'

const STORY_SECTIONS = [
  {
    phase: 'The Problem',
    title: 'Loan Advisory Is Broken',
    icon: '🔍',
    content: `Millions of people apply for loans every year in India with almost zero knowledge of what they qualify for, what documents they need, or how interest rates actually work. The information exists — in dense policy documents, bank websites, and financial advisory pamphlets — but it's fragmented, technical, and inaccessible.

Traditional financial advisors are expensive, often biased toward specific banks, and unavailable at 2am when you're doing your financial planning. Static EMI calculators tell you your monthly payment but not whether you'll actually get approved. Bank websites bury eligibility criteria under 10 layers of marketing copy.`,
  },
  {
    phase: 'The Vision',
    title: 'AI That Levels the Playing Field',
    icon: '💡',
    content: `Oryn was built on a simple belief: everyone deserves access to expert-level financial guidance — not just those who can afford a financial advisor. By combining large language models with retrieval-augmented generation over actual loan policy documents, we built an AI that doesn't just know general finance — it knows specific policies, current rates, and real eligibility rules.

The name "Oryn" represents a north star — reliable guidance in a complex financial landscape. Like a financial compass, Oryn points you in the right direction without making decisions for you.`,
  },
  {
    phase: 'The Architecture',
    title: 'Why Multi-Agent?',
    icon: '⚡',
    content: `A single LLM answering loan questions would inevitably hallucinate — fabricating rates, inventing policies, and giving false confidence. Oryn uses a multi-agent LangGraph architecture where specialized agents handle distinct tasks: query classification, document retrieval, credit analysis, employment verification, EMI calculation, and fraud detection.

Each agent has a specific scope and cannot invent information outside its domain. The orchestrator synthesizes their outputs into a coherent, grounded response. Every answer carries a confidence score and source citations — making it verifiably trustworthy, not just confidently wrong.`,
  },
  {
    phase: 'The Mission',
    title: 'What We\'re Building Toward',
    icon: '🎯',
    content: `Oryn is a proof-of-concept for what AI-powered financial advisory can look like: transparent, grounded, honest about its limitations, and genuinely useful. We're not trying to replace financial advisors — we're trying to make everyone informed enough to have a real conversation with one.

This prototype demonstrates the technical foundation. The roadmap includes real-time bank rate integration, multilingual support, and direct loan application assistance. The goal is simple: make navigating the loan system as easy as having a knowledgeable friend.`,
  },
]

const PRINCIPLES = [
  { icon: '🔬', label: 'Grounded Truth', desc: 'Every answer backed by source documents' },
  { icon: '🪟', label: 'Transparency', desc: 'Confidence scores and agent pipeline visibility' },
  { icon: '⚖️', label: 'No Bias', desc: 'Policy-based answers, not sales recommendations' },
  { icon: '🛡️', label: 'Honest Limits', desc: 'Clear disclosure of what Oryn cannot do' },
]

export default function WhyOryn() {
  return (
    <div className="info-page">
      <div className="info-hero">
        <div className="container">
          <div className="section-label">Origin Story</div>
          <h1 className="section-title">
            Why <span className="gradient-text">Oryn</span> Was Made
          </h1>
          <p className="section-subtitle">
            The story behind building an AI financial advisor — the problem it solves, the philosophy that guides it, and the mission it's working toward.
          </p>
        </div>
      </div>

      <div className="container">
        {/* Story sections */}
        <section className="page-section">
          <div className="story-timeline">
            {STORY_SECTIONS.map((s, i) => (
              <div key={s.phase} className={`story-entry ${i % 2 === 0 ? 'story-entry--left' : 'story-entry--right'}`}>
                <div className="story-phase-tag">{s.phase}</div>
                <div className="story-card">
                  <div className="story-card__icon">{s.icon}</div>
                  <h3 className="story-card__title">{s.title}</h3>
                  {s.content.split('\n\n').map((para, j) => (
                    <p key={j} className="story-card__para">{para}</p>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* Core principles */}
        <section className="page-section">
          <div className="section-label">Principles</div>
          <h2 className="section-title">Built on These Values</h2>
          <div className="principles-grid">
            {PRINCIPLES.map(p => (
              <div key={p.label} className="principle-card">
                <div className="principle-icon">{p.icon}</div>
                <div className="principle-label">{p.label}</div>
                <div className="principle-desc">{p.desc}</div>
              </div>
            ))}
          </div>
        </section>
      </div>
    </div>
  )
}

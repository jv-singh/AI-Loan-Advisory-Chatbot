import React, { useState, useEffect } from 'react'
import { NavLink, useLocation } from 'react-router-dom'
import './Layout.css'

const navItems = [
  { path: '/', label: 'Dashboard', icon: '⬡' },
  { path: '/how-to-use', label: 'How to Use', icon: '◈' },
  { path: '/features', label: 'Features', icon: '◇' },
  { path: '/why-oryn', label: 'Why Oryn', icon: '◆' },
  { path: '/limitations', label: 'Limitations', icon: '◉' },
  { path: '/roadmap', label: 'Roadmap', icon: '◎' },
]

export default function Layout({ children }) {
  const [scrolled, setScrolled] = useState(false)
  const [menuOpen, setMenuOpen] = useState(false)
  const location = useLocation()

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 20)
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => window.removeEventListener('scroll', onScroll)
  }, [])

  useEffect(() => {
    setMenuOpen(false)
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }, [location.pathname])

  return (
    <div className="app-layout">
      {/* ── Navigation ── */}
      <nav className={`navbar ${scrolled ? 'navbar--scrolled' : ''}`} role="navigation">
        <div className="navbar-inner container">
          {/* Logo */}
          <NavLink to="/" className="navbar-logo">
            <div className="logo-icon">
              <svg width="28" height="28" viewBox="0 0 32 32" fill="none">
                <defs>
                  <linearGradient id="logoGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                    <stop offset="0%" stopColor="#3b82f6" />
                    <stop offset="100%" stopColor="#06b6d4" />
                  </linearGradient>
                </defs>
                <circle cx="16" cy="16" r="14" stroke="url(#logoGrad)" strokeWidth="2" fill="rgba(37,99,235,0.1)" />
                <path d="M10 16 L14 10 L18 16 L22 10" stroke="url(#logoGrad)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                <path d="M10 22 L16 16 L22 22" stroke="#f59e0b" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            </div>
            <span className="logo-text">Oryn</span>
            <span className="logo-tag">AI</span>
          </NavLink>

          {/* Desktop nav */}
          <ul className="navbar-links" role="menubar">
            {navItems.map(item => (
              <li key={item.path} role="none">
                <NavLink
                  to={item.path}
                  className={({ isActive }) => `nav-link ${isActive ? 'nav-link--active' : ''}`}
                  role="menuitem"
                  end={item.path === '/'}
                >
                  {item.label}
                </NavLink>
              </li>
            ))}
          </ul>

          {/* Right CTA */}
          <div className="navbar-right">
            <a
              href="http://localhost:8000/docs"
              target="_blank"
              rel="noopener noreferrer"
              className="nav-api-btn"
            >
              API Docs
            </a>
          </div>

          {/* Mobile hamburger */}
          <button
            className={`hamburger ${menuOpen ? 'hamburger--open' : ''}`}
            onClick={() => setMenuOpen(!menuOpen)}
            aria-label="Toggle menu"
            id="mobile-menu-toggle"
          >
            <span /><span /><span />
          </button>
        </div>

        {/* Mobile menu */}
        <div className={`mobile-menu ${menuOpen ? 'mobile-menu--open' : ''}`}>
          {navItems.map(item => (
            <NavLink
              key={item.path}
              to={item.path}
              className={({ isActive }) => `mobile-nav-link ${isActive ? 'mobile-nav-link--active' : ''}`}
              end={item.path === '/'}
            >
              <span className="mobile-nav-icon">{item.icon}</span>
              {item.label}
            </NavLink>
          ))}
        </div>
      </nav>

      {/* ── Page content ── */}
      <main className="app-main" id="main-content">
        {children}
      </main>

      {/* ── Footer ── */}
      <footer className="app-footer">
        <div className="container">
          <div className="footer-inner">
            <div className="footer-brand">
              <div className="footer-logo">Oryn</div>
              <p className="footer-desc">
                Advisory AI Loan Chatbot powered by LangGraph, RAG, and multi-agent intelligence.
              </p>
              <p className="footer-disclaimer">
                ⚠️ Prototype using synthetic data. Not financial advice.
              </p>
            </div>
            <div className="footer-links">
              <div className="footer-col">
                <h4>Navigate</h4>
                {navItems.map(item => (
                  <NavLink key={item.path} to={item.path} className="footer-link" end={item.path === '/'}>
                    {item.label}
                  </NavLink>
                ))}
              </div>
              <div className="footer-col">
                <h4>Technical</h4>
                <a href="http://localhost:8000/docs" target="_blank" rel="noopener noreferrer" className="footer-link">API Docs</a>
                <a href="http://localhost:8000/redoc" target="_blank" rel="noopener noreferrer" className="footer-link">ReDoc</a>
                <a href="http://localhost:8000/health" target="_blank" rel="noopener noreferrer" className="footer-link">Health Check</a>
              </div>
              <div className="footer-col">
                <h4>Stack</h4>
                <span className="footer-link">LangGraph</span>
                <span className="footer-link">FastAPI</span>
                <span className="footer-link">ChromaDB</span>
                <span className="footer-link">Groq LLM</span>
              </div>
            </div>
          </div>
          <div className="footer-bottom">
            <span>© 2024 Oryn Advisory AI. Built for demonstration purposes.</span>
            <span className="footer-version">v1.0.0</span>
          </div>
        </div>
      </footer>
    </div>
  )
}

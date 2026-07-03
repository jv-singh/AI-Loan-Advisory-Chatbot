import React, { useState } from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import LandingPage from './pages/LandingPage'
import Layout from './components/Layout'
import Dashboard from './pages/Dashboard'
import HowToUse from './pages/HowToUse'
import Features from './pages/Features'
import WhyOryn from './pages/WhyOryn'
import Limitations from './pages/Limitations'
import Roadmap from './pages/Roadmap'

export default function App() {
  const [hasEntered, setHasEntered] = useState(false)

  if (!hasEntered) {
    return <LandingPage onEnter={() => setHasEntered(true)} />
  }

  return (
    <BrowserRouter>
      <Layout>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/how-to-use" element={<HowToUse />} />
          <Route path="/features" element={<Features />} />
          <Route path="/why-oryn" element={<WhyOryn />} />
          <Route path="/limitations" element={<Limitations />} />
          <Route path="/roadmap" element={<Roadmap />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </Layout>
    </BrowserRouter>
  )
}

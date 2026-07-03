import React, { useEffect, useRef, useState, Suspense } from 'react'
import { Canvas, useFrame, useThree } from '@react-three/fiber'
import { OrbitControls, Sphere, MeshDistortMaterial, Float, Stars, Text3D, Center } from '@react-three/drei'
import * as THREE from 'three'
import './LandingPage.css'

/* ── 3D Scene Components ──────────────────────────────────── */

function VaultCore() {
  const meshRef = useRef()
  const ringRef = useRef()
  const innerRef = useRef()

  useFrame((state) => {
    const t = state.clock.getElapsedTime()
    if (meshRef.current) {
      meshRef.current.rotation.y = t * 0.15
      meshRef.current.rotation.x = Math.sin(t * 0.3) * 0.1
    }
    if (ringRef.current) {
      ringRef.current.rotation.z = t * 0.4
      ringRef.current.rotation.x = Math.PI / 2 + Math.sin(t * 0.2) * 0.1
    }
    if (innerRef.current) {
      innerRef.current.rotation.y = -t * 0.3
      innerRef.current.scale.setScalar(1 + Math.sin(t * 2) * 0.05)
    }
  })

  return (
    <group position={[0, 0, 0]}>
      {/* Outer vault sphere */}
      <mesh ref={meshRef}>
        <icosahedronGeometry args={[1.6, 1]} />
        <meshStandardMaterial
          color="#0f3460"
          metalness={0.9}
          roughness={0.1}
          wireframe={false}
          emissive="#1a56db"
          emissiveIntensity={0.15}
        />
      </mesh>

      {/* Wireframe overlay */}
      <mesh ref={meshRef} scale={1.01}>
        <icosahedronGeometry args={[1.6, 1]} />
        <meshStandardMaterial
          color="#3b82f6"
          wireframe
          transparent
          opacity={0.4}
          emissive="#60a5fa"
          emissiveIntensity={0.3}
        />
      </mesh>

      {/* Inner glowing orb */}
      <mesh ref={innerRef}>
        <sphereGeometry args={[0.8, 32, 32]} />
        <MeshDistortMaterial
          color="#1d4ed8"
          attach="material"
          distort={0.5}
          speed={2}
          roughness={0.2}
          metalness={0.8}
          emissive="#3b82f6"
          emissiveIntensity={0.4}
        />
      </mesh>

      {/* Orbital ring 1 */}
      <mesh ref={ringRef}>
        <torusGeometry args={[2.2, 0.04, 16, 100]} />
        <meshStandardMaterial
          color="#2563eb"
          emissive="#3b82f6"
          emissiveIntensity={0.8}
          metalness={1}
          roughness={0}
        />
      </mesh>

      {/* Orbital ring 2 */}
      <mesh rotation={[Math.PI / 3, 0, Math.PI / 4]}>
        <torusGeometry args={[2.6, 0.025, 16, 100]} />
        <meshStandardMaterial
          color="#f59e0b"
          emissive="#fbbf24"
          emissiveIntensity={0.6}
          metalness={1}
          roughness={0}
        />
      </mesh>

      {/* Orbital ring 3 */}
      <mesh rotation={[-Math.PI / 4, Math.PI / 6, 0]}>
        <torusGeometry args={[3.0, 0.02, 16, 100]} />
        <meshStandardMaterial
          color="#06b6d4"
          emissive="#22d3ee"
          emissiveIntensity={0.5}
          transparent
          opacity={0.7}
          metalness={1}
          roughness={0}
        />
      </mesh>
    </group>
  )
}

function FloatingCubes() {
  const cubes = useRef([])
  const count = 8

  useFrame((state) => {
    const t = state.clock.getElapsedTime()
    cubes.current.forEach((cube, i) => {
      if (cube) {
        const angle = (i / count) * Math.PI * 2 + t * 0.2
        const radius = 4.5 + Math.sin(t * 0.5 + i) * 0.3
        cube.position.x = Math.cos(angle) * radius
        cube.position.y = Math.sin(t * 0.8 + i * 0.7) * 1.2
        cube.position.z = Math.sin(angle) * radius
        cube.rotation.x = t * 0.3 + i
        cube.rotation.y = t * 0.2 + i * 0.5
      }
    })
  })

  return (
    <>
      {Array.from({ length: count }).map((_, i) => (
        <mesh key={i} ref={(el) => (cubes.current[i] = el)}>
          <boxGeometry args={[0.2, 0.2, 0.2]} />
          <meshStandardMaterial
            color={i % 2 === 0 ? '#2563eb' : '#f59e0b'}
            emissive={i % 2 === 0 ? '#3b82f6' : '#fbbf24'}
            emissiveIntensity={0.8}
            metalness={0.9}
            roughness={0.1}
          />
        </mesh>
      ))}
    </>
  )
}

function DataParticles() {
  const points = useRef()
  const count = 400

  const positions = React.useMemo(() => {
    const pos = new Float32Array(count * 3)
    for (let i = 0; i < count; i++) {
      const r = 5 + Math.random() * 6
      const theta = Math.random() * Math.PI * 2
      const phi = Math.random() * Math.PI
      pos[i * 3] = r * Math.sin(phi) * Math.cos(theta)
      pos[i * 3 + 1] = r * Math.cos(phi)
      pos[i * 3 + 2] = r * Math.sin(phi) * Math.sin(theta)
    }
    return pos
  }, [])

  useFrame((state) => {
    if (points.current) {
      points.current.rotation.y = state.clock.getElapsedTime() * 0.05
      points.current.rotation.x = state.clock.getElapsedTime() * 0.02
    }
  })

  return (
    <points ref={points}>
      <bufferGeometry>
        <bufferAttribute
          attach="attributes-position"
          count={count}
          array={positions}
          itemSize={3}
        />
      </bufferGeometry>
      <pointsMaterial
        size={0.04}
        color="#60a5fa"
        transparent
        opacity={0.7}
        sizeAttenuation
      />
    </points>
  )
}

function Scene() {
  const { camera } = useThree()

  useEffect(() => {
    camera.position.set(0, 0, 8)
  }, [camera])

  useFrame((state) => {
    const t = state.clock.getElapsedTime()
    camera.position.x = Math.sin(t * 0.1) * 0.5
    camera.position.y = Math.cos(t * 0.08) * 0.3
    camera.lookAt(0, 0, 0)
  })

  return (
    <>
      <ambientLight intensity={0.2} />
      <directionalLight position={[5, 5, 5]} intensity={0.5} color="#ffffff" />
      <pointLight position={[-5, -5, -5]} intensity={0.8} color="#3b82f6" />
      <pointLight position={[5, -3, 3]} intensity={0.6} color="#f59e0b" />
      <pointLight position={[0, 5, -5]} intensity={0.4} color="#06b6d4" />

      <Stars radius={60} depth={50} count={3000} factor={3} saturation={0} fade speed={1.5} />
      <DataParticles />
      <FloatingCubes />

      <Float speed={1.5} rotationIntensity={0.2} floatIntensity={0.4}>
        <VaultCore />
      </Float>
    </>
  )
}

/* ── Particle background (CSS) ────────────────────────────── */
function HeroParticles() {
  return (
    <div className="hero-particles" aria-hidden>
      {Array.from({ length: 20 }).map((_, i) => (
        <div key={i} className={`hero-particle hero-particle--${i % 4}`} style={{
          '--delay': `${(i * 0.4) % 4}s`,
          '--x': `${5 + (i * 4.7) % 90}%`,
          '--duration': `${6 + (i * 0.7) % 6}s`
        }} />
      ))}
    </div>
  )
}

/* ── Typing animation ─────────────────────────────────────── */
function TypedSubtitle({ text }) {
  const [displayed, setDisplayed] = useState('')
  const [phase, setPhase] = useState(0) // 0=typing, 1=done

  useEffect(() => {
    if (phase !== 0) return
    let i = 0
    const interval = setInterval(() => {
      setDisplayed(text.slice(0, i + 1))
      i++
      if (i >= text.length) {
        clearInterval(interval)
        setPhase(1)
      }
    }, 40)
    return () => clearInterval(interval)
  }, [text, phase])

  return (
    <span>
      {displayed}
      {phase === 0 && <span className="typing-cursor">|</span>}
    </span>
  )
}

/* ── Stat counter ─────────────────────────────────────────── */
function StatCounter({ value, label, prefix = '', suffix = '' }) {
  const [count, setCount] = useState(0)
  const ref = useRef()

  useEffect(() => {
    const observer = new IntersectionObserver(([entry]) => {
      if (entry.isIntersecting) {
        let start = 0
        const end = parseInt(value)
        const duration = 1500
        const step = end / (duration / 16)
        const timer = setInterval(() => {
          start = Math.min(start + step, end)
          setCount(Math.floor(start))
          if (start >= end) clearInterval(timer)
        }, 16)
      }
    }, { threshold: 0.5 })
    if (ref.current) observer.observe(ref.current)
    return () => observer.disconnect()
  }, [value])

  return (
    <div className="stat-item" ref={ref}>
      <div className="stat-value">{prefix}{count}{suffix}</div>
      <div className="stat-label">{label}</div>
    </div>
  )
}

/* ── Main LandingPage ─────────────────────────────────────── */
export default function LandingPage({ onEnter }) {
  const [entered, setEntered] = useState(false)
  const heroRef = useRef()
  const titleRef = useRef()

  const handleEnter = () => {
    setEntered(true)
    setTimeout(onEnter, 800)
  }

  useEffect(() => {
    // Animate title on load
    const title = titleRef.current
    if (title) {
      title.style.opacity = '0'
      title.style.transform = 'translateY(40px)'
      setTimeout(() => {
        title.style.transition = 'all 1s cubic-bezier(0.19, 1, 0.22, 1)'
        title.style.opacity = '1'
        title.style.transform = 'translateY(0)'
      }, 300)
    }
  }, [])

  return (
    <div className={`landing ${entered ? 'landing--exiting' : ''}`}>
      {/* ── 3D Canvas background ── */}
      <div className="landing-canvas">
        <Canvas
          dpr={[1, 2]}
          gl={{ antialias: true, alpha: true }}
          camera={{ fov: 60, near: 0.1, far: 100 }}
        >
          <Suspense fallback={null}>
            <Scene />
          </Suspense>
        </Canvas>
      </div>

      {/* ── Atmospheric overlays ── */}
      <div className="landing-vignette" />
      <div className="landing-scan-line" />
      <HeroParticles />

      {/* ── Gradient orbs ── */}
      <div className="orb orb--blue" />
      <div className="orb orb--gold" />
      <div className="orb orb--cyan" />

      {/* ── Grid overlay ── */}
      <div className="landing-grid" aria-hidden />

      {/* ── Hero content ── */}
      <div className="landing-content">
        {/* Top badge */}
        <div className="landing-badge">
          <span className="badge-dot" />
          <span>AI-Powered Financial Advisory</span>
        </div>

        {/* Main title */}
        <div className="landing-title-wrap" ref={titleRef}>
          <h1 className="landing-title">
            <span className="title-oryn">Oryn</span>
          </h1>
          <div className="title-tagline-wrap">
            <div className="title-line" />
            <span className="title-tagline">Financial Intelligence</span>
            <div className="title-line" />
          </div>
        </div>

        {/* Subtitle */}
        <p className="landing-subtitle">
          <TypedSubtitle text="Advisory AI Loan Chatbot — Handle Your Loans & Finance Like a PRO" />
        </p>

        {/* Stats row */}
        <div className="landing-stats">
          <StatCounter value="99" suffix="%" label="Accuracy Rate" />
          <div className="stat-divider" />
          <StatCounter value="50" prefix="" suffix="+" label="Loan Types Covered" />
          <div className="stat-divider" />
          <StatCounter value="180" suffix="s" label="Response Time" />
          <div className="stat-divider" />
          <StatCounter value="24" suffix="/7" label="Available" />
        </div>

        {/* CTA buttons */}
        <div className="landing-cta">
          <button className="cta-enter" onClick={handleEnter} id="enter-oryn-btn">
            <span className="cta-enter__text">Enter Oryn</span>
            <span className="cta-enter__icon">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                <path d="M5 12h14M12 5l7 7-7 7" />
              </svg>
            </span>
            <span className="cta-enter__glow" />
          </button>
          <button className="cta-learn">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M14.5 10c-.83 0-1.5-.67-1.5-1.5v-5c0-.83.67-1.5 1.5-1.5s1.5.67 1.5 1.5v5c0 .83-.67 1.5-1.5 1.5z"/>
              <path d="M20.5 10H19V8.5c0-.83.67-1.5 1.5-1.5s1.5.67 1.5 1.5-.67 1.5-1.5 1.5z"/>
              <path d="M9.5 14c.83 0 1.5.67 1.5 1.5v5c0 .83-.67 1.5-1.5 1.5S8 21.33 8 20.5v-5c0-.83.67-1.5 1.5-1.5z"/>
              <path d="M3.5 14H5v1.5c0 .83-.67 1.5-1.5 1.5S2 16.33 2 15.5 2.67 14 3.5 14z"/>
              <path d="M14 14.5c0-.83.67-1.5 1.5-1.5h5c.83 0 1.5.67 1.5 1.5s-.67 1.5-1.5 1.5h-5c-.83 0-1.5-.67-1.5-1.5z"/>
              <path d="M15.5 19H14v1.5c0 .83.67 1.5 1.5 1.5s1.5-.67 1.5-1.5-.67-1.5-1.5-1.5z"/>
              <path d="M10 9.5C10 8.67 9.33 8 8.5 8h-5C2.67 8 2 8.67 2 9.5S2.67 11 3.5 11h5c.83 0 1.5-.67 1.5-1.5z"/>
              <path d="M8.5 5H10V3.5C10 2.67 9.33 2 8.5 2S7 2.67 7 3.5 7.67 5 8.5 5z"/>
            </svg>
            Learn More
          </button>
        </div>

        {/* Feature pills */}
        <div className="landing-pills">
          {['Loan Eligibility', 'EMI Calculator', 'Document Guidance', 'Fraud Detection', 'Policy Q&A'].map(pill => (
            <div className="feature-pill" key={pill}>{pill}</div>
          ))}
        </div>
      </div>

      {/* ── Scroll indicator ── */}
      <div className="scroll-indicator">
        <div className="scroll-mouse">
          <div className="scroll-wheel" />
        </div>
        <span>Scroll to explore</span>
      </div>

      {/* ── Bottom info strip ── */}
      <div className="landing-footer-strip">
        <div className="footer-strip-item">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>
          <span>Bank-grade security</span>
        </div>
        <div className="footer-strip-item">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
          <span>Real-time advisory</span>
        </div>
        <div className="footer-strip-item">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
          <span>Intelligent chatbot</span>
        </div>
        <div className="footer-strip-item">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>
          <span>Multi-agent AI</span>
        </div>
      </div>
    </div>
  )
}

import { useEffect, useState } from 'react'
import { H3, Body } from '@leafygreen-ui/typography'
import Banner from '@leafygreen-ui/banner'
import { Leaf } from './components.jsx'
import { getConfig, getClusters } from './api.js'

import Overview from './pages/Overview.jsx'
import Clusters from './pages/Clusters.jsx'
import PerformanceAdvisor from './pages/PerformanceAdvisor.jsx'
import Profiler from './pages/Profiler.jsx'
import Scale from './pages/Scale.jsx'
import FinOps from './pages/FinOps.jsx'
import Compare from './pages/Compare.jsx'
import Health from './pages/Health.jsx'
import Chat from './pages/Chat.jsx'

const NAV = [
  { section: 'Principal' },
  { id: 'overview', label: 'Visão Geral', icon: '📊', Comp: Overview },
  { id: 'clusters', label: 'Clusters', icon: '🗄️', Comp: Clusters },
  { section: 'Performance' },
  { id: 'pa', label: 'Performance Advisor', icon: '⚡', Comp: PerformanceAdvisor },
  { id: 'profiler', label: 'Query Profiler', icon: '🔍', Comp: Profiler },
  { id: 'health', label: 'Health Score', icon: '❤️', Comp: Health },
  { section: 'Operações' },
  { id: 'scale', label: 'Scale', icon: '📈', Comp: Scale },
  { id: 'finops', label: 'FinOps', icon: '💰', Comp: FinOps },
  { id: 'compare', label: 'Compare', icon: '📊', Comp: Compare },
  { section: 'IA' },
  { id: 'chat', label: 'AI Chat', icon: '💬', Comp: Chat },
]

export default function App() {
  const [active, setActive] = useState('overview')
  const [config, setConfig] = useState(null)
  const [clusters, setClusters] = useState([])
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.all([getConfig(), getClusters()])
      .then(([cfg, cls]) => { setConfig(cfg); setClusters(cls) })
      .catch(e => setError(e?.response?.data?.detail || e.message))
      .finally(() => setLoading(false))
  }, [])

  const Current = NAV.find(n => n.id === active)?.Comp || Overview

  return (
    <div className="app-shell">
      <nav className="sidenav">
        <div className="sidenav-brand">
          <Leaf size={28} />
          <div>
            <div style={{ fontWeight: 800, fontSize: 15, color: '#E3FCF7' }}>Maestro</div>
            <div className="mono" style={{ fontSize: 9, color: '#3D5A6C', letterSpacing: 1.5 }}>ATLAS CONTROL PLANE</div>
          </div>
        </div>
        {NAV.map((n, i) => n.section
          ? <div key={i} className="sidenav-section">{n.section}</div>
          : <button key={n.id} className={`sidenav-item ${active === n.id ? 'active' : ''}`} onClick={() => setActive(n.id)}>
              <span>{n.icon}</span>{n.label}
            </button>
        )}
        <div className="spacer" />
        {config && (
          <div className="mono" style={{ fontSize: 10, color: '#3D5A6C', padding: '8px 12px', borderTop: '1px solid rgba(255,255,255,0.06)' }}>
            {config.atlas ? '🟢' : '🔴'} Atlas&nbsp;&nbsp;{config.anthropic ? '🟢' : '⚪'} Claude&nbsp;&nbsp;{config.mongodb ? '🟢' : '⚪'} Mongo
          </div>
        )}
      </nav>

      <main className="main">
        {loading && <Body style={{ color: '#889397' }}>🍃 Conectando ao MongoDB Atlas…</Body>}
        {error && <Banner variant="danger">Erro ao carregar: {error}</Banner>}
        {!loading && !error && config && (
          <Current clusters={clusters} config={config} />
        )}
      </main>
    </div>
  )
}

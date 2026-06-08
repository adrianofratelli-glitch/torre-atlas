import { useEffect, useState } from 'react'
import { H1 } from '@leafygreen-ui/typography'
import { Leaf, KpiGrid, Kpi, Section, StatusDot } from '../components.jsx'
import { getAlerts } from '../api.js'

export default function Overview({ clusters }) {
  const [alerts, setAlerts] = useState(0)
  useEffect(() => {
    const ids = [...new Set(clusters.map(c => c.project_id))]
    if (ids.length) getAlerts(ids).then(setAlerts).catch(() => {})
  }, [clusters])

  const projects = new Set(clusters.map(c => c.project_name)).size
  const idle = clusters.filter(c => c.status === 'IDLE').length
  const costBrl = clusters.reduce((s, c) => s + c.cost_brl, 0)
  const costUsd = clusters.reduce((s, c) => s + c.cost_usd, 0)
  const dedic = clusters.filter(c => c.tier !== 'Free/Shared')
  const topTier = dedic.length ? mode(dedic.map(c => c.tier)) : '—'

  return (
    <>
      <div className="page-head">
        <Leaf size={26} />
        <H1 style={{ color: '#E3FCF7' }}>Visão Geral</H1>
      </div>

      <KpiGrid>
        <Kpi label="Total Clusters" value={clusters.length} />
        <Kpi label="Projetos" value={projects} color="#0498EC" />
        <Kpi label="Ativos (IDLE)" value={`${idle}/${clusters.length}`}
             delta={idle === clusters.length ? 'todos online' : `${clusters.length - idle} offline`}
             color={idle === clusters.length ? '#00ED64' : '#FFC010'} />
        <Kpi label="Tier + comum" value={topTier} color="#00A35C" />
        <Kpi label="Custo / Mês" value={`R$ ${fmt(costBrl)}`} delta={`≈ USD ${fmt(costUsd)}`} />
        <Kpi label="Alertas" value={alerts} delta={alerts === 0 ? '✓ nenhum' : `↑ ${alerts} abertos`}
             color={alerts === 0 ? '#00ED64' : '#FFC010'} />
      </KpiGrid>

      <Section title="Frota de Clusters" badge={String(clusters.length)} />
      {clusters.map(c => (
        <div key={c.cluster_name} className="fleet-card" style={{ borderLeft: `3px solid ${dotColor(c.status)}` }}>
          <StatusDot status={c.status} />
          <div style={{ flex: 1 }}>
            <div className="mono" style={{ fontWeight: 700, color: '#E3FCF7' }}>{c.cluster_name}</div>
            <div style={{ fontSize: 11, color: '#889397', marginTop: 2 }}>
              {c.tier} · {c.region_pretty} · MongoDB {c.mongo_version}
            </div>
          </div>
          <div style={{ textAlign: 'right' }}>
            <div className="mono" style={{ fontSize: 11, fontWeight: 700, color: dotColor(c.status) }}>{c.status}</div>
            <div className="mono" style={{ fontSize: 9, color: '#3D5A6C' }}>{c.cluster_type}</div>
          </div>
        </div>
      ))}
      <div style={{ fontSize: 12, color: '#5C6C75', marginTop: 14 }}>
        💡 Métricas vivas (CPU, conexões, IOPS) ficam sob demanda nas abas <b>Scale</b>, <b>Health Score</b> e <b>AI Chat</b> — para manter a Visão Geral rápida.
      </div>
    </>
  )
}

const fmt = (n) => Math.round(n).toLocaleString('pt-BR')
const dotColor = (s) => s === 'IDLE' ? '#00ED64' : s === 'PAUSED' ? '#FFC010' : '#0498EC'
function mode(arr) { const m = {}; let best = arr[0], bc = 0; arr.forEach(v => { m[v] = (m[v]||0)+1; if (m[v]>bc){bc=m[v];best=v} }); return best }

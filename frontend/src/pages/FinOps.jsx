import { useState, useEffect } from 'react'
import { H1, Body } from '@leafygreen-ui/typography'
import Banner from '@leafygreen-ui/banner'
import Badge from '@leafygreen-ui/badge'
import { KpiGrid, Kpi, Section } from '../components.jsx'
import { getFinops } from '../api.js'

const fmt = (n) => Math.round(n).toLocaleString('pt-BR')
const COLOR = { green: '#00ED64', yellow: '#f97316', red: '#ef4444', muted: '#7fa8bc' }
const VAR = { green: 'green', yellow: 'yellow', red: 'red', muted: 'lightgray' }

export default function FinOps({ clusters }) {
  const [data, setData] = useState(null)
  const [busy, setBusy] = useState(true)

  useEffect(() => { getFinops().then(setData).catch(() => setData({ clusters: [], total_usd: 0, potential_savings_usd: 0 })).finally(() => setBusy(false)) }, [])

  // Totals come straight from the clusters (instant) — independent of the slow /finops
  const totalBrl = clusters.reduce((s, c) => s + c.cost_brl, 0)
  const totalUsd = clusters.reduce((s, c) => s + c.cost_usd, 0)
  const avg = clusters.length ? totalBrl / clusters.length : 0
  const measured = data?.clusters.filter(c => c.cpu != null) || []
  const overprov = measured.filter(c => c.color === 'yellow')
  const saturated = measured.filter(c => c.color === 'red')

  // Project-wide verdict
  let verdict = { variant: 'success', text: '✅ Custos saudáveis — a utilização justifica o investimento.' }
  if (saturated.length) verdict = { variant: 'warning', text: `⚠️ ${saturated.length} cluster(s) saturado(s) — pode ser hora de scale up para manter performance.` }
  else if (overprov.length) verdict = { variant: 'info', text: `💡 ${overprov.length} cluster(s) subutilizado(s) — possível economia de ~$${fmt(data.potential_savings_usd)}/mês com scale down.` }

  return (
    <>
      <div className="page-head"><H1 style={{ color: '#fafafa' }}>FinOps</H1></div>
      <KpiGrid>
        <Kpi label="Total USD/Mês" value={`$${fmt(totalUsd)}`} />
        <Kpi label="Total BRL/Mês" value={`R$ ${fmt(totalBrl)}`} color="#00A35C" />
        <Kpi label="Média/Cluster" value={`R$ ${fmt(avg)}`} color="#06b6d4" />
        <Kpi label="Economia Potencial" value={busy ? '…' : `$${fmt(data?.potential_savings_usd || 0)}`}
             delta={busy ? 'avaliando…' : overprov.length ? `${overprov.length} subutilizado(s)` : 'frota otimizada'}
             color={overprov.length ? '#f97316' : '#00ED64'} />
      </KpiGrid>

      {!busy && <Banner variant={verdict.variant} style={{ marginBottom: 18 }}>{verdict.text}</Banner>}

      <Section title="Eficiência por Cluster" sub="custo vs utilização real de CPU" />
      {busy && <Body style={{ color: '#7fa8bc' }}>Avaliando utilização dos clusters…</Body>}
      {!busy && (
        <table className="mdb">
          <thead><tr><th>Projeto</th><th>Cluster</th><th>Tier</th><th>CPU</th><th style={{ textAlign: 'right' }}>USD/Mês</th><th>Veredito</th></tr></thead>
          <tbody>
            {[...(data?.clusters || [])].sort((a, b) => b.cost_usd - a.cost_usd).map((c, i) => (
              <tr key={i}>
                <td>{c.project}</td>
                <td className="mono" style={{ color: '#00ED64' }}>{c.cluster}</td>
                <td className="mono">{c.tier}</td>
                <td className="mono" style={{ color: c.cpu == null ? '#6b94a8' : COLOR[c.color] }}>{c.cpu == null ? '—' : `${c.cpu}%`}</td>
                <td className="mono" style={{ textAlign: 'right' }}>${fmt(c.cost_usd)}</td>
                <td><Badge variant={VAR[c.color]}>{c.verdict}</Badge></td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </>
  )
}

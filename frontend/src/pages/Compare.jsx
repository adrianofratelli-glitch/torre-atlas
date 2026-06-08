import { useState } from 'react'
import { H1, Body } from '@leafygreen-ui/typography'
import Button from '@leafygreen-ui/button'
import Banner from '@leafygreen-ui/banner'
import { Section, Empty } from '../components.jsx'
import { getHealth } from '../api.js'

export default function Compare({ clusters }) {
  const [a, setA] = useState(clusters[0])
  const [b, setB] = useState(clusters[1] || clusters[0])
  const [data, setData] = useState(null)
  const [busy, setBusy] = useState(false)

  const cmp = async () => {
    setBusy(true)
    try {
      const [ha, hb] = await Promise.all([
        getHealth(a.project_id, a.cluster_name, a.status, a.mongo_version),
        getHealth(b.project_id, b.cluster_name, b.status, b.mongo_version),
      ])
      setData({ a: { ...a, ...ha }, b: { ...b, ...hb } })
    } finally { setBusy(false) }
  }

  if (clusters.length < 2) return <><div className="page-head"><H1>Compare</H1></div><Empty icon="📊" title="São necessários 2 clusters" hint="Esta organização tem apenas um cluster." /></>

  const Sel = ({ v, set, label }) => (
    <div>
      <div style={{ fontSize: 12, color: '#889397', marginBottom: 6 }}>{label}</div>
      <select className="mono" value={v.cluster_name} onChange={e => set(clusters.find(c => c.cluster_name === e.target.value))}
        style={{ background: '#00271C', color: '#E3FCF7', border: '1px solid rgba(0,237,100,0.22)', borderRadius: 6, padding: '8px 12px', minWidth: 220 }}>
        {clusters.map(c => <option key={c.cluster_name} value={c.cluster_name}>{c.cluster_name}</option>)}
      </select>
    </div>
  )

  // metric, valueA, valueB, betterWhen ('high'|'low'|null)
  const metrics = data ? [
    ['Health Score', data.a.score, data.b.score, 'high', v => `${v}/100`],
    ['Grade', data.a.grade, data.b.grade, null, v => v],
    ['PA Sugestões', data.a.n_pa, data.b.n_pa, 'low', v => v],
    ['Slow Queries', data.a.n_sq, data.b.n_sq, 'low', v => v],
    ['Custo USD/Mês', data.a.cost_usd, data.b.cost_usd, 'low', v => `$${v}`],
    ['Tier', data.a.tier, data.b.tier, null, v => v],
    ['Região', data.a.region_pretty, data.b.region_pretty, null, v => v],
    ['MongoDB', data.a.mongo_version, data.b.mongo_version, 'high', v => v],
  ] : []

  const winner = (va, vb, better) => {
    if (better === null || va === vb) return 0
    const na = parseFloat(va), nb = parseFloat(vb)
    const a_ = isNaN(na) ? va : na, b_ = isNaN(nb) ? vb : nb
    if (better === 'high') return a_ > b_ ? -1 : 1
    return a_ < b_ ? -1 : 1   // low is better
  }

  // Resumo: quem venceu mais métricas
  let scoreA = 0, scoreB = 0
  metrics.forEach(([, va, vb, better]) => { const w = winner(va, vb, better); if (w < 0) scoreA++; if (w > 0) scoreB++ })

  return (
    <>
      <div className="page-head"><H1 style={{ color: '#E3FCF7' }}>Comparar Clusters</H1></div>
      <div className="row" style={{ marginBottom: 18, alignItems: 'flex-end' }}>
        <Sel v={a} set={setA} label="🔵 Cluster A" />
        <Sel v={b} set={setB} label="🟠 Cluster B" />
        <Button variant="primary" onClick={cmp} disabled={busy}>{busy ? 'Comparando…' : '🔍 Comparar'}</Button>
      </div>

      {data && (
        <>
          <Banner variant={scoreA === scoreB ? 'info' : 'success'} style={{ marginBottom: 16 }}>
            {scoreA === scoreB
              ? `Empate técnico — ${data.a.cluster_name} e ${data.b.cluster_name} vencem ${scoreA} métrica(s) cada.`
              : `🏆 ${scoreA > scoreB ? data.a.cluster_name : data.b.cluster_name} leva vantagem geral (${Math.max(scoreA, scoreB)} × ${Math.min(scoreA, scoreB)} métricas).`}
          </Banner>
          <Section title="Comparativo detalhado" sub="🏆 = melhor nessa métrica" />
          <table className="mdb">
            <thead><tr><th>Métrica</th><th>🔵 {data.a.cluster_name}</th><th>🟠 {data.b.cluster_name}</th><th>Quem está melhor</th></tr></thead>
            <tbody>
              {metrics.map(([m, va, vb, better, fmt], i) => {
                const w = winner(va, vb, better)
                return (
                  <tr key={i}>
                    <td style={{ color: '#889397' }}>{m}</td>
                    <td className="mono" style={{ color: w < 0 ? '#00ED64' : '#E3FCF7', fontWeight: w < 0 ? 700 : 400 }}>{w < 0 ? '🏆 ' : ''}{fmt(va)}</td>
                    <td className="mono" style={{ color: w > 0 ? '#00ED64' : '#E3FCF7', fontWeight: w > 0 ? 700 : 400 }}>{w > 0 ? '🏆 ' : ''}{fmt(vb)}</td>
                    <td style={{ fontSize: 12, color: '#889397' }}>
                      {better === null ? '—' : w === 0 ? 'empate' : `${w < 0 ? data.a.cluster_name : data.b.cluster_name} (${better === 'low' ? 'menor é melhor' : 'maior é melhor'})`}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </>
      )}
    </>
  )
}

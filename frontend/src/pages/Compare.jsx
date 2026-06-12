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
  const [err, setErr] = useState(null)

  const cmp = async () => {
    setBusy(true); setErr(null)
    try {
      const [ha, hb] = await Promise.all([
        getHealth(a.project_id, a.cluster_name, a.status, a.mongo_version),
        getHealth(b.project_id, b.cluster_name, b.status, b.mongo_version),
      ])
      setData({ a: { ...a, ...ha }, b: { ...b, ...hb } })
    } catch (e) {
      setErr(e?.response?.data?.detail || e.message)
    } finally { setBusy(false) }
  }

  if (clusters.length < 2) return <><div className="page-head"><H1>Compare</H1></div><Empty icon="📊" title="São necessários 2 clusters" hint="Esta organização tem apenas um cluster." /></>

  const Sel = ({ v, set, label }) => (
    <div>
      <div style={{ fontSize: 12, color: '#7fa8bc', marginBottom: 6 }}>{label}</div>
      <select className="mono" value={v.cluster_name} onChange={e => set(clusters.find(c => c.cluster_name === e.target.value))}
        style={{ background: '#003345', color: '#fafafa', border: '1px solid rgba(0,237,100,0.25)', borderRadius: 6, padding: '8px 12px', minWidth: 220 }}>
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

  // Compara versões segmento a segmento ("7.0.28" vs "8.0.5") — parseFloat
  // descartaria o patch e empataria "7.0.2" com "7.0.28"
  const cmpVersion = (va, vb) => {
    const sa = String(va).split('.').map(Number), sb = String(vb).split('.').map(Number)
    for (let i = 0; i < Math.max(sa.length, sb.length); i++) {
      const d = (sa[i] || 0) - (sb[i] || 0)
      if (d !== 0) return d
    }
    return 0
  }

  const winner = (va, vb, better) => {
    if (better === null || va === vb) return 0
    const isVersion = v => /^\d+(\.\d+)+$/.test(String(v))
    let diff
    if (isVersion(va) && isVersion(vb)) {
      diff = cmpVersion(va, vb)
    } else {
      const na = parseFloat(va), nb = parseFloat(vb)
      const a_ = isNaN(na) ? va : na, b_ = isNaN(nb) ? vb : nb
      diff = a_ > b_ ? 1 : a_ < b_ ? -1 : 0
    }
    if (diff === 0) return 0
    if (better === 'high') return diff > 0 ? -1 : 1
    return diff < 0 ? -1 : 1   // low is better
  }

  // Resumo: quem venceu mais métricas
  let scoreA = 0, scoreB = 0
  metrics.forEach(([, va, vb, better]) => { const w = winner(va, vb, better); if (w < 0) scoreA++; if (w > 0) scoreB++ })

  return (
    <>
      <div className="page-head"><H1 style={{ color: '#fafafa' }}>Comparar Clusters</H1></div>
      <div className="row" style={{ marginBottom: 18, alignItems: 'flex-end' }}>
        <Sel v={a} set={setA} label="🔵 Cluster A" />
        <Sel v={b} set={setB} label="🟠 Cluster B" />
        <Button variant="primary" onClick={cmp} disabled={busy}>{busy ? 'Comparando…' : '🔍 Comparar'}</Button>
      </div>

      {err && <Banner variant="danger" style={{ marginBottom: 16 }}>{err}</Banner>}

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
                    <td style={{ color: '#7fa8bc' }}>{m}</td>
                    <td className="mono" style={{ color: w < 0 ? '#00ED64' : '#fafafa', fontWeight: w < 0 ? 700 : 400 }}>{w < 0 ? '🏆 ' : ''}{fmt(va)}</td>
                    <td className="mono" style={{ color: w > 0 ? '#00ED64' : '#fafafa', fontWeight: w > 0 ? 700 : 400 }}>{w > 0 ? '🏆 ' : ''}{fmt(vb)}</td>
                    <td style={{ fontSize: 12, color: '#7fa8bc' }}>
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

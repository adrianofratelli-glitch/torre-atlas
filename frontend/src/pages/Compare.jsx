import { useState } from 'react'
import { H1 } from '@leafygreen-ui/typography'
import Button from '@leafygreen-ui/button'
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

  if (clusters.length < 2) return <><div className="page-head"><H1 style={{ color: '#E3FCF7' }}>Compare</H1></div><Empty icon="📊" title="São necessários 2 clusters" hint="Esta organização tem apenas um cluster." /></>

  const Sel = ({ v, set, label }) => (
    <div>
      <div style={{ fontSize: 12, color: '#889397', marginBottom: 6 }}>{label}</div>
      <select className="mono" value={v.cluster_name} onChange={e => set(clusters.find(c => c.cluster_name === e.target.value))}
        style={{ background: '#00271C', color: '#E3FCF7', border: '1px solid rgba(0,237,100,0.22)', borderRadius: 6, padding: '8px 12px', minWidth: 220 }}>
        {clusters.map(c => <option key={c.cluster_name} value={c.cluster_name}>{c.cluster_name}</option>)}
      </select>
    </div>
  )

  const rows = data ? [
    ['Tier', data.a.tier, data.b.tier],
    ['Região', data.a.region_pretty, data.b.region_pretty],
    ['Status', data.a.status, data.b.status],
    ['MongoDB', data.a.mongo_version, data.b.mongo_version],
    ['PA Sugestões', data.a.n_pa, data.b.n_pa],
    ['Slow Queries', data.a.n_sq, data.b.n_sq],
    ['Health Score', `${data.a.score}/100`, `${data.b.score}/100`],
    ['Grade', data.a.grade, data.b.grade],
    ['USD/Mês', `$${data.a.cost_usd}`, `$${data.b.cost_usd}`],
  ] : []

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
          <Section title="Comparativo" />
          <table className="mdb">
            <thead><tr><th>Métrica</th><th>🔵 {data.a.cluster_name}</th><th>🟠 {data.b.cluster_name}</th></tr></thead>
            <tbody>{rows.map((r, i) => <tr key={i}><td style={{ color: '#889397' }}>{r[0]}</td><td className="mono">{r[1]}</td><td className="mono">{r[2]}</td></tr>)}</tbody>
          </table>
        </>
      )}
    </>
  )
}

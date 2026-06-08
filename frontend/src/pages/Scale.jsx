import { useState, useEffect } from 'react'
import { H1, Body } from '@leafygreen-ui/typography'
import Button from '@leafygreen-ui/button'
import Banner from '@leafygreen-ui/banner'
import { KpiGrid, Kpi, Section, MiniChart } from '../components.jsx'
import { getScaling, getSeries, scaleCluster } from '../api.js'
import { ClusterPicker } from './_picker.jsx'

export default function Scale({ clusters, config }) {
  const [sel, setSel] = useState(clusters[0])
  const [rec, setRec] = useState(null)
  const [series, setSeries] = useState(null)
  const [newTier, setNewTier] = useState(sel?.tier)
  const [msg, setMsg] = useState(null)

  useEffect(() => {
    if (!sel) return
    setRec(null); setSeries(null); setNewTier(sel.tier); setMsg(null)
    getScaling(sel.project_id, sel.cluster_name, sel.tier).then(setRec).catch(() => {})
    getSeries(sel.project_id, sel.cluster_name).then(setSeries).catch(() => {})
  }, [sel])

  const tiers = config.tiers.dedicated
  const doScale = async () => {
    try { const r = await scaleCluster(sel.project_id, sel.cluster_name, newTier); setMsg({ ok: true, t: `Scaling iniciado! Status: ${r.state}` }) }
    catch (e) { setMsg({ ok: false, t: e?.response?.data?.detail || e.message }) }
  }

  const recColor = rec?.severity === 'high' ? 'danger' : rec?.severity === 'med' ? 'warning' : 'success'
  return (
    <>
      <div className="page-head"><H1 style={{ color: '#E3FCF7' }}>Scale</H1></div>
      <Banner variant="info" style={{ marginBottom: 16 }}>O scaling causa um rolling restart sem downtime — o Atlas atualiza os nós um a um.</Banner>
      <div className="row" style={{ marginBottom: 18 }}>
        <ClusterPicker clusters={clusters} value={sel} onChange={setSel} />
      </div>

      <KpiGrid>
        <Kpi label="Cluster" value={sel.cluster_name} color="#0498EC" />
        <Kpi label="Tier Atual" value={sel.tier} color="#00A35C" />
        <Kpi label="Região" value={sel.region_pretty} color="#889397" />
        <Kpi label="Custo Est./Mês" value={`R$ ${sel.cost_brl.toLocaleString('pt-BR')}`} delta={`≈ USD ${sel.cost_usd.toLocaleString('pt-BR')}`} />
      </KpiGrid>

      {rec && rec.headline && (
        <Banner variant={recColor} style={{ marginBottom: 16 }}>
          <b>{rec.headline}</b>
          <ul style={{ margin: '6px 0 0', paddingLeft: 18 }}>
            {rec.reasons.map((r, i) => <li key={i}>{r.replace(/\*\*/g, '')}</li>)}
          </ul>
        </Banner>
      )}

      <Section title="Carga 24h" badge={sel.cluster_name} />
      <MiniChart series={series} height={280} />

      <Section title="Alterar Tier" />
      <div className="row">
        <select className="mono" value={newTier} onChange={e => setNewTier(e.target.value)}
          style={{ background: '#00271C', color: '#E3FCF7', border: '1px solid rgba(0,237,100,0.22)', borderRadius: 6, padding: '8px 12px' }}>
          {tiers.map(t => <option key={t} value={t}>{t}</option>)}
        </select>
        <Button variant="primary" disabled={newTier === sel.tier} onClick={doScale}>🚀 Executar Scaling</Button>
      </div>
      {msg && <Banner variant={msg.ok ? 'success' : 'danger'} style={{ marginTop: 14 }}>{msg.t}</Banner>}
    </>
  )
}

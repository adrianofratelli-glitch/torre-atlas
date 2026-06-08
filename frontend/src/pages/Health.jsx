import { useState } from 'react'
import { H1 } from '@leafygreen-ui/typography'
import Button from '@leafygreen-ui/button'
import Banner from '@leafygreen-ui/banner'
import { KpiGrid, Kpi, Section, Empty } from '../components.jsx'
import { getHealth } from '../api.js'
import { ClusterPicker } from './_picker.jsx'

export default function Health({ clusters }) {
  const [sel, setSel] = useState(clusters[0])
  const [hs, setHs] = useState(null)
  const [busy, setBusy] = useState(false)

  const calc = async () => {
    setBusy(true); setHs(null)
    try { setHs(await getHealth(sel.project_id, sel.cluster_name, sel.status, sel.mongo_version)) }
    finally { setBusy(false) }
  }

  return (
    <>
      <div className="page-head"><H1 style={{ color: '#E3FCF7' }}>Health Score</H1></div>
      <div className="row" style={{ marginBottom: 18 }}>
        <ClusterPicker clusters={clusters} value={sel} onChange={setSel} />
        <Button variant="primary" onClick={calc} disabled={busy}>{busy ? 'Calculando…' : '❤️ Calcular Health Score'}</Button>
      </div>

      {!hs && <Empty icon="🏥" title="Avalie a saúde do cluster" hint="Clique em Calcular Health Score para gerar uma nota de 0–100, combinando Performance Advisor, slow queries, status e versão do MongoDB." />}
      {hs && (
        <>
          <KpiGrid>
            <Kpi label="Health Score" value={`${hs.score}/100`} color={hs.color} />
            <Kpi label="Grade" value={hs.grade} color={hs.color} />
            <Kpi label="PA Sugestões" value={hs.n_pa} color={hs.n_pa ? '#FFC010' : '#00ED64'} />
            <Kpi label="Slow Queries" value={hs.n_sq} color={hs.n_sq ? '#FF6960' : '#00ED64'} />
          </KpiGrid>
          <Section title="Penalizações" />
          {hs.issues.length === 0
            ? <Banner variant="success">Nenhuma penalização — cluster saudável!</Banner>
            : hs.issues.map((it, i) => <Banner key={i} variant="warning" style={{ marginBottom: 8 }}>{it}</Banner>)}
        </>
      )}
    </>
  )
}

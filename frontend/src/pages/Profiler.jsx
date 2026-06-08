import { useState } from 'react'
import { H1 } from '@leafygreen-ui/typography'
import Button from '@leafygreen-ui/button'
import Banner from '@leafygreen-ui/banner'
import { KpiGrid, Kpi, Section, Empty } from '../components.jsx'
import { getSlow } from '../api.js'
import { ClusterPicker } from './_picker.jsx'

const PLAN = { COLLSCAN: '🔴 COLLSCAN', IXSCAN: '🟢 IXSCAN', FETCH: '🟡 FETCH', SORT: '🟠 SORT', IDHACK: '🟢 IDHACK' }

export default function Profiler({ clusters }) {
  const [sel, setSel] = useState(clusters[0])
  const [rows, setRows] = useState(null)
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState(null)

  const load = async () => {
    setBusy(true); setErr(null); setRows(null)
    try {
      const data = await getSlow(sel.project_id, sel.cluster_name)
      const list = (data.slowQueries || []).map(q => {
        let attr = {}
        try { attr = JSON.parse(q.line || '{}').attr || {} } catch {}
        let plan = attr.planSummary || '—'
        for (const k of Object.keys(PLAN)) if (String(plan).includes(k)) { plan = PLAN[k]; break }
        return { ns: q.namespace || 'N/A', plan, dur: attr.durationMillis || 0, docs: attr.docsExamined ?? '—', ret: attr.nreturned ?? '—' }
      }).sort((a, b) => b.dur - a.dur)
      setRows(list)
    } catch (e) { setErr(e?.response?.data?.detail || e.message) }
    finally { setBusy(false) }
  }

  const collscans = rows?.filter(r => String(r.plan).includes('COLLSCAN')).length || 0
  const worst = rows?.length ? Math.max(...rows.map(r => r.dur)) : 0
  const avg = rows?.length ? Math.round(rows.reduce((s, r) => s + r.dur, 0) / rows.length) : 0

  return (
    <>
      <div className="page-head"><H1 style={{ color: '#E3FCF7' }}>Query Profiler</H1></div>
      <div className="row" style={{ marginBottom: 18 }}>
        <ClusterPicker clusters={clusters} value={sel} onChange={setSel} />
        <Button variant="primary" onClick={load} disabled={busy}>{busy ? 'Buscando…' : '🔍 Carregar Slow Queries'}</Button>
      </div>

      {err && <Banner variant="danger">{err}</Banner>}
      {!rows && !err && <Empty icon="🔍" title="Investigue as queries lentas" hint="Clique em Carregar Slow Queries para ver as operações mais lentas com plano de execução, documentos examinados e latência." />}
      {rows && rows.length === 0 && <Banner variant="success">Nenhuma slow query em {sel.cluster_name}.</Banner>}
      {rows && rows.length > 0 && (
        <>
          <KpiGrid>
            <Kpi label="Slow Queries" value={rows.length} color="#FFC010" />
            <Kpi label="COLLSCANs" value={collscans} delta={collscans ? 'sem índice' : '✓ nenhum'} color={collscans ? '#FF4444' : '#00ED64'} />
            <Kpi label="Pior Latência" value={`${worst.toLocaleString('pt-BR')}ms`} color="#FF6960" />
            <Kpi label="Latência Média" value={`${avg.toLocaleString('pt-BR')}ms`} color="#00A35C" />
          </KpiGrid>
          <Section title="Operações Lentas" />
          <table className="mdb">
            <thead><tr><th>Namespace</th><th>Plano</th><th>Duração</th><th>Docs Examinados</th><th>Retornados</th></tr></thead>
            <tbody>
              {rows.map((r, i) => (
                <tr key={i}>
                  <td className="mono" style={{ color: '#00ED64' }}>{r.ns}</td>
                  <td>{r.plan}</td>
                  <td className="mono">{r.dur.toLocaleString('pt-BR')}ms</td>
                  <td className="mono" style={{ color: '#889397' }}>{typeof r.docs === 'number' ? r.docs.toLocaleString('pt-BR') : r.docs}</td>
                  <td className="mono" style={{ color: '#889397' }}>{r.ret}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {collscans > 0 && <Banner variant="info" style={{ marginTop: 14 }}>💡 Queries com 🔴 COLLSCAN varrem a collection inteira — veja a aba Performance Advisor para os índices recomendados.</Banner>}
        </>
      )}
    </>
  )
}

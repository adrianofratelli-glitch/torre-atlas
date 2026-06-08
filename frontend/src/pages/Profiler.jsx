import { useState, useMemo } from 'react'
import { H1 } from '@leafygreen-ui/typography'
import Button from '@leafygreen-ui/button'
import Banner from '@leafygreen-ui/banner'
import Badge from '@leafygreen-ui/badge'
import { KpiGrid, Kpi, Section, Empty } from '../components.jsx'
import { getSlow, explainQuery } from '../api.js'
import { ClusterPicker } from './_picker.jsx'

const PLAN = { COLLSCAN: '🔴 COLLSCAN', IXSCAN: '🟢 IXSCAN', FETCH: '🟡 FETCH', SORT: '🟠 SORT', IDHACK: '🟢 IDHACK' }
const WRITE_OPS = ['insert', 'update', 'remove', 'delete', 'findAndModify']

function classify(attr) {
  const t = (attr.type || '').toLowerCase()
  const cmd = attr.command || {}
  const op = t || Object.keys(cmd)[0] || 'query'
  const isWrite = WRITE_OPS.some(w => op.includes(w))
  return { op, kind: isWrite ? 'write' : 'read' }
}

export default function Profiler({ clusters, config }) {
  const [sel, setSel] = useState(clusters[0])
  const [rows, setRows] = useState(null)
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState(null)
  const [sort, setSort] = useState('dur')       // dur | count
  const [filter, setFilter] = useState('all')   // all | read | write | collscan
  const [explain, setExplain] = useState({})    // key -> result/loading

  const load = async () => {
    setBusy(true); setErr(null); setRows(null); setExplain({})
    try {
      const data = await getSlow(sel.project_id, sel.cluster_name)
      // Agrupa por shape (namespace + plano + operação) para contar execuções
      const map = {}
      for (const q of (data.slowQueries || [])) {
        let attr = {}
        try { attr = JSON.parse(q.line || '{}').attr || {} } catch {}
        const { op, kind } = classify(attr)
        let plan = attr.planSummary || '—'
        for (const k of Object.keys(PLAN)) if (String(plan).includes(k)) { plan = PLAN[k]; break }
        const ns = q.namespace || 'N/A'
        const key = `${ns}|${plan}|${op}`
        if (!map[key]) map[key] = { ns, plan, op, kind, count: 0, totalDur: 0, maxDur: 0, docs: 0, ret: 0, filter: attr.command?.filter || attr.command?.q || {} }
        const r = map[key]
        r.count++; r.totalDur += attr.durationMillis || 0
        r.maxDur = Math.max(r.maxDur, attr.durationMillis || 0)
        r.docs = Math.max(r.docs, attr.docsExamined || 0)
        r.ret = Math.max(r.ret, attr.nreturned || 0)
      }
      setRows(Object.values(map).map(r => ({ ...r, avgDur: Math.round(r.totalDur / r.count) })))
    } catch (e) { setErr(e?.response?.data?.detail || e.message) }
    finally { setBusy(false) }
  }

  const filtered = useMemo(() => {
    if (!rows) return []
    let r = rows
    if (filter === 'read') r = r.filter(x => x.kind === 'read')
    if (filter === 'write') r = r.filter(x => x.kind === 'write')
    if (filter === 'collscan') r = r.filter(x => String(x.plan).includes('COLLSCAN'))
    return [...r].sort((a, b) => sort === 'count' ? b.count - a.count : b.maxDur - a.maxDur)
  }, [rows, sort, filter])

  const runExplain = async (r) => {
    const key = `${r.ns}|${r.op}`
    setExplain(e => ({ ...e, [key]: { loading: true } }))
    try {
      const res = await explainQuery(r.ns, r.filter || {})
      setExplain(e => ({ ...e, [key]: res }))
    } catch (e) {
      setExplain(prev => ({ ...prev, [key]: { error: e?.response?.data?.detail || e.message } }))
    }
  }

  const collscans = rows?.filter(r => String(r.plan).includes('COLLSCAN')).reduce((s, r) => s + r.count, 0) || 0
  const totalExec = rows?.reduce((s, r) => s + r.count, 0) || 0
  const worst = rows?.length ? Math.max(...rows.map(r => r.maxDur)) : 0

  return (
    <>
      <div className="page-head"><H1 style={{ color: '#E3FCF7' }}>Query Profiler</H1></div>
      <div className="row" style={{ marginBottom: 18 }}>
        <ClusterPicker clusters={clusters} value={sel} onChange={setSel} />
        <Button variant="primary" onClick={load} disabled={busy}>{busy ? 'Buscando…' : '🔍 Carregar Slow Queries'}</Button>
      </div>

      {err && <Banner variant="danger">{err}</Banner>}
      {!rows && !err && <Empty icon="🔍" title="Investigue as queries lentas" hint="Carregue as slow queries para ver shapes agrupados por execução, tipo leitura/escrita, plano, e rodar explain real." />}
      {rows && rows.length === 0 && <Banner variant="success">Nenhuma slow query em {sel.cluster_name}.</Banner>}
      {rows && rows.length > 0 && (
        <>
          <KpiGrid>
            <Kpi label="Query Shapes" value={rows.length} color="#FFC010" />
            <Kpi label="Execuções Lentas" value={totalExec.toLocaleString('pt-BR')} color="#0498EC" />
            <Kpi label="COLLSCANs" value={collscans} delta={collscans ? 'sem índice' : '✓ nenhum'} color={collscans ? '#FF4444' : '#00ED64'} />
            <Kpi label="Pior Latência" value={`${worst.toLocaleString('pt-BR')}ms`} color="#FF6960" />
          </KpiGrid>

          {/* Filtros + ordenação */}
          <div className="row" style={{ marginBottom: 12 }}>
            <span style={{ fontSize: 12, color: '#889397' }}>Filtrar:</span>
            {['all', 'read', 'write', 'collscan'].map(f => (
              <button key={f} onClick={() => setFilter(f)} className="chip" data-active={filter === f}>
                {f === 'all' ? 'Todas' : f === 'read' ? '📖 Leitura' : f === 'write' ? '✏️ Escrita' : '🔴 COLLSCAN'}
              </button>
            ))}
            <span className="spacer" />
            <span style={{ fontSize: 12, color: '#889397' }}>Ordenar:</span>
            <button onClick={() => setSort('dur')} className="chip" data-active={sort === 'dur'}>Latência</button>
            <button onClick={() => setSort('count')} className="chip" data-active={sort === 'count'}>Execuções</button>
          </div>

          <table className="mdb">
            <thead><tr><th>Namespace</th><th>Tipo</th><th>Plano</th><th>Execuções</th><th>Latência (máx/méd)</th><th>Docs Exam.</th><th></th></tr></thead>
            <tbody>
              {filtered.map((r, i) => {
                const key = `${r.ns}|${r.op}`
                const ex = explain[key]
                return (
                  <>
                    <tr key={i}>
                      <td className="mono" style={{ color: '#00ED64' }}>{r.ns}</td>
                      <td><Badge variant={r.kind === 'write' ? 'yellow' : 'blue'}>{r.kind === 'write' ? '✏️ ' + r.op : '📖 ' + r.op}</Badge></td>
                      <td>{r.plan}</td>
                      <td className="mono">{r.count.toLocaleString('pt-BR')}×</td>
                      <td className="mono">{r.maxDur.toLocaleString('pt-BR')} / {r.avgDur.toLocaleString('pt-BR')}ms</td>
                      <td className="mono" style={{ color: '#889397' }}>{r.docs.toLocaleString('pt-BR')}</td>
                      <td>{config.mongodb && <Button size="xsmall" onClick={() => runExplain(r)}>explain</Button>}</td>
                    </tr>
                    {ex && (
                      <tr key={i + 'e'}><td colSpan={7} style={{ background: '#001016' }}>
                        {ex.loading ? 'Rodando explain…' : ex.error ? <span style={{ color: '#FF6960' }}>{ex.error}</span> : (
                          <div className="mono" style={{ fontSize: 12, color: '#C3E7DD', display: 'flex', gap: 24, flexWrap: 'wrap' }}>
                            <span>stage: <b style={{ color: String(ex.index_used).includes('COLLSCAN') ? '#FF6960' : '#00ED64' }}>{ex.stage}</b></span>
                            <span>índice: {ex.index_used}</span>
                            <span>docs examinados: {ex.docs_examined}</span>
                            <span>retornados: {ex.n_returned}</span>
                            <span>tempo: {ex.exec_ms}ms</span>
                          </div>
                        )}
                      </td></tr>
                    )}
                  </>
                )
              })}
            </tbody>
          </table>
          {collscans > 0 && <Banner variant="info" style={{ marginTop: 14 }}>💡 As {collscans} execuções 🔴 COLLSCAN varrem a collection inteira — crie índices na aba Performance Advisor.</Banner>}
        </>
      )}
    </>
  )
}

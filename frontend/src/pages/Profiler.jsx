import { useState, useMemo } from 'react'
import { H1 } from '@leafygreen-ui/typography'
import Button from '@leafygreen-ui/button'
import Banner from '@leafygreen-ui/banner'
import Badge from '@leafygreen-ui/badge'
import { KpiGrid, Kpi, Section, Empty } from '../components.jsx'
import { getSlow } from '../api.js'
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
  const [open, setOpen] = useState(null)        // índice da linha expandida

  const load = async () => {
    setBusy(true); setErr(null); setRows(null); setOpen(null)
    try {
      const data = await getSlow(sel.project_id, sel.cluster_name)
      // Agrupa por shape (namespace + plano + operação) para contar execuções
      const map = {}
      for (const q of (data.slowQueries || [])) {
        let attr = {}
        try { attr = JSON.parse(q.line || '{}').attr || {} } catch {}
        const { op, kind } = classify(attr)
        const planRaw = attr.planSummary || '—'
        let plan = planRaw
        for (const k of Object.keys(PLAN)) if (String(planRaw).includes(k)) { plan = PLAN[k]; break }
        const ns = q.namespace || 'N/A'
        const key = `${ns}|${plan}|${op}`
        const cmd = attr.command || {}
        if (!map[key]) map[key] = {
          ns, plan, planRaw, op, kind, count: 0, totalDur: 0, maxDur: 0,
          docs: 0, keys: 0, ret: 0, yields: 0,
          filter: cmd.filter || cmd.q || cmd.pipeline || {},
          queryHash: attr.queryHash || '—',
        }
        const r = map[key]
        r.count++; r.totalDur += attr.durationMillis || 0
        r.maxDur = Math.max(r.maxDur, attr.durationMillis || 0)
        r.docs = Math.max(r.docs, attr.docsExamined || 0)
        r.keys = Math.max(r.keys, attr.keysExamined || 0)
        r.ret = Math.max(r.ret, attr.nreturned || 0)
        r.yields = Math.max(r.yields, attr.numYields || 0)
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
                const ratio = r.ret > 0 ? Math.round(r.docs / r.ret) : (r.docs > 0 ? r.docs : 0)
                const ratioBad = ratio >= 100
                return (
                  <>
                    <tr key={i}>
                      <td className="mono" style={{ color: '#00ED64' }}>
                        <div title={r.ns} style={{ maxWidth: 230, overflow: 'hidden',
                             textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{r.ns}</div>
                      </td>
                      <td>
                        <Badge variant={r.kind === 'write' ? 'yellow' : 'blue'}>
                          <span title={r.op} style={{ display: 'inline-block', maxWidth: 100, overflow: 'hidden',
                                  textOverflow: 'ellipsis', whiteSpace: 'nowrap', verticalAlign: 'bottom' }}>
                            {r.kind === 'write' ? '✏️ ' : '📖 '}{r.op}
                          </span>
                        </Badge>
                      </td>
                      <td>
                        <div title={r.planRaw} style={{ maxWidth: 130, overflow: 'hidden',
                             textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{r.plan}</div>
                      </td>
                      <td className="mono">{r.count.toLocaleString('pt-BR')}×</td>
                      <td className="mono">{r.maxDur.toLocaleString('pt-BR')} / {r.avgDur.toLocaleString('pt-BR')}ms</td>
                      <td className="mono" style={{ color: '#889397' }}>{r.docs.toLocaleString('pt-BR')}</td>
                      <td><Button size="xsmall" onClick={() => setOpen(open === i ? null : i)}>{open === i ? 'fechar' : '🔬 plano'}</Button></td>
                    </tr>
                    {open === i && (
                      <tr key={i + 'e'}><td colSpan={7} style={{ background: '#001016', padding: 16 }}>
                        <div style={{ fontSize: 11, color: '#5C6C75', textTransform: 'uppercase', letterSpacing: 1, marginBottom: 10 }}>Plano de execução capturado (slow query log)</div>
                        <div className="mono" style={{ fontSize: 12, color: '#C3E7DD', display: 'flex', gap: 28, flexWrap: 'wrap', marginBottom: 12 }}>
                          <span>plano: <b style={{ color: r.planRaw.includes('COLLSCAN') ? '#FF6960' : '#00ED64' }}>{r.planRaw}</b></span>
                          <span>docs examinados: <b>{r.docs.toLocaleString('pt-BR')}</b></span>
                          <span>keys examinados: <b>{r.keys.toLocaleString('pt-BR')}</b></span>
                          <span>retornados: <b>{r.ret.toLocaleString('pt-BR')}</b></span>
                          <span>yields: {r.yields}</span>
                          <span>queryHash: {r.queryHash}</span>
                        </div>
                        <div style={{ marginBottom: 10 }}>
                          <Badge variant={ratioBad ? 'red' : ratio > 10 ? 'yellow' : 'green'}>
                            Query Targeting: {ratio.toLocaleString('pt-BR')} docs escaneados por documento retornado
                          </Badge>
                          {ratioBad && <span style={{ fontSize: 12, color: '#FF6960', marginLeft: 10 }}>← índice provavelmente faltando</span>}
                        </div>
                        <div style={{ fontSize: 11, color: '#5C6C75', marginBottom: 4 }}>Query / comando:</div>
                        <pre style={{ margin: 0, maxHeight: 200 }}>{JSON.stringify(r.filter, null, 2)}</pre>
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

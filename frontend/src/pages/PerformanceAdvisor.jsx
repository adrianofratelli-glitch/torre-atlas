import { useState } from 'react'
import { H1, Body } from '@leafygreen-ui/typography'
import Button from '@leafygreen-ui/button'
import Banner from '@leafygreen-ui/banner'
import Card from '@leafygreen-ui/card'
import { Section, Empty } from '../components.jsx'
import { getPA, createIndex, streamAnalyze } from '../api.js'
import { ClusterPicker } from './_picker.jsx'

export default function PerformanceAdvisor({ clusters, config }) {
  const [sel, setSel] = useState(clusters[0])
  const [data, setData] = useState(null)
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState(null)
  const [analysis, setAnalysis] = useState('')

  const load = async () => {
    setBusy(true); setErr(null); setData(null); setAnalysis('')
    try { setData(await getPA(sel.project_id, sel.cluster_name)) }
    catch (e) { setErr(e?.response?.data?.detail || e.message) }
    finally { setBusy(false) }
  }

  const analyze = async () => {
    setAnalysis('')
    for await (const chunk of streamAnalyze(sel.project_id, sel.cluster_name)) setAnalysis(a => a + chunk)
  }

  const suggestions = data?.suggestedIndexes || []
  return (
    <>
      <div className="page-head"><H1 style={{ color: '#E3FCF7' }}>Performance Advisor</H1></div>
      <div className="row" style={{ marginBottom: 18 }}>
        <ClusterPicker clusters={clusters} value={sel} onChange={setSel} />
        <Button variant="primary" onClick={load} disabled={busy}>{busy ? 'Consultando…' : '🔍 Buscar Recomendações'}</Button>
      </div>

      {err && <Banner variant="danger">{err}</Banner>}
      {!data && !err && <Empty icon="⚡" title="Analise os índices de um cluster" hint="Selecione o cluster e clique em Buscar Recomendações para o Performance Advisor sugerir índices com base nos padrões de acesso reais." />}

      {data && suggestions.length === 0 && <Banner variant="success">Nenhuma recomendação para {sel.cluster_name} — cluster saudável!</Banner>}
      {data && suggestions.length > 0 && (
        <>
          <Banner variant="warning">{suggestions.length} índice(s) sugerido(s) para {sel.cluster_name}</Banner>
          <Section title="Índices Sugeridos" />
          {suggestions.map((idx, i) => {
            const ns = idx.namespace || 'N/A'
            const fields = (idx.index || []).map(k => `"${Object.keys(k)[0]}": ${Object.values(k)[0]}`).join(', ')
            const cmd = `db.${ns.split('.').pop()}.createIndex({ ${fields} })`
            return (
              <Card key={i} darkMode style={{ marginBottom: 12 }}>
                <Body weight="medium">#{i + 1} · {ns} · peso {Math.round((idx.weight || 0) * 100) / 100}</Body>
                <pre>{cmd}</pre>
                {config.mongodb && (
                  <Button size="small" onClick={async () => {
                    const r = await createIndex(ns, idx.index)
                    alert(r.result)
                  }}>▶ Executar Índice</Button>
                )}
              </Card>
            )
          })}
          <Button variant="primaryOutline" onClick={analyze} style={{ marginTop: 8 }}>🤖 Analisar com Claude</Button>
          {analysis && <Card darkMode style={{ marginTop: 12 }}><div style={{ whiteSpace: 'pre-wrap' }}>{analysis}</div></Card>}
        </>
      )}
    </>
  )
}

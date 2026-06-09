import { useState, useEffect } from 'react'
import { H1, H3, Body } from '@leafygreen-ui/typography'
import Button from '@leafygreen-ui/button'
import Banner from '@leafygreen-ui/banner'
import Card from '@leafygreen-ui/card'
import { KpiGrid, Kpi, Section, MiniChart, Empty } from '../components.jsx'
import { getScaling, getSeries, scaleCluster } from '../api.js'
import { ClusterPicker } from './_picker.jsx'

export default function Scale({ clusters, config }) {
  const [sel, setSel] = useState(clusters[0])
  const [rec, setRec] = useState(null)
  const [series, setSeries] = useState(null)
  const [newTier, setNewTier] = useState(sel?.tier)
  const [msg, setMsg] = useState(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (!sel) return
    setRec(null); setSeries(null); setNewTier(sel.tier); setMsg(null); setLoading(true)
    Promise.all([
      getScaling(sel.project_id, sel.cluster_name, sel.tier).then(setRec).catch(() => {}),
      getSeries(sel.project_id, sel.cluster_name).then(setSeries).catch(() => {}),
    ]).finally(() => setLoading(false))
  }, [sel])

  const usdBrl = config.usd_brl
  const pricing = config.pricing || {}
  const tiers = config.tiers?.dedicated || []

  if (!sel) return (
    <>
      <div className="page-head"><H1 style={{ color: '#E3FCF7' }}>Scale</H1></div>
      <Empty icon="📈" title="Nenhum cluster encontrado" hint="Verifique as credenciais do Atlas no servidor (.env) e recarregue a página." />
    </>
  )

  const curUsd = pricing[sel.tier] || 0
  const newUsd = pricing[newTier] || 0
  const deltaUsd = newUsd - curUsd
  const curIdx = tiers.indexOf(sel.tier), newIdx = tiers.indexOf(newTier)
  const direction = newIdx > curIdx ? '⬆️ Scale UP' : newIdx < curIdx ? '⬇️ Scale DOWN' : ''

  const doScale = async () => {
    try { const r = await scaleCluster(sel.project_id, sel.cluster_name, newTier); setMsg({ ok: true, t: `Scaling iniciado! Status: ${r.state}. O cluster entrará em UPDATING por alguns minutos.` }) }
    catch (e) { setMsg({ ok: false, t: e?.response?.data?.detail || e.message }) }
  }

  const recColor = rec?.severity === 'high' ? 'danger' : rec?.severity === 'med' ? 'warning' : 'success'
  return (
    <>
      <div className="page-head"><H1 style={{ color: '#E3FCF7' }}>Scale</H1></div>
      <div className="row" style={{ marginBottom: 16 }}>
        <ClusterPicker clusters={clusters} value={sel} onChange={setSel} />
      </div>

      <KpiGrid>
        <Kpi label="Cluster" value={sel.cluster_name} color="#0498EC" />
        <Kpi label="Tier Atual" value={sel.tier} color="#00A35C" />
        <Kpi label="Região" value={sel.region_pretty} color="#889397" />
        <Kpi label="Custo Atual/Mês" value={`R$ ${sel.cost_brl.toLocaleString('pt-BR')}`} delta={`≈ USD ${sel.cost_usd.toLocaleString('pt-BR')}`} />
      </KpiGrid>

      {/* ── Métricas-chave que regem o scaling: CPU · Memória · Storage ── */}
      <Section title="Métricas de Scaling" sub="as 3 dimensões que definem o tier" />
      {loading && <Body style={{ color: '#889397' }}>Analisando métricas do cluster…</Body>}
      {rec?.metrics && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 14, marginBottom: 18 }}>
          <MetricBar label="CPU" pct={rec.metrics.cpu_pct}
                     sub={`${rec.metrics.cpu_pct}%`} warn={75} crit={90} />
          <MetricBar label="Memória" pct={rec.metrics.mem_pct}
                     sub={`${rec.metrics.memory_used_gb}/${rec.metrics.mem_total_gb} GB · ${rec.metrics.mem_pct}%`} warn={75} crit={90} />
          <MetricBar label="Storage" pct={rec.metrics.disk_pct}
                     sub={`${rec.metrics.disk_pct}% do disco`} warn={70} crit={85} />
          <MetricBar label="Conexões" pct={rec.metrics.conn_pct}
                     sub={`${rec.metrics.connections} · ${rec.metrics.conn_pct}% do limite`} warn={60} crit={80} />
        </div>
      )}

      {/* ── Recomendação: por que escalar (ou não) ── */}
      <Section title="Recomendação Inteligente" sub="baseada em CPU · memória · storage · conexões reais" />
      {rec && rec.headline && (
        <Banner variant={recColor} style={{ marginBottom: 8 }}>
          <b>{rec.headline}</b>
          <ul style={{ margin: '8px 0 0', paddingLeft: 18 }}>
            {rec.reasons.map((r, i) => <li key={i} style={{ margin: '4px 0' }}>{r.replace(/\*\*/g, '')}</li>)}
          </ul>
        </Banner>
      )}
      {rec && rec.action === 'ok' && (
        <Body style={{ color: '#889397', fontSize: 13 }}>
          ✅ Sem necessidade imediata de scaling — você ainda pode simular cenários abaixo para planejar crescimento.
        </Body>
      )}

      <Section title="Carga 24h" badge={sel.cluster_name} />
      <MiniChart series={series} height={150} />

      {/* ── Simulador de tier com custo ── */}
      <Section title="Simular Mudança de Tier" />
      <Card darkMode>
        <div className="row" style={{ alignItems: 'flex-end', gap: 18 }}>
          <div>
            <div style={{ fontSize: 11, color: '#889397', marginBottom: 6 }}>Novo tier</div>
            <select className="mono" value={newTier} onChange={e => setNewTier(e.target.value)}
              style={{ background: '#001016', color: '#E3FCF7', border: '1px solid rgba(0,237,100,0.3)', borderRadius: 6, padding: '9px 14px', fontSize: 15 }}>
              {tiers.map(t => <option key={t} value={t}>{t}</option>)}
            </select>
          </div>
          {newTier !== sel.tier && (
            <>
              <div style={{ fontSize: 22, color: '#5C6C75' }}>→</div>
              <div>
                <div style={{ fontSize: 11, color: '#889397', marginBottom: 6 }}>{direction}</div>
                <div className="mono" style={{ fontSize: 20, fontWeight: 700, color: '#E3FCF7' }}>
                  R$ {Math.round(newUsd * usdBrl).toLocaleString('pt-BR')}<span style={{ fontSize: 12, color: '#889397' }}>/mês</span>
                </div>
              </div>
              <div>
                <div style={{ fontSize: 11, color: '#889397', marginBottom: 6 }}>Variação</div>
                <div className="mono" style={{ fontSize: 18, fontWeight: 700, color: deltaUsd >= 0 ? '#FF6960' : '#00ED64' }}>
                  {deltaUsd >= 0 ? '+' : ''}R$ {Math.round(deltaUsd * usdBrl).toLocaleString('pt-BR')}
                  <span style={{ fontSize: 11, color: '#889397' }}> ({deltaUsd >= 0 ? '+' : ''}USD {deltaUsd.toLocaleString('pt-BR')})</span>
                </div>
              </div>
              <div className="spacer" />
              <Button variant="primary" onClick={doScale}>🚀 Executar Scaling</Button>
            </>
          )}
        </div>
        <Banner variant="info" style={{ marginTop: 16 }}>
          O scaling faz um <b>rolling restart sem downtime</b> — o Atlas atualiza os nós um a um.
        </Banner>
      </Card>
      {msg && <Banner variant={msg.ok ? 'success' : 'danger'} style={{ marginTop: 14 }}>{msg.t}</Banner>}
    </>
  )
}

// Barra de métrica com cor por gravidade (verde → amarelo → vermelho)
function MetricBar({ label, pct, sub, warn = 75, crit = 90 }) {
  const v = Math.max(0, Math.min(100, pct || 0))
  const color = v >= crit ? '#F87171' : v >= warn ? '#FACC15' : '#00ED64'
  return (
    <div style={{ background: '#00271C', border: '1px solid rgba(255,255,255,0.06)',
                  borderTop: `3px solid ${color}`, borderRadius: '0 0 8px 8px', padding: '14px 16px' }}>
      <div style={{ fontSize: 10, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '1.2px',
                    color: '#5C6C75', marginBottom: 8 }}>{label}</div>
      <div className="mono" style={{ fontSize: 22, fontWeight: 700, color, lineHeight: 1 }}>{v}%</div>
      <div style={{ height: 6, background: '#001016', borderRadius: 3, overflow: 'hidden', margin: '8px 0 6px' }}>
        <div style={{ width: `${v}%`, height: '100%', background: color }} />
      </div>
      <div style={{ fontSize: 11, color: '#889397', fontFamily: "'IBM Plex Mono',monospace" }}>{sub}</div>
    </div>
  )
}

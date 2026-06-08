import { useState } from 'react'
import { H1, H3, Body } from '@leafygreen-ui/typography'
import Button from '@leafygreen-ui/button'
import Banner from '@leafygreen-ui/banner'
import Card from '@leafygreen-ui/card'
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

      {!hs && <Empty icon="🏥" title="Avalie a saúde do cluster" hint="Clique em Calcular Health Score para uma nota 0–100 com o detalhamento de cada componente e como melhorar." />}
      {hs && (
        <>
          {/* Nota grande + grade */}
          <div className="row" style={{ gap: 24, alignItems: 'stretch', marginBottom: 8 }}>
            <Card darkMode style={{ textAlign: 'center', minWidth: 200 }}>
              <div className="mono" style={{ fontSize: 64, fontWeight: 800, color: hs.color, lineHeight: 1 }}>{hs.grade}</div>
              <div className="mono" style={{ fontSize: 20, color: hs.color, marginTop: 6 }}>{hs.score}<span style={{ color: '#5C6C75', fontSize: 14 }}>/100</span></div>
              <div style={{ fontSize: 12, color: '#889397', marginTop: 8 }}>{interp(hs.grade)}</div>
            </Card>
            <Card darkMode style={{ flex: 1 }}>
              <div style={{ fontSize: 11, color: '#5C6C75', textTransform: 'uppercase', letterSpacing: 1.2, marginBottom: 12, fontWeight: 700 }}>Composição do Score</div>
              {hs.components.map((c, i) => (
                <div key={i} style={{ marginBottom: 10 }}>
                  <div className="row" style={{ justifyContent: 'space-between', marginBottom: 4 }}>
                    <span style={{ fontSize: 13 }}>{c.ok ? '🟢' : '🔴'} {c.label} <span style={{ color: '#5C6C75', fontSize: 11 }}>· {c.detail}</span></span>
                    <span className="mono" style={{ fontSize: 12, color: c.earned === c.max ? '#00ED64' : '#FFC010' }}>{c.earned}/{c.max} pts</span>
                  </div>
                  <div style={{ height: 6, background: '#001016', borderRadius: 3, overflow: 'hidden' }}>
                    <div style={{ width: `${(c.earned / c.max) * 100}%`, height: '100%', background: c.earned === c.max ? '#00ED64' : '#FFC010' }} />
                  </div>
                </div>
              ))}
            </Card>
          </div>

          {/* Como melhorar */}
          <Section title="Como melhorar a nota" badge={`+${hs.tips.reduce((s, t) => s + t.gain, 0)} pts possíveis`} badge_color="green" />
          {hs.tips.map((t, i) => (
            <Banner key={i} variant={t.gain > 0 ? 'warning' : 'success'} style={{ marginBottom: 8 }}>
              {t.gain > 0 && <b className="mono" style={{ color: '#00ED64', marginRight: 8 }}>+{t.gain} pts</b>}
              {t.text.replace(/\*\*/g, '')}
            </Banner>
          ))}
        </>
      )}
    </>
  )
}

const interp = (g) => ({
  A: 'Excelente — nenhuma ação necessária', B: 'Saudável — pequenas melhorias possíveis',
  C: 'Atenção — otimizações importantes', D: 'Problemas significativos', F: 'Crítico — intervenção urgente',
}[g] || '')

import { H1 } from '@leafygreen-ui/typography'
import { KpiGrid, Kpi, Section } from '../components.jsx'

export default function FinOps({ clusters }) {
  const totalUsd = clusters.reduce((s, c) => s + c.cost_usd, 0)
  const totalBrl = clusters.reduce((s, c) => s + c.cost_brl, 0)
  const avg = clusters.length ? totalBrl / clusters.length : 0
  const top = clusters.reduce((a, b) => (b.cost_usd > (a?.cost_usd || 0) ? b : a), null)

  return (
    <>
      <div className="page-head"><H1 style={{ color: '#E3FCF7' }}>FinOps</H1></div>
      <KpiGrid>
        <Kpi label="Total USD/Mês" value={`$${fmt(totalUsd)}`} delta="estimativa AWS us-east-1" />
        <Kpi label="Total BRL/Mês" value={`R$ ${fmt(totalBrl)}`} color="#00A35C" />
        <Kpi label="Média/Cluster" value={`R$ ${fmt(avg)}`} color="#0498EC" />
        <Kpi label="Maior Custo" value={top?.cluster_name || '—'} color="#FFC010" />
      </KpiGrid>
      <Section title="Custo por Cluster" />
      <table className="mdb">
        <thead><tr><th>Projeto</th><th>Cluster</th><th>Tier</th><th>Região</th><th style={{ textAlign: 'right' }}>USD/Mês</th><th style={{ textAlign: 'right' }}>BRL/Mês</th></tr></thead>
        <tbody>
          {[...clusters].sort((a, b) => b.cost_usd - a.cost_usd).map(c => (
            <tr key={c.cluster_name}>
              <td>{c.project_name}</td>
              <td className="mono" style={{ color: '#00ED64' }}>{c.cluster_name}</td>
              <td className="mono">{c.tier}</td>
              <td style={{ color: '#889397' }}>{c.region_pretty}</td>
              <td className="mono" style={{ textAlign: 'right' }}>${fmt(c.cost_usd)}</td>
              <td className="mono" style={{ textAlign: 'right', color: '#00ED64' }}>R${fmt(c.cost_brl)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </>
  )
}
const fmt = (n) => Math.round(n).toLocaleString('pt-BR')

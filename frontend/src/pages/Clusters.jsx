import { H1 } from '@leafygreen-ui/typography'
import Badge from '@leafygreen-ui/badge'
import { Section, StatusDot } from '../components.jsx'

export default function Clusters({ clusters }) {
  return (
    <>
      <div className="page-head"><H1 style={{ color: '#fafafa' }}>Clusters da Organização</H1></div>
      <Section title="Frota" badge={`${clusters.length} cluster(s)`} />
      <table className="mdb">
        <thead>
          <tr><th>Projeto</th><th>Cluster</th><th>Tier</th><th>Região</th><th>Status</th><th>MongoDB</th><th>Tipo</th><th style={{ textAlign: 'right' }}>Custo/Mês</th></tr>
        </thead>
        <tbody>
          {clusters.map(c => (
            <tr key={c.cluster_name}>
              <td>{c.project_name}</td>
              <td className="mono" style={{ color: '#00ED64' }}>{c.cluster_name}</td>
              <td><Badge variant="blue">{c.tier}</Badge></td>
              <td style={{ color: '#7fa8bc' }}>{c.region_pretty}</td>
              <td><span className="row" style={{ gap: 6 }}><StatusDot status={c.status} /><span className="mono" style={{ fontSize: 12 }}>{c.status}</span></span></td>
              <td className="mono" style={{ color: '#7fa8bc' }}>{c.mongo_version}</td>
              <td className="mono" style={{ color: '#7fa8bc' }}>{c.cluster_type}</td>
              <td className="mono" style={{ textAlign: 'right' }}>${fmt(c.cost_usd)} <span style={{ color: '#5f869e' }}>/</span> <span style={{ color: '#00ED64' }}>R${fmt(c.cost_brl)}</span></td>
            </tr>
          ))}
        </tbody>
      </table>
    </>
  )
}
const fmt = (n) => Math.round(n).toLocaleString('pt-BR')

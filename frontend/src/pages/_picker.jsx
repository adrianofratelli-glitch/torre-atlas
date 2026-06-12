// Seletor de cluster reutilizável (select nativo estilizado MongoDB)
export function ClusterPicker({ clusters, value, onChange }) {
  return (
    <select
      className="mono"
      value={value?.cluster_name || ''}
      onChange={e => onChange(clusters.find(c => c.cluster_name === e.target.value))}
      style={{
        background: '#003345', color: '#fafafa', border: '1px solid rgba(0,237,100,0.25)',
        borderRadius: 6, padding: '8px 12px', fontSize: 13, minWidth: 220,
      }}
    >
      {clusters.map(c => (
        <option key={c.cluster_name} value={c.cluster_name}>
          {c.project_name} / {c.cluster_name} ({c.tier})
        </option>
      ))}
    </select>
  )
}

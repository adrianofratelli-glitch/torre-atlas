import { useState, useRef, useEffect } from 'react'
import { H1, Body } from '@leafygreen-ui/typography'
import Button from '@leafygreen-ui/button'
import TextInput from '@leafygreen-ui/text-input'
import Banner from '@leafygreen-ui/banner'
import { Section } from '../components.jsx'
import { streamChat } from '../api.js'
import { ClusterPicker } from './_picker.jsx'

const SUGGESTIONS = [
  'Quais índices estão sendo sugeridos para o cluster e por quê?',
  'Quando devo usar sharding vs fazer scale up do tier?',
  'Explique o Bucket Pattern para séries temporais financeiras',
  'Quais indicadores mostram que meu cluster precisa de scale up?',
]

export default function Chat({ clusters, config }) {
  const [ctx, setCtx] = useState(null)
  const [msgs, setMsgs] = useState([])
  const [input, setInput] = useState('')
  const [busy, setBusy] = useState(false)
  const endRef = useRef(null)

  useEffect(() => { endRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [msgs])

  const send = async (text) => {
    if (!text.trim() || busy) return
    const next = [...msgs, { role: 'user', content: text }]
    setMsgs(next); setInput(''); setBusy(true)
    let acc = ''
    setMsgs([...next, { role: 'assistant', content: '' }])
    try {
      for await (const chunk of streamChat(next, ctx?.project_id, ctx?.cluster_name)) {
        acc += chunk
        setMsgs([...next, { role: 'assistant', content: acc }])
      }
    } finally { setBusy(false) }
  }

  if (!config.anthropic) return <><div className="page-head"><H1 style={{ color: '#E3FCF7' }}>AI Chat</H1></div><Banner variant="warning">Configure a ANTHROPIC_API_KEY no servidor (.env) para usar o chat.</Banner></>

  return (
    <>
      <div className="page-head"><H1 style={{ color: '#E3FCF7' }}>AI Chat — MongoDB Expert</H1></div>
      <div className="row" style={{ marginBottom: 8 }}>
        <Body style={{ color: '#889397' }}>Contexto:</Body>
        <select className="mono" value={ctx?.cluster_name || ''} onChange={e => setCtx(clusters.find(c => c.cluster_name === e.target.value) || null)}
          style={{ background: '#00271C', color: '#E3FCF7', border: '1px solid rgba(0,237,100,0.22)', borderRadius: 6, padding: '6px 10px' }}>
          <option value="">Sem contexto (MongoDB geral)</option>
          {clusters.map(c => <option key={c.cluster_name} value={c.cluster_name}>{c.cluster_name}</option>)}
        </select>
        {ctx && <span style={{ fontSize: 12, color: '#00ED64' }}>📎 enriquecido com métricas de {ctx.cluster_name}</span>}
      </div>

      {msgs.length === 0 && (
        <>
          <Section title="Sugestões" />
          <div className="row">
            {SUGGESTIONS.map((s, i) => <Button key={i} size="small" onClick={() => send(s)}>{s}</Button>)}
          </div>
        </>
      )}

      <div style={{ margin: '18px 0' }}>
        {msgs.map((m, i) => (
          <div key={i} className={`chat-msg ${m.role}`}>
            <div style={{ fontSize: 11, color: '#5C6C75', marginBottom: 4 }}>{m.role === 'user' ? 'Você' : 'Claude'}</div>
            <div style={{ whiteSpace: 'pre-wrap' }}>{m.content || '▌'}</div>
          </div>
        ))}
        <div ref={endRef} />
      </div>

      <div className="row">
        <div style={{ flex: 1 }}>
          <TextInput aria-label="Mensagem" placeholder="Pergunte sobre MongoDB, performance, indexação, Atlas…"
            value={input} onChange={e => setInput(e.target.value)}
            onKeyDown={e => { if (e.key === 'Enter') send(input) }} darkMode />
        </div>
        <Button variant="primary" onClick={() => send(input)} disabled={busy}>Enviar</Button>
      </div>
    </>
  )
}

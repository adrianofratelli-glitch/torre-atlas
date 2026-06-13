import { useState, useRef, useEffect, memo } from 'react'
import { H1 } from '@leafygreen-ui/typography'
import Button from '@leafygreen-ui/button'
import TextInput from '@leafygreen-ui/text-input'
import Banner from '@leafygreen-ui/banner'
import Badge from '@leafygreen-ui/badge'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Leaf } from '../components.jsx'
import { streamChat, listConversations, getConversation, deleteConversation } from '../api.js'

const SUGGESTIONS = [
  'Quais indicadores mostram que meu cluster precisa de scale up?',
  'Quando devo usar sharding vs subir o tier do cluster?',
  'Explique o Bucket Pattern para séries temporais financeiras',
  'Como o WiredTiger usa o cache e por que isso afeta a performance?',
]

// memo: during streaming only the last bubble changes — the previous ones don't
// re-parse Markdown on every received chunk
const Bubble = memo(function Bubble({ m }) {
  return (
    <div className={`bubble ${m.role}`}>
      <div className="bubble-avatar">{m.role === 'user' ? '🧑' : <Leaf size={18} />}</div>
      <div className="bubble-body">
        <div className="bubble-name">{m.role === 'user' ? 'Você' : 'Claude'}</div>
        {m.role === 'assistant'
          ? (m.content
              ? <div className="md"><ReactMarkdown remarkPlugins={[remarkGfm]}>{m.content}</ReactMarkdown></div>
              : <span style={{ color: '#00ED64' }}>▌ pensando…</span>)
          : <div style={{ whiteSpace: 'pre-wrap' }}>{m.content}</div>}
      </div>
    </div>
  )
})

export default function Chat({ clusters, config }) {
  const [ctx, setCtx] = useState(null)
  const [msgs, setMsgs] = useState([])
  const [input, setInput] = useState('')
  const [busy, setBusy] = useState(false)
  const [convId, setConvId] = useState(null)
  const [history, setHistory] = useState([])
  const endRef = useRef(null)
  useEffect(() => { endRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [msgs])

  const refreshHistory = () => {
    if (config.mongodb) listConversations().then(setHistory).catch(() => {})
  }
  useEffect(refreshHistory, [config.mongodb])

  const openConversation = async (id) => {
    if (!id) { setMsgs([]); setConvId(null); return }
    try {
      const messages = await getConversation(id)
      setMsgs(messages.map(m => ({ role: m.role, content: m.content })))
      setConvId(id)
    } catch { /* conversation removed — list will be updated on the next refresh */ }
  }

  const removeConversation = async () => {
    if (!convId) return
    try { await deleteConversation(convId) } catch { /* already removed */ }
    setMsgs([]); setConvId(null); refreshHistory()
  }

  const send = async (text) => {
    if (!text.trim() || busy) return
    const next = [...msgs, { role: 'user', content: text }]
    setMsgs(next); setInput(''); setBusy(true)
    let acc = ''
    setMsgs([...next, { role: 'assistant', content: '' }])
    try {
      const onResponse = res => { const id = res.headers.get('X-Conversation-Id'); if (id) setConvId(id) }
      for await (const chunk of streamChat(next, ctx?.project_id, ctx?.cluster_name, convId, onResponse)) {
        acc += chunk
        setMsgs([...next, { role: 'assistant', content: acc }])
      }
      refreshHistory()
    } catch (e) {
      setMsgs([...next, { role: 'assistant', content: `❌ **Erro:** ${e.message}` }])
    } finally { setBusy(false) }
  }

  if (!config.anthropic) return <><div className="page-head"><H1>AI Chat</H1></div><Banner variant="warning">Configure a ANTHROPIC_API_KEY no servidor (.env) para usar o chat.</Banner></>

  return (
    <div style={{ maxWidth: 900, margin: '0 auto' }}>
      <div className="page-head" style={{ justifyContent: 'space-between' }}>
        <div className="row"><Leaf size={24} /><H1 style={{ color: '#fafafa' }}>MongoDB Expert</H1></div>
        <select className="mono" value={ctx?.cluster_name || ''} onChange={e => setCtx(clusters.find(c => c.cluster_name === e.target.value) || null)}
          style={{ background: '#003345', color: '#fafafa', border: '1px solid rgba(0,237,100,0.25)', borderRadius: 20, padding: '6px 14px', fontSize: 12 }}>
          <option value="">🌐 MongoDB geral</option>
          {clusters.map(c => <option key={c.cluster_name} value={c.cluster_name}>📎 {c.cluster_name}</option>)}
        </select>
      </div>

      {config.mongodb && (
        <div className="row" style={{ marginBottom: 12, gap: 8 }}>
          <select className="mono" value={convId || ''} onChange={e => openConversation(e.target.value)}
            style={{ background: '#003345', color: '#fafafa', border: '1px solid rgba(255,255,255,0.12)', borderRadius: 6, padding: '6px 10px', fontSize: 12, maxWidth: 420 }}>
            <option value="">🕘 Histórico — nova conversa</option>
            {history.map(h => <option key={h.id} value={h.id}>{h.title} · {h.msg_count} msg{h.cluster ? ` · 📎 ${h.cluster}` : ''}</option>)}
          </select>
          {convId && <Button size="xsmall" variant="dangerOutline" onClick={removeConversation}>🗑 Apagar</Button>}
        </div>
      )}

      {ctx && <div style={{ marginBottom: 12 }}><Badge variant="green">Contexto: métricas reais de {ctx.cluster_name}</Badge></div>}

      {msgs.length === 0 && (
        <div style={{ marginBottom: 20 }}>
          <div style={{ fontSize: 12, color: '#7fa8bc', marginBottom: 10 }}>💡 Comece com uma pergunta:</div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
            {SUGGESTIONS.map((s, i) => (
              <button key={i} onClick={() => send(s)} className="suggestion-card">{s}</button>
            ))}
          </div>
        </div>
      )}

      <div style={{ marginBottom: 18 }}>
        {msgs.map((m, i) => <Bubble key={i} m={m} />)}
        <div ref={endRef} />
      </div>

      <div className="row chat-input-bar">
        {/* hidden label: LeafyGreen validation requires label/aria-labelledby (does not accept aria-label) */}
        <span id="chat-input-label" style={{ display: 'none' }}>Mensagem para o chat</span>
        <div style={{ flex: 1 }}>
          <TextInput aria-labelledby="chat-input-label" placeholder="Pergunte sobre MongoDB Atlas, performance, indexação…"
            value={input} onChange={e => setInput(e.target.value)}
            onKeyDown={e => { if (e.key === 'Enter') send(input) }} darkMode />
        </div>
        <Button variant="primary" onClick={() => send(input)} disabled={busy}>{busy ? '…' : 'Enviar'}</Button>
      </div>
    </div>
  )
}

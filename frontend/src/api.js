// api.js — cliente axios para o backend FastAPI do Torre
import axios from 'axios'

const http = axios.create({ baseURL: '/api', timeout: 60000 })

export const getConfig      = () => http.get('/config').then(r => r.data)
export const getClusters    = () => http.get('/clusters').then(r => r.data.clusters)
export const getAlerts      = (ids) => http.get('/alerts', { params: { project_ids: ids.join(',') } }).then(r => r.data.open_alerts)
export const getInvoice     = () => http.get('/invoice').then(r => r.data.amount_usd)

const c = (pid, name) => `/cluster/${pid}/${encodeURIComponent(name)}`
export const getPA          = (pid, name) => http.get(`${c(pid, name)}/pa`).then(r => r.data)
export const getSlow        = (pid, name) => http.get(`${c(pid, name)}/slow`).then(r => r.data)
export const getMeasurements= (pid, name) => http.get(`${c(pid, name)}/measurements`).then(r => r.data)
export const getSeries      = (pid, name) => http.get(`${c(pid, name)}/series`).then(r => r.data)
export const getHealth      = (pid, name, status, mv) => http.get(`${c(pid, name)}/health`, { params: { status, mongo_version: mv } }).then(r => r.data)
export const getScaling     = (pid, name, tier) => http.get(`${c(pid, name)}/scaling`, { params: { tier } }).then(r => r.data)
export const scaleCluster   = (pid, name, newTier) => http.post(`${c(pid, name)}/scale`, { new_tier: newTier }).then(r => r.data)
export const createIndex    = (namespace, indexKeys) => http.post('/index', { namespace, index_keys: indexKeys }).then(r => r.data)
export const getFinops      = () => http.get('/finops').then(r => r.data)
export const explainQuery   = (namespace, filter) => http.post('/explain', { namespace, filter }).then(r => r.data)

// Histórico de conversas (persistido no Atlas — requer MONGODB_URI no backend)
export const listConversations  = (q = '') => http.get('/chat/conversations', { params: { q } }).then(r => r.data.conversations)
export const getConversation    = (id) => http.get(`/chat/conversations/${id}`).then(r => r.data.messages)
export const deleteConversation = (id) => http.delete(`/chat/conversations/${id}`).then(r => r.data)

// Streaming helpers (fetch para ler chunks de texto)
async function* streamPost(url, payload, onResponse) {
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  if (!res.ok || !res.body) {
    let detail = `Erro HTTP ${res.status}`
    try { detail = (await res.json()).detail || detail } catch { /* corpo não-JSON */ }
    throw new Error(detail)
  }
  onResponse?.(res)
  const reader = res.body.getReader()
  const dec = new TextDecoder()
  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    yield dec.decode(value, { stream: true })
  }
}

export const streamChat = (messages, project_id, cluster_name, conversation_id, onResponse) =>
  streamPost('/api/chat', { messages, project_id, cluster_name, conversation_id }, onResponse)

export const streamAnalyze = (project_id, cluster_name) =>
  streamPost('/api/analyze', { project_id, cluster_name })

// Baixa o relatório PDF (ou Markdown, se fpdf2 indisponível) da análise
export async function downloadReport(cluster_name, analysis, health_score = null, health_issues = null) {
  const res = await fetch('/api/report', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ cluster_name, analysis, health_score, health_issues }),
  })
  if (!res.ok) throw new Error(`Erro ao gerar relatório (HTTP ${res.status})`)
  const blob = await res.blob()
  const ext = (res.headers.get('Content-Type') || '').includes('pdf') ? 'pdf' : 'md'
  const a = document.createElement('a')
  a.href = URL.createObjectURL(blob)
  a.download = `torre-${cluster_name}.${ext}`
  a.click()
  URL.revokeObjectURL(a.href)
}

// api.js — cliente axios para o backend FastAPI do Maestro
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

// Streaming helpers (fetch para ler chunks de texto)
export async function* streamChat(messages, project_id, cluster_name) {
  const res = await fetch('/api/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ messages, project_id, cluster_name }),
  })
  const reader = res.body.getReader()
  const dec = new TextDecoder()
  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    yield dec.decode(value, { stream: true })
  }
}

export async function* streamAnalyze(project_id, cluster_name) {
  const res = await fetch('/api/analyze', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ project_id, cluster_name }),
  })
  const reader = res.body.getReader()
  const dec = new TextDecoder()
  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    yield dec.decode(value, { stream: true })
  }
}

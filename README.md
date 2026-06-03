# 🎯 Maestro — Atlas Control Plane

> Dashboard operacional para MongoDB Atlas com IA integrada via Claude (Anthropic).  
> Construído com Streamlit · Plotly · pymongo · LangGraph-inspired memory.

![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![Streamlit](https://img.shields.io/badge/Streamlit-1.35%2B-red)
![MongoDB](https://img.shields.io/badge/MongoDB-Atlas-green)
![Claude](https://img.shields.io/badge/Claude-Sonnet_4.6-orange)
![License](https://img.shields.io/badge/License-MIT-lightgrey)

---

## ✨ Funcionalidades

| Aba | Descrição |
|-----|-----------|
| 🏗️ **Clusters** | Visão geral de todos os clusters da org com status, tier, região, custo estimado e **alertas abertos** |
| ⚡ **Performance Advisor** | Índices sugeridos pelo Atlas PA com 1-click copy, execução direta via pymongo e **análise AI com Claude** |
| 🔍 **Query Profiler** | Slow queries com histograma de latência |
| 📈 **Scale** | Scale up/down com preview de custo antes de confirmar |
| 💰 **FinOps** | Estimativa de custo por cluster/projeto + simulador de cenários + **fatura pendente real do Atlas** |
| 📊 **Compare** | Comparativo side-by-side entre 2 clusters com radar chart |
| 🏥 **Health Score** | Score 0–100 por cluster com gauge chart e breakdown de penalizações |
| 💬 **AI Chat** | Chat conversacional com Claude usando contexto real do cluster (PA + slow queries + métricas de hardware) com histórico persistido no Atlas |

### Destaques técnicos
- **Métricas de hardware em tempo real** — CPU, memória, IOPS, conexões via Atlas Measurements API
- **Persistência no MongoDB Atlas** — histórico do AI Chat salvo como documentos com mensagens embedadas (showcase do Document Model)
- **Text Index com português** — busca de conversas passadas com stemming em PT-BR
- **Auto-refresh** configurável (30s / 60s / 120s)
- **Detecção de cluster PAUSED** via campo `paused` da API (independente do `stateName`)
- **get_primary() resiliente** — usa hash único do cluster extraído via `srvAddress` para evitar false match em nomes genéricos

---

## 🗂️ Estrutura do Projeto

```
maestro/
├── app.py              # UI principal — 8 abas Streamlit
├── atlas_client.py     # Client HTTP para Atlas Admin API v2
├── ai_agent.py         # Streaming Claude — análise one-shot + chat
├── chat_memory.py      # Persistência de conversas no Atlas (pymongo)
├── requirements.txt    # Dependências Python
├── run.sh              # Script de inicialização
├── .env.example        # Template de variáveis de ambiente
└── .gitignore
```

---

## 🚀 Instalação

### Pré-requisitos
- Python 3.10+
- Conta MongoDB Atlas (qualquer tier)
- API Key Anthropic

### 1. Clone o repositório

```bash
git clone https://github.com/adrianofratelli-glitch/maestro-atlas.git
cd maestro-atlas
```

### 2. Crie o ambiente virtual e instale as dependências

```bash
python3 -m venv venv
source venv/bin/activate       # Linux/macOS
# venv\Scripts\activate        # Windows

pip install -r requirements.txt
```

### 3. Configure as variáveis de ambiente

```bash
cp .env.example .env
```

Edite o `.env` com suas credenciais:

```bash
# macOS/Linux
open -a TextEdit .env
# ou
nano .env
```

```env
ATLAS_PUBLIC_KEY=sua_chave_publica
ATLAS_PRIVATE_KEY=sua_chave_privada
ATLAS_ORG_ID=seu_org_id
ANTHROPIC_API_KEY=sua_chave_anthropic
MONGODB_URI=mongodb+srv://user:pass@cluster.mongodb.net/  # opcional
```

### 4. Execute

```bash
# Via script (recomendado)
chmod +x run.sh && ./run.sh

# Ou diretamente
streamlit run app.py --server.port 8502
```

Acesse: **http://localhost:8502**

### Atalho (opcional)

```bash
echo 'alias maestro="cd ~/maestro && source venv/bin/activate && streamlit run app.py --server.port 8502"' >> ~/.zshrc
source ~/.zshrc
# Agora basta digitar: maestro
```

---

## 🔑 Configuração da API Key Atlas

1. Acesse **Atlas UI → Organization → Access Manager → API Keys**
2. Clique em **Create API Key**
3. Permissões mínimas necessárias:
   - `Organization Read Only`
   - `Project Cluster Manager` (para scaling)
   - `Project Read Only` (para métricas)
4. Adicione seu IP na **API Access List**
5. Copie as chaves para o `.env`

---

## 💰 Referência de Custos

Os valores de custo são **estimativas** baseadas em AWS us-east-1, 3-node replica set.  
Variam por cloud provider, região e configuração de storage.  
Fonte de referência: [atlas.mongodb.com/pricing](https://www.mongodb.com/pricing)

---

## 🧠 Arquitetura do AI Chat

```
┌─────────────────────────────────────────────────────┐
│                    AI Chat Tab                       │
│                                                      │
│  Contexto do Cluster                                 │
│  ┌──────────────────────────────────────────────┐   │
│  │ Atlas API → Cluster Info                     │   │
│  │          → Performance Advisor (PA)          │   │
│  │          → Slow Queries                      │   │
│  │          → Hardware Measurements             │   │
│  └──────────────────────────────────────────────┘   │
│           │                                          │
│           ▼                                          │
│  System Prompt (enriquecido com dados reais)         │
│           │                                          │
│           ▼                                          │
│  Claude Sonnet 4.6 (streaming)                       │
│           │                                          │
│           ▼                                          │
│  MongoDB Atlas ← Persistência do histórico           │
│  Collection: maestro.chat_history                    │
│  {                                                   │
│    cluster: "inter",                                 │
│    title: "Quais índices...",                        │
│    messages: [                        ← embedded     │
│      {role, content, elapsed_ms, ts}                 │
│    ]                                                 │
│  }                                                   │
└─────────────────────────────────────────────────────┘
```

### Por que MongoDB para persistência?
- **Document Model**: mensagens embedadas = 1 leitura por conversa, sem JOIN
- **`$push` atômico**: adiciona mensagem + atualiza `updated_at` em 1 operação
- **Text Index em português**: busca com stemming PT-BR nativo
- **Aggregation**: contagem de mensagens via `$size` sem query separada

---

## 🛠️ Desenvolvimento

### Variáveis de ambiente opcionais

| Variável | Descrição | Default |
|----------|-----------|---------|
| `ATLAS_PROJECT_ID` | Limita a um projeto específico | Todos os projetos |
| `MONGODB_URI` | Para criar índices e persistir chat | Desabilitado |

### Adicionando novos tabs

Cada tab segue o padrão:

```python
with tab_novo:
    st.subheader("Meu Tab")
    # Seleciona projeto e cluster
    _, proj_id, in_proj = project_selector("meu_prefix")
    cluster_name, row   = cluster_selector(in_proj, "meu_prefix")
    # Chama Atlas API
    data = client.get_alguma_coisa(proj_id, cluster_name)
    # Renderiza
    st.dataframe(data)
```

---

## 📊 Métricas de Hardware Disponíveis

Coletadas via `GET /groups/{groupId}/processes/{processId}/measurements`:

| Métrica | Descrição |
|---------|-----------|
| `SYSTEM_CPU_USER` + `SYSTEM_CPU_KERNEL` | CPU total (%) |
| `SYSTEM_MEMORY_USED` / `SYSTEM_MEMORY_AVAILABLE` | RAM (MB → GB) |
| `DISK_PARTITION_IOPS_READ/WRITE` | IOPS de disco |
| `CONNECTIONS` | Conexões ativas |
| `OPCOUNTER_INSERT/QUERY/UPDATE/DELETE` | Operações/segundo |
| `NETWORK_BYTES_IN/OUT` | Throughput de rede |

---

## 🤝 Contribuindo

Pull requests são bem-vindos! Para mudanças maiores, abra uma issue primeiro.

1. Fork o repositório
2. Crie sua branch: `git checkout -b feature/minha-feature`
3. Commit suas mudanças: `git commit -m 'feat: adiciona X'`
4. Push: `git push origin feature/minha-feature`
5. Abra um Pull Request

---

## 📄 Licença

MIT — veja [LICENSE](LICENSE) para detalhes.

---

*Construído com ❤️ para demonstrar o poder do MongoDB Atlas em aplicações financeiras de alto volume.*

"""
chat_memory.py — Chat history persistido no MongoDB Atlas
Showcases: Document Model · Embedded Arrays · Text Index · Aggregation

Coleção: maestro.chat_history
Estrutura:
{
  "_id": ObjectId,
  "cluster":    "inter",
  "title":      "Quais índices estão sendo sugeridos...",
  "messages": [
    { "role": "user",      "content": "...", "elapsed_ms": 0,    "ts": ISODate },
    { "role": "assistant", "content": "...", "elapsed_ms": 4100, "ts": ISODate }
  ],
  "created_at": ISODate,
  "updated_at": ISODate
}
"""

from datetime import datetime, timezone
from typing import List, Dict, Optional
from bson import ObjectId
from pymongo import MongoClient, TEXT, DESCENDING
from pymongo.collection import Collection

DB_NAME   = "maestro"
COLL_NAME = "chat_history"

_clients: dict = {}

# ── Conexão ───────────────────────────────────────────────────────────────────
def _get_collection(mongo_uri: str) -> Collection:
    if mongo_uri not in _clients:
        _clients[mongo_uri] = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
    return _clients[mongo_uri][DB_NAME][COLL_NAME]


def init_db(mongo_uri: str):
    """Garante índices na coleção. Idempotente."""
    coll = _get_collection(mongo_uri)

    existing = {idx["name"] for idx in coll.list_indexes()}

    # Text index para busca semântica simples nas mensagens e título
    if "text_search" not in existing:
        coll.create_index(
            [("title", TEXT), ("messages.content", TEXT)],
            name="text_search",
            default_language="portuguese",
        )

    # Índice para listagem recente (ordenação por updated_at)
    if "updated_at_desc" not in existing:
        coll.create_index([("updated_at", DESCENDING)], name="updated_at_desc")

    # Índice por cluster (filtro por contexto)
    if "cluster_idx" not in existing:
        coll.create_index([("cluster", DESCENDING)], name="cluster_idx")


# ── CRUD ──────────────────────────────────────────────────────────────────────
def new_conversation(mongo_uri: str, cluster: str = "") -> str:
    """Cria uma nova conversa. Retorna o _id como string."""
    now  = datetime.now(timezone.utc)
    doc  = {
        "cluster":    cluster,
        "title":      "Nova Conversa",
        "messages":   [],
        "created_at": now,
        "updated_at": now,
    }
    result = _get_collection(mongo_uri).insert_one(doc)
    return str(result.inserted_id)


def add_message(mongo_uri: str, conversation_id: str, role: str, content: str, elapsed_ms: int = 0):
    """
    Faz $push da mensagem no array embutido e $set no updated_at.
    Demonstra o poder do Document Model — sem tabela separada de mensagens.
    """
    now = datetime.now(timezone.utc)
    msg = {"role": role, "content": content, "elapsed_ms": elapsed_ms, "ts": now}

    update = {
        "$push": {"messages": msg},
        "$set":  {"updated_at": now},
    }

    # Auto-título: usa a 1ª mensagem do usuário
    if role == "user":
        title = content[:70] + ("…" if len(content) > 70 else "")
        # Só seta título se ainda for "Nova Conversa"
        _get_collection(mongo_uri).update_one(
            {"_id": ObjectId(conversation_id), "title": "Nova Conversa"},
            {"$set": {"title": title}},
        )

    _get_collection(mongo_uri).update_one(
        {"_id": ObjectId(conversation_id)},
        update,
    )


def load_messages(mongo_uri: str, conversation_id: str) -> List[Dict]:
    """Retorna as mensagens de uma conversa. Array embutido = 1 leitura."""
    doc = _get_collection(mongo_uri).find_one(
        {"_id": ObjectId(conversation_id)},
        {"messages": 1, "cluster": 1},
    )
    if not doc:
        return []
    return doc.get("messages", [])


def list_conversations(mongo_uri: str, cluster: str = "", limit: int = 25) -> List[Dict]:
    """
    Lista conversas recentes com contagem de mensagens via $size.
    Aggregation pipeline demonstra poder do MongoDB para analytics.
    """
    coll     = _get_collection(mongo_uri)
    match    = {"cluster": cluster} if cluster else {}
    pipeline = [
        {"$match": match},
        {"$project": {
            "cluster":    1,
            "title":      1,
            "updated_at": 1,
            "created_at": 1,
            "msg_count":  {"$size": "$messages"},
        }},
        {"$sort":  {"updated_at": -1}},
        {"$limit": limit},
    ]
    return [
        {**doc, "id": str(doc["_id"])}
        for doc in coll.aggregate(pipeline)
    ]


def search_conversations(mongo_uri: str, query: str, limit: int = 8) -> List[Dict]:
    """
    Full-text search via índice de texto do MongoDB.
    Demonstra Atlas Text Search sem Elasticsearch.
    """
    coll = _get_collection(mongo_uri)
    docs = coll.find(
        {"$text": {"$search": query}},
        {"title": 1, "cluster": 1, "updated_at": 1,
         "score": {"$meta": "textScore"},
         "msg_count": {"$size": "$messages"}},
    ).sort([("score", {"$meta": "textScore"})]).limit(limit)
    return [{**doc, "id": str(doc["_id"])} for doc in docs]


def delete_conversation(mongo_uri: str, conversation_id: str):
    """Deleta uma conversa por ID."""
    _get_collection(mongo_uri).delete_one({"_id": ObjectId(conversation_id)})


# ── Utilitários ───────────────────────────────────────────────────────────────
def format_relative_time(dt) -> str:
    """Converte datetime para texto relativo (ex: 'há 2h')."""
    try:
        if isinstance(dt, str):
            dt = datetime.fromisoformat(dt)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        delta = datetime.now(timezone.utc) - dt
        s     = int(delta.total_seconds())
        if s < 60:     return "agora"
        if s < 3600:   return f"há {s//60}min"
        if s < 86400:  return f"há {s//3600}h"
        if s < 604800: return f"há {s//86400}d"
        return dt.strftime("%d/%m/%Y")
    except Exception:
        return "—"

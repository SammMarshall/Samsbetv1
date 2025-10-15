# src/samsbet/core/cache.py

import redis
import json
import streamlit as st
from typing import Any

# Tenta buscar a URL do Redis a partir dos secrets do Hugging Face
redis_url = st.secrets.get("REDIS_URL")

redis_client = None
if redis_url:
    try:
        # Inicializa a conexão com o Redis
        redis_client = redis.from_url(redis_url)
        # Testa a conexão para garantir que está funcionando
        redis_client.ping()
        print("✅ Conectado ao cache Redis com sucesso!")
    except Exception as e:
        print(f"⚠️ Falha ao conectar ao Redis: {e}")
        redis_client = None

def get_from_cache(key: str) -> Any:
    """Busca um valor do cache Redis."""
    if not redis_client:
        return None

    try:
        cached_data = redis_client.get(key)
        if cached_data:
            # Desserializa a string JSON de volta para um objeto Python
            return json.loads(cached_data)
    except Exception as e:
        print(f"Erro ao ler do cache: {e}")
    return None

def set_to_cache(key: str, value: Any, ttl_seconds: int = 86400):
    """Salva um valor no cache Redis com um tempo de vida (TTL) de 24 horas."""
    if not redis_client:
        return

    try:
        # Serializa o objeto Python para uma string JSON antes de salvar
        redis_client.setex(key, ttl_seconds, json.dumps(value))
    except Exception as e:
        print(f"Erro ao salvar no cache: {e}")
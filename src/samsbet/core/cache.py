# src/samsbet/core/cache.py
import streamlit as st
import redis
import json
from typing import Any

@st.cache_resource
def connect_to_redis():
    """
    Cria e gerencia a conexão com o Redis.
    A anotação @st.cache_resource garante que esta função só rode uma vez por sessão.
    """
    redis_url = st.secrets.get("REDIS_URL")
    if not redis_url:
        st.warning("URL do Redis não configurada. O cache compartilhado está desativado.")
        return None
    
    try:
        client = redis.from_url(redis_url)
        client.ping()
        print("✅ Conexão com o cache Redis estabelecida com sucesso!")
        return client
    except Exception as e:
        st.error(f"⚠️ Falha crítica ao conectar ao Redis: {e}")
        return None

def get_from_cache(key: str) -> Any:
    """Busca um valor do cache Redis."""
    client = connect_to_redis()
    if not client:
        return None
    
    try:
        cached_data = client.get(key)
        if cached_data:
            return json.loads(cached_data)
    except Exception as e:
        print(f"Erro ao ler do cache: {e}")
    return None

def set_to_cache(key: str, value: Any, ttl_seconds: int = 14400):
    """Salva um valor no cache Redis."""
    client = connect_to_redis()
    if not client:
        return
    
    try:
        client.setex(key, ttl_seconds, json.dumps(value))
    except Exception as e:
        print(f"Erro ao salvar no cache: {e}")
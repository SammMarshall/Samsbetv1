import os
import json
import time
import hashlib
from typing import Any


def _get_cache_dir() -> str:
    base = os.environ.get("SAMSBET_CACHE_DIR")
    if not base:
        # Diretório padrão: pasta oculta na RAIZ DO PROJETO
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
        base = os.path.join(project_root, ".samsbet_cache")
    os.makedirs(base, exist_ok=True)
    return base


def _key_to_path(key: str) -> str:
    digest = hashlib.sha1(key.encode("utf-8")).hexdigest()
    return os.path.join(_get_cache_dir(), f"{digest}.json")


def get_from_disk_cache(key: str) -> Any:
    path = _key_to_path(key)
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            payload = json.load(f)
        expires_at = payload.get("expires_at", 0)
        if time.time() >= expires_at:
            try:
                os.remove(path)
            except OSError:
                pass
            return None
        return payload.get("data")
    except Exception:
        return None


def set_to_disk_cache(key: str, value: Any, ttl_seconds: int) -> None:
    path = _key_to_path(key)
    payload = {
        "expires_at": time.time() + max(1, int(ttl_seconds)),
        "data": value,
    }
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False)
    except Exception:
        pass



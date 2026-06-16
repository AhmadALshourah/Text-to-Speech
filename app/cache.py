"""In-memory TTL cache for synthesis results — IDEA-02.

Avoids calling edge-tts for identical (text, voice, rate, volume, ssml)
combinations within the TTL window.  Thread-safe via RLock.

100 entries × ~250 KB average ≈ 25 MB max RAM, acceptable for a small app.
"""

import hashlib
import threading
from typing import Optional

from cachetools import TTLCache

_cache: TTLCache = TTLCache(maxsize=100, ttl=1800)   # 30-minute TTL
_lock = threading.RLock()


def synthesis_key(text: str, voice: str, rate: str, volume: str, ssml: bool) -> str:
    """Deterministic SHA-256 key for a set of synthesis parameters."""
    raw = f"{text}\x00{voice}\x00{rate}\x00{volume}\x00{ssml}"
    return hashlib.sha256(raw.encode()).hexdigest()


def get(key: str) -> Optional[bytes]:
    with _lock:
        return _cache.get(key)


def put(key: str, audio: bytes) -> None:
    with _lock:
        _cache[key] = audio


def stats() -> dict:
    with _lock:
        return {"entries": len(_cache), "maxsize": _cache.maxsize, "ttl_seconds": _cache.ttl}

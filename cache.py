import time
import hashlib


_cache: dict = {}   # in-memory cache

class CacheManager:
    def __init__(self, ttl: int = 3600):
        self.ttl = ttl

    def make_key(self, target_url: str, params: dict) -> str:
        raw = f"{target_url}?{params}"
        return hashlib.md5(raw.encode()).hexdigest()

    def get(self, key: str):
        entry = _cache.get(key)
        if entry and time.time() - entry['ts'] < self.ttl:
            return entry

        if key in _cache:
            del _cache[key]     # expired - clean up
        return None

    def set(self, key: str, content: bytes, status_code: int, headers: dict, media_type: str):
        _cache[key] = {
            'ts': time.time(),
            'content': content,
            'status_code': status_code,
            'headers': headers,
            'media_type': media_type,
        }

    def clear(self) -> int:
        count = len(_cache)
        _cache.clear()
        return count

    def size(self) -> int:
        return len(_cache)

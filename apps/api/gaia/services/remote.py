"""Bounded, cached requests to fixed upstream services. No arbitrary URL proxy."""

from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from threading import RLock
from time import monotonic
import httpx

_cache = {}
_lock = RLock()


def cached(key, loader, ttl=900):
    with _lock:
        entry = _cache.get(key)
        if entry and monotonic() - entry[0] < ttl:
            return deepcopy(entry[1])
    value = loader()
    with _lock:
        if len(_cache) >= 256:
            _cache.pop(next(iter(_cache)))
        _cache[key] = (monotonic(), deepcopy(value))
    return value


def fetch(url, *, params=None, headers=None, as_text=False):
    with httpx.Client(
        timeout=20, follow_redirects=False, headers={"User-Agent": "GAIA/2.0 environmental-monitoring"}
    ) as client:
        response = client.get(url, params=params, headers=headers)
        response.raise_for_status()
        if len(response.content) > 16_000_000:
            raise ValueError("Upstream response exceeds limit")
        return response.text if as_text else response.json()


def gather(tasks):
    def run(item):
        name, loader = item
        try:
            return name, {"status": "ok", "data": loader()}
        except Exception as exc:
            status = exc.response.status_code if isinstance(exc, httpx.HTTPStatusError) else None
            return name, {
                "status": "unavailable",
                "message": f"Источник временно недоступен{f' (HTTP {status})' if status else ''}. Повторите позже.",
            }

    with ThreadPoolExecutor(max_workers=6) as pool:
        return dict(pool.map(run, tasks.items()))

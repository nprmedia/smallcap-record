"""Shared HTTP plumbing for the free backend: on-disk cache + polite rate limiting.

Raw API responses are cached under data_cache/ (gitignored) with a TTL from
config/backends.yaml, so repeated test runs don't hammer EDGAR/Tiingo.
EDGAR asks for <=10 requests/second and a descriptive User-Agent.
"""
from __future__ import annotations

import hashlib
import json
import os
import time

import requests

from ...config import ROOT


class CachedSession:
    def __init__(self, cache_cfg: dict, user_agent: str | None = None,
                 max_per_sec: float = 6.0):
        self.cache_dir = ROOT / cache_cfg.get("dir", "data_cache")
        self.cache_dir.mkdir(exist_ok=True)
        self.ttl_seconds = float(cache_cfg.get("ttl_hours", 24)) * 3600
        self.min_interval = 1.0 / max_per_sec
        self._last_request = 0.0
        self.session = requests.Session()
        self.session.headers["Accept"] = "application/json"  # FINRA defaults to text
        if user_agent:
            self.session.headers["User-Agent"] = user_agent

    def _cache_path(self, key: str):
        return self.cache_dir / (hashlib.sha256(key.encode()).hexdigest()[:32] + ".json")

    def get_json(self, url: str, params: dict | None = None) -> dict | list | None:
        return self._request_json("GET", url, params=params)

    def post_json(self, url: str, payload) -> dict | list | None:
        return self._request_json("POST", url, payload=payload)

    def get_text(self, url: str) -> str | None:
        cached = self._read_cache(url)
        if cached is not None:
            return cached["body"]
        resp = self._throttled("GET", url)
        if resp is None:
            return None
        self._write_cache(url, {"body": resp.text})
        return resp.text

    def _request_json(self, method, url, params=None, payload=None):
        key = json.dumps([method, url, params, payload], sort_keys=True)
        cached = self._read_cache(key)
        if cached is not None:
            return cached["body"]
        resp = self._throttled(method, url, params=params, payload=payload)
        if resp is None:
            return None
        body = resp.json()
        self._write_cache(key, {"body": body})
        return body

    def _throttled(self, method, url, params=None, payload=None):
        wait = self.min_interval - (time.monotonic() - self._last_request)
        if wait > 0:
            time.sleep(wait)
        self._last_request = time.monotonic()
        try:
            resp = self.session.request(method, url, params=params, json=payload,
                                        timeout=30)
        except requests.RequestException as exc:
            print(f"  [warn] {method} {url} failed: {exc}")
            return None
        if resp.status_code != 200:
            print(f"  [warn] {method} {url} -> HTTP {resp.status_code}")
            return None
        return resp

    def _read_cache(self, key: str):
        path = self._cache_path(key)
        if not path.exists():
            return None
        if time.time() - path.stat().st_mtime > self.ttl_seconds:
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return None

    def _write_cache(self, key: str, body: dict) -> None:
        self._cache_path(key).write_text(
            json.dumps(body, ensure_ascii=False), encoding="utf-8")


def edgar_user_agent() -> str:
    return os.environ.get(
        "EDGAR_USER_AGENT",
        "smallcap-record research np.media.market@gmail.com",
    )

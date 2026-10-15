"""
http.py — One polite, auditable HTTP client for every live source.

  * retries with back-off on 429/5xx (urllib3 Retry)
  * per-host minimum interval (e.g. Nominatim = 1 request per second)
  * identifying User-Agent with contact e-mail (OSM usage policy)
  * on-disk cache of raw responses (data/external/cache/, git-ignored)
  * provenance log (docs/live_provenance_log.csv): time, source, URL with
    secrets removed, HTTP status, bytes, SHA-256 of the response body
"""
from __future__ import annotations

import csv
import hashlib
import re
import time
from datetime import datetime
from urllib.parse import urlparse

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from src.config import CONTACT_EMAIL, LIVE_CACHE_DIR, LIVE_PROVENANCE

USER_AGENT = f"qm640-capstone-research/1.0 (Walsh College; contact: {CONTACT_EMAIL or 'not-set'})"
MIN_INTERVAL = {"nominatim.openstreetmap.org": 1.1, "overpass-api.de": 2.0, "api.data.gov.in": 0.5}
SECRET_PARAMS = re.compile(r"(api-key|api_key|apikey|token|key)=[^&]+", re.I)


def redact_url(url: str) -> str:
    """Remove API keys from URLs before they are logged anywhere."""
    return SECRET_PARAMS.sub(r"\1=***", url)


def log_provenance(source: str, url: str, status: int, body: bytes, note: str = "") -> None:
    LIVE_PROVENANCE.parent.mkdir(parents=True, exist_ok=True)
    new = not LIVE_PROVENANCE.exists()
    with open(LIVE_PROVENANCE, "a", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        if new:
            w.writerow(["timestamp", "source", "url", "status", "bytes", "sha256", "note"])
        w.writerow([datetime.now().isoformat(timespec="seconds"), source, redact_url(url), status,
                    len(body), hashlib.sha256(body).hexdigest()[:16], note])


class LiveClient:
    def __init__(self, source: str, use_cache: bool = True, timeout: int = 60):
        self.source, self.use_cache, self.timeout = source, use_cache, timeout
        self.session = requests.Session()
        self.session.headers["User-Agent"] = USER_AGENT
        retry = Retry(total=4, backoff_factor=2, status_forcelist=(429, 500, 502, 503, 504),
                      allowed_methods=("GET", "POST"))
        self.session.mount("https://", HTTPAdapter(max_retries=retry))
        self._last: dict[str, float] = {}

    def _wait(self, url: str) -> None:
        host = urlparse(url).netloc
        gap = MIN_INTERVAL.get(host, 0.3)
        dt = time.time() - self._last.get(host, 0)
        if dt < gap:
            time.sleep(gap - dt)
        self._last[host] = time.time()

    def _cache_path(self, key: str):
        return LIVE_CACHE_DIR / self.source / (hashlib.sha256(key.encode()).hexdigest()[:24] + ".bin")

    def request(self, method: str, url: str, **kw) -> bytes:
        key = method + redact_url(url) + repr(sorted(kw.get("params", {}).items())) + repr(kw.get("data"))
        cp = self._cache_path(key)
        if self.use_cache and cp.exists():
            return cp.read_bytes()
        self._wait(url)
        r = self.session.request(method, url, timeout=self.timeout, **kw)
        log_provenance(self.source, r.url, r.status_code, r.content)
        r.raise_for_status()
        cp.parent.mkdir(parents=True, exist_ok=True)
        cp.write_bytes(r.content)
        return r.content

    def get_json(self, url: str, **kw):
        import json
        return json.loads(self.request("GET", url, **kw))

"""Base source class and shared helpers."""

from __future__ import annotations

import logging
import time
from typing import Any

import requests

from ..config import Profile
from ..models import Job

log = logging.getLogger(__name__)

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/126.0.0.0 Safari/537.36"
)

# Words -> ISO alpha-2 for the countries we care about, plus a few neighbours so
# location strings can be resolved.
COUNTRY_WORDS: dict[str, str] = {
    "united kingdom": "GB", "great britain": "GB", "england": "GB",
    "scotland": "GB", "wales": "GB", "uk": "GB", "u.k.": "GB",
    "norway": "NO", "norge": "NO",
    "sweden": "SE", "sverige": "SE",
    "iceland": "IS", "ísland": "IS", "island": "IS",
    "denmark": "DK", "danmark": "DK",
    "finland": "FI", "suomi": "FI",
    "portugal": "PT",
    "germany": "DE", "netherlands": "NL", "nederland": "NL",
    "belgium": "BE", "belgië": "BE", "belgique": "BE",
    "ireland": "IE",
    "canada": "CA",
}

# Major cities -> country, to resolve location strings that omit the country.
CITY_COUNTRY: dict[str, str] = {
    "london": "GB", "manchester": "GB", "edinburgh": "GB", "glasgow": "GB",
    "cambridge": "GB", "bristol": "GB", "leeds": "GB", "birmingham": "GB",
    "oslo": "NO", "bergen": "NO", "trondheim": "NO", "stavanger": "NO",
    "stockholm": "SE", "gothenburg": "SE", "göteborg": "SE", "malmo": "SE",
    "malmö": "SE", "lund": "SE", "uppsala": "SE",
    "reykjavik": "IS", "reykjavík": "IS",
    "copenhagen": "DK", "københavn": "DK", "aarhus": "DK", "odense": "DK",
    "helsinki": "FI", "espoo": "FI", "tampere": "FI", "oulu": "FI",
    "amsterdam": "NL", "rotterdam": "NL", "the hague": "NL",
    "den haag": "NL", "utrecht": "NL", "eindhoven": "NL",
    "brussels": "BE", "brussel": "BE", "bruxelles": "BE",
    "antwerp": "BE", "antwerpen": "BE", "ghent": "BE",
    "gent": "BE", "bruges": "BE", "brugge": "BE",
    "toronto": "CA", "vancouver": "CA", "montreal": "CA",
    "ottawa": "CA", "calgary": "CA", "edmonton": "CA",
}


def resolve_country(text: str | None) -> str | None:
    """Best-effort ISO alpha-2 from a free-form location string."""
    if not text:
        return None
    low = text.lower()
    for word, code in COUNTRY_WORDS.items():
        if word in low:
            return code
    for city, code in CITY_COUNTRY.items():
        if city in low:
            return code
    return None


class Source:
    """Abstract job source. Subclasses implement :meth:`fetch`."""

    name: str = "base"

    def __init__(self, profile: Profile):
        self.profile = profile
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,application/json;q=0.8,*/*;q=0.7",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
        })

    # -- helpers -----------------------------------------------------------
    def _request(self, method: str, url: str, **kwargs) -> requests.Response | None:
        last_exc: Exception | None = None
        for attempt in range(1, 4):
            try:
                resp = self.session.request(method, url, **kwargs)
                resp.raise_for_status()
                return resp
            except Exception as exc:  # noqa: BLE001 - network layer
                last_exc = exc
                log.warning("[%s] %s %s failed (attempt %d/3): %s",
                            self.name, method, url, attempt, exc)
                if hasattr(exc, "response") and exc.response is not None:
                    body = (exc.response.text or "")[:400]
                    log.debug("[%s] response body: %s", self.name, body)
                time.sleep(min(2 ** attempt, 8))
        log.error("[%s] giving up on %s: %s", self.name, url, last_exc)
        return None

    def _get(self, url: str, *, params: dict[str, Any] | None = None,
             timeout: int = 25) -> requests.Response | None:
        return self._request("GET", url, params=params, timeout=timeout)

    def _post(self, url: str, *, json: Any | None = None,
              timeout: int = 30) -> requests.Response | None:
        return self._request("POST", url, json=json, timeout=timeout)

    # -- API ---------------------------------------------------------------
    def fetch(self) -> list[Job]:  # pragma: no cover - abstract
        raise NotImplementedError

    def safe_fetch(self) -> list[Job]:
        """Never let one source break the whole run."""
        try:
            jobs = self.fetch()
            log.info("[%s] fetched %d jobs", self.name, len(jobs))
            return jobs
        except Exception:
            log.exception("[%s] fetch crashed", self.name)
            return []

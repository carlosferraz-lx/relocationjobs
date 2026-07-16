"""Base source class and shared helpers."""

from __future__ import annotations

import logging
import time
from typing import Any, Optional

import requests

from ..config import Profile
from ..models import Job

log = logging.getLogger(__name__)

USER_AGENT = (
    "relocation-job-finder/0.1 (personal job search; "
    "https://github.com/carlosferraz-lx/relocation-job-finder)"
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
    "germany": "DE", "netherlands": "NL", "ireland": "IE",
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
}


def resolve_country(text: Optional[str]) -> Optional[str]:
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
        self.session.headers.update({"User-Agent": USER_AGENT,
                                     "Accept": "application/json"})

    # -- helpers -----------------------------------------------------------
    def _get(self, url: str, *, params: dict[str, Any] | None = None,
             timeout: int = 25, retries: int = 3) -> Optional[requests.Response]:
        last_exc: Optional[Exception] = None
        for attempt in range(1, retries + 1):
            try:
                resp = self.session.get(url, params=params, timeout=timeout)
                resp.raise_for_status()
                return resp
            except Exception as exc:  # noqa: BLE001 - network layer
                last_exc = exc
                log.warning("[%s] GET %s failed (attempt %d/%d): %s",
                            self.name, url, attempt, retries, exc)
                time.sleep(min(2 ** attempt, 8))
        log.error("[%s] giving up on %s: %s", self.name, url, last_exc)
        return None

    # -- API ---------------------------------------------------------------
    def fetch(self) -> list[Job]:  # pragma: no cover - abstract
        raise NotImplementedError

    def safe_fetch(self) -> list[Job]:
        """Never let one source break the whole run."""
        try:
            jobs = self.fetch()
            log.info("[%s] fetched %d jobs", self.name, len(jobs))
            return jobs
        except Exception as exc:  # noqa: BLE001
            log.exception("[%s] fetch crashed: %s", self.name, exc)
            return []

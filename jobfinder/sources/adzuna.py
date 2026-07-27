"""Adzuna (optional) - richer UK salary data. Needs a free API key.

Set ADZUNA_APP_ID and ADZUNA_APP_KEY in the environment (or repo secrets) to
enable. When the keys are absent the source disables itself silently.
"""

from __future__ import annotations

import logging
import os

from ..models import Job, strip_html
from .base import Source, resolve_country

log = logging.getLogger(__name__)

API = "https://api.adzuna.com/v1/api/jobs/{country}/search/1"
# Adzuna coverage intersected with the target countries.
ADZUNA_COUNTRIES = {"GB": "gb"}
QUERIES = ["qa engineer", "test automation", "sdet", "quality assurance"]


class Adzuna(Source):
    name = "adzuna"

    def fetch(self) -> list[Job]:
        app_id = os.getenv("ADZUNA_APP_ID")
        app_key = os.getenv("ADZUNA_APP_KEY")
        if not app_id or not app_key:
            log.info("[adzuna] ADZUNA_APP_ID/ADZUNA_APP_KEY not set; skipping")
            return []

        jobs: list[Job] = []
        seen: set[str] = set()
        for target, adz in ADZUNA_COUNTRIES.items():
            if target not in self.profile.target_countries:
                continue
            for what in QUERIES:
                resp = self._get(
                    API.format(country=adz),
                    params={
                        "app_id": app_id,
                        "app_key": app_key,
                        "results_per_page": min(self.profile.results_per_source, 50),
                        "what": what,
                        "content-type": "application/json",
                    },
                )
                if resp is None:
                    continue
                for r in resp.json().get("results", []):
                    rid = str(r.get("id"))
                    if rid in seen:
                        continue
                    seen.add(rid)
                    loc = (r.get("location") or {}).get("display_name") or ""
                    jobs.append(
                        Job(
                            source=self.name,
                            external_id=rid,
                            title=(r.get("title") or "").strip(),
                            company=(r.get("company") or {}).get("display_name", ""),
                            url=r.get("redirect_url", ""),
                            description=strip_html(r.get("description")),
                            country=resolve_country(loc) or target,
                            city=loc.split(",")[0].strip() if loc else None,
                            remote=False,
                            tags=[(r.get("category") or {}).get("label", "")],
                            posted=(r.get("created") or "")[:10] or None,
                            salary_min=r.get("salary_min"),
                            salary_max=r.get("salary_max"),
                            salary_currency="GBP",
                            salary_period="year",
                        )
                    )
        return jobs

"""EU-wide - Arbeitnow public job board API (no key).

Returns one page of the newest postings; we filter to target countries and QA
roles downstream. Many Arbeitnow ads flag visa relocation in their tags/text.
"""

from __future__ import annotations

from ..models import Job, strip_html
from .base import resolve_country, Source

API = "https://www.arbeitnow.com/api/job-board-api"


class Arbeitnow(Source):
    name = "arbeitnow"

    def fetch(self) -> list[Job]:
        resp = self._get(API)
        if resp is None:
            return []
        data = resp.json().get("data", [])
        jobs: list[Job] = []
        for it in data:
            location = it.get("location") or ""
            tags = list(it.get("tags") or []) + list(it.get("job_types") or [])
            posted = it.get("created_at")
            posted_iso = None
            if isinstance(posted, (int, float)):
                from datetime import datetime, timezone
                posted_iso = datetime.fromtimestamp(posted, timezone.utc).date().isoformat()
            jobs.append(
                Job(
                    source=self.name,
                    external_id=str(it.get("slug")),
                    title=(it.get("title") or "").strip(),
                    company=it.get("company_name") or "",
                    url=it.get("url", ""),
                    description=strip_html(it.get("description")),
                    country=resolve_country(location),
                    city=location.split(",")[0].strip() if location else None,
                    remote=bool(it.get("remote")),
                    tags=tags,
                    posted=posted_iso,
                )
            )
        return jobs

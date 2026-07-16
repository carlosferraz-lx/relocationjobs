"""Remote board - RemoteOK API (no key).

Per their API terms we link back to Remote OK as the source (the job ``url``
points to remoteok.com and the dashboard credits the source).
"""

from __future__ import annotations

from ..models import Job, strip_html
from .base import resolve_country, Source

API = "https://remoteok.com/api"


class RemoteOK(Source):
    name = "remoteok"

    def fetch(self) -> list[Job]:
        resp = self._get(API)
        if resp is None:
            return []
        data = resp.json()
        jobs: list[Job] = []
        for it in data:
            # First element is a legal/attribution notice, not a job.
            if not isinstance(it, dict) or "position" not in it:
                continue
            location = it.get("location") or ""
            jobs.append(
                Job(
                    source=self.name,
                    external_id=str(it.get("id")),
                    title=(it.get("position") or "").strip(),
                    company=it.get("company") or "",
                    url=it.get("url") or it.get("apply_url") or "",
                    description=strip_html(it.get("description")),
                    country=resolve_country(location),
                    city=None,
                    remote=True,
                    tags=list(it.get("tags") or []),
                    posted=(it.get("date") or "")[:10] or None,
                    salary_min=it.get("salary_min") or None,
                    salary_max=it.get("salary_max") or None,
                    salary_currency="USD",
                    salary_period="year",
                )
            )
        return jobs

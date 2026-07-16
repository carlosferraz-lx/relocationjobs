"""Portugal/EU tech - Landing.jobs API (no key).

Rich fields: relocation_paid flag, gross salary range, currency and locations.
"""

from __future__ import annotations

from ..models import Job, strip_html
from .base import Source

API = "https://landing.jobs/api/v1/jobs"


class LandingJobs(Source):
    name = "landingjobs"

    def fetch(self) -> list[Job]:
        resp = self._get(API, params={"limit": min(self.profile.results_per_source, 200)})
        if resp is None:
            return []
        data = resp.json()
        if isinstance(data, dict):
            data = data.get("jobs") or data.get("data") or []
        jobs: list[Job] = []
        for it in data:
            locs = it.get("locations") or []
            loc = locs[0] if locs else {}
            desc = " ".join(
                strip_html(it.get(k, ""))
                for k in ("role_description", "main_requirements", "nice_to_have", "perks")
            ).strip()
            tags = list(it.get("tags") or [])
            if it.get("relocation_paid"):
                tags.append("relocation")
            jobs.append(
                Job(
                    source=self.name,
                    external_id=str(it.get("id")),
                    title=(it.get("title") or "").strip(),
                    company=(it.get("company") or {}).get("name", "") if isinstance(it.get("company"), dict) else "",
                    url=it.get("url", ""),
                    description=desc,
                    country=(loc.get("country_code") or "").upper() or None,
                    city=loc.get("city"),
                    remote=bool(it.get("remote")),
                    tags=tags,
                    posted=(it.get("published_at") or "")[:10] or None,
                    salary_min=it.get("gross_salary_low"),
                    salary_max=it.get("gross_salary_high"),
                    salary_currency=it.get("currency_code"),
                    salary_period="year",
                )
            )
        return jobs

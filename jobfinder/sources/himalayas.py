"""Remote board - Himalayas API (no key)."""

from __future__ import annotations

from datetime import datetime, timezone

from ..models import Job, strip_html
from .base import Source, resolve_country

API = "https://himalayas.app/jobs/api"


class Himalayas(Source):
    name = "himalayas"

    def fetch(self) -> list[Job]:
        # The feed returns placeholder company names and caps results once the
        # limit reaches ~20, so we request a small, clean page.
        resp = self._get(API, params={"limit": 10})
        if resp is None:
            return []
        jobs: list[Job] = []
        for it in resp.json().get("jobs", []):
            restrictions = it.get("locationRestrictions") or []
            country = None
            for r in restrictions:
                country = resolve_country(r)
                if country:
                    break
            posted = it.get("pubDate")
            posted_iso = None
            if isinstance(posted, (int, float)):
                posted_iso = datetime.fromtimestamp(posted, timezone.utc).date().isoformat()
            tags = list(it.get("categories") or []) + list(it.get("seniority") or [])
            company = it.get("companyName") or ""
            if company in ("", "name"):
                slug = it.get("companySlug") or ""
                company = slug.replace("-", " ").title()
            jobs.append(
                Job(
                    source=self.name,
                    external_id=str(it.get("guid")),
                    title=(it.get("title") or "").strip(),
                    company=company,
                    url=it.get("applicationLink") or it.get("guid") or "",
                    description=strip_html(it.get("description")) + " " + " ".join(restrictions),
                    country=country,
                    city=None,
                    remote=True,
                    tags=tags,
                    posted=posted_iso,
                    salary_min=it.get("minSalary"),
                    salary_max=it.get("maxSalary"),
                    salary_currency=it.get("currency"),
                    salary_period=it.get("salaryPeriod") or "year",
                )
            )
        return jobs

"""freehire.me aggregator — open API, no key.

Tech jobs from ~50 ATS platforms across many countries.
Docs: https://freehire.me/docs/api
"""

from __future__ import annotations

from ..models import Job, strip_html
from .base import Source

API = "https://freehire.me/api/v1/jobs/search"
QUERIES = ["QA", "quality assurance", "test automation", "test engineer"]


class FreeHire(Source):
    name = "freehire"

    def fetch(self) -> list[Job]:
        seen: set[str] = set()
        jobs: list[Job] = []
        limit = min(self.profile.results_per_source, 100)
        target = [c.lower() for c in self.profile.target_countries]
        # freehire uses "gb" for the United Kingdom.
        target = ["gb" if c == "uk" else c for c in target]

        for query in QUERIES:
            params: dict[str, object] = {
                "q": query,
                "limit": limit,
                "offset": 0,
            }
            if target:
                params["countries"] = target

            resp = self._get(API, params=params)
            if resp is None:
                continue
            data = resp.json().get("data") or []
            for it in data:
                slug = it.get("public_slug") or it.get("external_id")
                if not slug or slug in seen:
                    continue
                seen.add(slug)

                countries = [c.upper() for c in (it.get("countries") or [])]
                cities = it.get("cities") or []
                work_mode = it.get("work_mode") or ""
                remote = work_mode == "remote"

                tags = list(it.get("skills") or [])
                tags.extend(it.get("collections") or [])

                posted = it.get("posted_at") or it.get("created_at") or ""
                if posted:
                    posted = posted[:10]

                salary = it.get("salary") or {}
                salary_min = salary.get("min") or salary.get("minimum")
                salary_max = salary.get("max") or salary.get("maximum")
                salary_currency = salary.get("currency")
                salary_period = salary.get("period") or "year"

                description = strip_html(it.get("description") or "")
                jobs.append(
                    Job(
                        source=self.name,
                        external_id=slug,
                        title=(it.get("title") or "").strip(),
                        company=(it.get("company") or "").strip(),
                        url=it.get("url", ""),
                        description=description,
                        country=countries[0] if countries else None,
                        city=cities[0] if cities else None,
                        remote=remote,
                        tags=tags,
                        posted=posted or None,
                        salary_min=salary_min,
                        salary_max=salary_max,
                        salary_currency=salary_currency,
                        salary_period=salary_period,
                    )
                )

                if len(jobs) >= self.profile.results_per_source:
                    break
            if len(jobs) >= self.profile.results_per_source:
                break

        return jobs

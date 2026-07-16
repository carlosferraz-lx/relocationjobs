"""Sweden - Arbetsförmedlingen Platsbanken (JobTech open API, no key)."""

from __future__ import annotations

from ..models import Job, strip_html
from .base import Source

API = "https://jobsearch.api.jobtechdev.se/search"
# The API ANDs multi-word free text, so we issue one query per phrase and merge.
QUERIES = ["QA", "test automation", "SDET", "quality assurance",
           "test engineer", "quality engineer"]


class Platsbanken(Source):
    name = "platsbanken"

    def fetch(self) -> list[Job]:
        hits: list[dict] = []
        seen: set[str] = set()
        per = max(10, min(self.profile.results_per_source, 100) // 2)
        for q in QUERIES:
            resp = self._get(API, params={"q": q, "limit": per})
            if resp is None:
                continue
            for h in resp.json().get("hits", []):
                hid = str(h.get("id"))
                if hid not in seen:
                    seen.add(hid)
                    hits.append(h)
        jobs: list[Job] = []
        for h in hits:
            desc = (h.get("description") or {}).get("text") or ""
            addr = h.get("workplace_address") or {}
            employer = h.get("employer") or {}
            jobs.append(
                Job(
                    source=self.name,
                    external_id=str(h.get("id")),
                    title=h.get("headline", "").strip(),
                    company=employer.get("name") or employer.get("workplace") or "",
                    url=h.get("webpage_url", ""),
                    description=strip_html(desc),
                    country="SE",
                    city=addr.get("municipality") or addr.get("city"),
                    remote=False,
                    tags=self._tags(h),
                    posted=h.get("publication_date"),
                    salary_currency="SEK" if h.get("salary_description") else None,
                )
            )
        return jobs

    @staticmethod
    def _tags(h: dict) -> list[str]:
        tags = []
        for key in ("occupation", "occupation_group", "occupation_field"):
            node = h.get(key) or {}
            if node.get("label"):
                tags.append(node["label"])
        for m in (h.get("must_have") or {}).get("skills", []) or []:
            if isinstance(m, dict) and m.get("label"):
                tags.append(m["label"])
        return tags

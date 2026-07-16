"""Norway - NAV Arbeidsplassen public job search API (no key)."""

from __future__ import annotations

from ..models import Job, strip_html
from .base import Source

API = "https://arbeidsplassen.nav.no/stillinger/api/search"
AD_URL = "https://arbeidsplassen.nav.no/stillinger/stilling/{uuid}"
# The API ANDs multi-word free text, so we issue one query per phrase and merge.
QUERIES = ["QA", "test automation", "test engineer", "quality assurance", "SDET"]


class Nav(Source):
    name = "nav"

    def fetch(self) -> list[Job]:
        hits: list[dict] = []
        seen: set[str] = set()
        per = max(10, min(self.profile.results_per_source, 100) // 2)
        for q in QUERIES:
            resp = self._get(API, params={"q": q, "size": per})
            if resp is None:
                continue
            for hit in resp.json().get("hits", {}).get("hits", []):
                hid = str(hit.get("_id") or (hit.get("_source") or {}).get("uuid"))
                if hid not in seen:
                    seen.add(hid)
                    hits.append(hit)
        jobs: list[Job] = []
        for hit in hits:
            src = hit.get("_source", {})
            props = src.get("properties") or {}
            loc = (src.get("locationList") or [{}])[0]
            employer = src.get("employer") or {}
            desc = props.get("adtext") or props.get("shortSummary") or ""
            summary = (src.get("generatedSearchMetadata") or {}).get("shortSummary", "")
            jobs.append(
                Job(
                    source=self.name,
                    external_id=str(src.get("uuid")),
                    title=(props.get("jobtitle") or src.get("title") or "").strip(),
                    company=employer.get("name") or src.get("businessName") or "",
                    url=AD_URL.format(uuid=src.get("uuid")),
                    description=strip_html(desc) or summary,
                    country="NO",
                    city=(loc.get("city") or "").title() or None,
                    remote=False,
                    tags=self._tags(props),
                    posted=(src.get("published") or "")[:10] or None,
                    salary_currency="NOK",
                )
            )
        return jobs

    @staticmethod
    def _tags(props: dict) -> list[str]:
        tags: list[str] = []
        for t in props.get("searchtagsai", []) or []:
            if isinstance(t, str):
                tags.append(t)
        for t in props.get("searchtags", []) or []:
            if isinstance(t, dict) and t.get("label"):
                tags.append(t["label"])
        kw = props.get("keywords")
        if kw:
            tags.extend([p.strip() for p in str(kw).replace(";", ",").split(",") if p.strip()])
        return tags

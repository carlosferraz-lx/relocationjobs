"""EURES (European Job Mobility Portal) public search API.

Covers EU/EEA job vacancies. No API key required.
Docs: https://github.com/rorar/EURES-API-Documentation
"""

from __future__ import annotations

from datetime import datetime, timezone

from ..models import Job, strip_html
from .base import Source

SEARCH_API = "https://europa.eu/eures/api/jv-searchengine/public/jv-search/search"
QUERIES = ["QA", "quality assurance", "test automation"]

# EURES uses lowercase ISO-3166 country codes and does not cover UK/Canada.
SUPPORTED = {"nl", "be", "no", "se", "is", "dk", "fi", "de", "ie", "fr", "at",
             "es", "it", "pt", "pl", "cz", "lu", "li"}


class EURES(Source):
    name = "eures"

    def fetch(self) -> list[Job]:
        locations = sorted(
            c.lower() for c in self.profile.target_countries
            if c.lower() in SUPPORTED
        )
        if not locations:
            return []

        per_page = 50
        jobs: list[Job] = []
        seen: set[str] = set()

        for query in QUERIES:
            for page in range(1, (self.profile.results_per_source // per_page) + 2):
                payload = {
                    "resultsPerPage": per_page,
                    "page": page,
                    "sortSearch": "MOST_RECENT",
                    "keywords": [{"keyword": query, "specificSearchCode": "EVERYWHERE"}],
                    "publicationPeriod": None,
                    "occupationUris": [],
                    "skillUris": [],
                    "requiredExperienceCodes": [],
                    "positionScheduleCodes": [],
                    "sectorCodes": [],
                    "educationAndQualificationLevelCodes": [],
                    "positionOfferingCodes": [],
                    "locationCodes": locations,
                    "euresFlagCodes": [],
                    "otherBenefitsCodes": [],
                    "requiredLanguages": [],
                    "minNumberPost": None,
                    "sessionId": f"relocationjobs-{self.name}",
                    "requestLanguage": "en",
                }
                resp = self._post(SEARCH_API, json=payload)
                if resp is None:
                    break

                data = resp.json()
                items = data.get("jvs") or []
                if not items:
                    break

                for it in items:
                    eid = it.get("id")
                    if not eid or eid in seen:
                        continue
                    seen.add(eid)

                    location_map = it.get("locationMap") or {}
                    countries = [c.upper() for c in location_map]

                    ts = it.get("creationDate")
                    posted = None
                    if ts:
                        posted = datetime.fromtimestamp(ts / 1000, tz=timezone.utc).date().isoformat()

                    employer = it.get("employer") or {}
                    company = (employer.get("name") or "").strip()

                    jobs.append(
                        Job(
                            source=self.name,
                            external_id=eid,
                            title=(it.get("title") or "").strip(),
                            company=company,
                            url=f"https://europa.eu/eures/portal/jv-se/jv-detail/{eid}",
                            description=strip_html(it.get("description") or ""),
                            country=countries[0] if countries else None,
                            city=None,
                            remote=False,
                            tags=it.get("jobCategoriesCodes") or [],
                            posted=posted,
                        )
                    )

                    if len(jobs) >= self.profile.results_per_source:
                        return jobs

            if len(jobs) >= self.profile.results_per_source:
                break

        return jobs

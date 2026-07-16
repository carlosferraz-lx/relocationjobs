"""Generate the GitHub Pages dashboard data (docs/data.json)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from .config import Profile
from .cost_of_living import COUNTRIES, required_gross_eur, required_gross_local
from .models import Job

DOCS = Path(__file__).resolve().parent.parent / "docs"
DATA_JSON = DOCS / "data.json"

COUNTRY_NAMES = {code: econ.name for code, econ in COUNTRIES.items()}


def _salary_floors(profile: Profile) -> list[dict]:
    rows = []
    for code in profile.target_countries:
        eur = required_gross_eur(code, None, profile.current_gross_salary,
                                 margin=profile.standard_of_living_margin)
        local = required_gross_local(code, None, profile.current_gross_salary,
                                     margin=profile.standard_of_living_margin)
        if eur is None or local is None:
            continue
        amount, currency = local
        rows.append({
            "country": code,
            "country_name": COUNTRY_NAMES.get(code, code),
            "floor_eur": round(eur),
            "floor_local": round(amount),
            "currency": currency,
        })
    return rows


def _job_row(job: Job, is_new: bool) -> dict:
    return {
        "uid": job.uid,
        "title": job.title,
        "company": job.company,
        "url": job.url,
        "source": job.source,
        "country": job.country,
        "country_name": COUNTRY_NAMES.get(job.country or "", job.country or ""),
        "city": job.city,
        "remote": job.remote,
        "posted": job.posted,
        "score": job.score,
        "matched_skills": job.matched_skills,
        "relocation": bool(job.relocation_signals),
        "relocation_signals": job.relocation_signals,
        "salary_status": job.salary_status,
        "salary_eur_year": job.salary_eur_year,
        "salary_floor_eur": job.salary_floor_eur,
        "salary_min": job.salary_min,
        "salary_max": job.salary_max,
        "salary_currency": job.salary_currency,
        "is_new": is_new,
    }


def write_dashboard(
    profile: Profile,
    new_jobs: list[Job],
    all_matches: list[Job],
    new_uids: set[str],
) -> Path:
    DOCS.mkdir(parents=True, exist_ok=True)
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "candidate": profile.name,
        "baseline": {
            "country": profile.current_country,
            "gross_salary": profile.current_gross_salary,
            "currency": profile.current_currency,
        },
        "salary_floors": _salary_floors(profile),
        "counts": {
            "new": len(new_jobs),
            "total": len(all_matches),
        },
        "jobs": [_job_row(j, j.uid in new_uids) for j in all_matches],
    }
    DATA_JSON.write_text(json.dumps(payload, indent=1, ensure_ascii=False), "utf-8")
    return DATA_JSON

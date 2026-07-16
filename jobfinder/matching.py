"""Scoring and filtering of raw jobs against the user profile."""

from __future__ import annotations

import re
from datetime import date, datetime
from typing import Optional

from .config import Profile
from .cost_of_living import annualise, required_gross_eur, to_eur
from .models import Job

# Countries in the EU/EEA (free movement for EU/EEA citizens). All target
# countries except the UK are EEA.
EEA = {"SE", "DK", "FI", "NO", "IS", "PT", "DE", "NL", "IE", "FR", "ES", "IT",
       "BE", "AT", "PL", "LU", "LI"}

# Unambiguous QA role phrases. A body-only match must contain one of these
# (generic words like "testing"/"tester" alone are too noisy for a fallback).
STRONG_QA = (
    "qa", "sdet", "quality assurance", "quality engineer", "quality engineering",
    "test engineer", "test automation", "software engineer in test",
    "software development engineer in test", "test analyst", "test lead", "qa lead",
)

# Language-requirement phrases -> the language they demand.
_LANG_REQ = {
    "norwegian": ["flytende norsk", "fluent norwegian", "norsk skriftlig", "must speak norwegian"],
    "swedish": ["flytande svenska", "fluent swedish", "must speak swedish", "svenska i tal"],
    "danish": ["flydende dansk", "fluent danish", "must speak danish"],
    "finnish": ["fluent finnish", "sujuva suomi", "must speak finnish"],
    "icelandic": ["fluent icelandic", "must speak icelandic"],
}


def _needs_sponsorship(country: str, eu_citizen: bool) -> bool:
    """Does working in `country` require visa sponsorship for this candidate?"""
    if country == "GB":
        return True  # post-Brexit, EU citizens need a UK work visa
    if not eu_citizen:
        return True
    return country not in EEA


def _language_penalty(haystack: str, spoken: list[str]) -> Optional[str]:
    for lang, phrases in _LANG_REQ.items():
        if lang in spoken:
            continue
        if any(p in haystack for p in phrases):
            return lang
    return None


def _recency_bonus(posted: Optional[str]) -> float:
    if not posted:
        return 0.0
    try:
        d = datetime.fromisoformat(posted[:10]).date()
    except ValueError:
        return 0.0
    age = (date.today() - d).days
    if age <= 7:
        return 2.0
    if age <= 30:
        return 1.0
    return 0.0


def _word_hit(needle: str, haystack: str) -> bool:
    """Match short tokens (e.g. "qa") on word boundaries; substring otherwise."""
    if len(needle) <= 3:
        return re.search(rf"(?<![a-z]){re.escape(needle)}(?![a-z])", haystack) is not None
    return needle in haystack


def _is_qa(job: Job, profile: Profile, skill_weight: float) -> bool:
    title = job.title.lower()
    if any(_word_hit(kw, title) for kw in profile.title_keywords):
        return True
    # No QA title: only accept on an unambiguous QA phrase in the body plus a
    # solid cluster of relevant skills, to avoid false positives.
    body_qa = any(_word_hit(kw, job.haystack) for kw in STRONG_QA)
    return body_qa and skill_weight >= 6


def evaluate(job: Job, profile: Profile) -> Optional[Job]:
    """Score a job and decide whether it survives the filters.

    Returns the enriched Job if it matches, else None.
    """
    hay = job.haystack

    # -- skills ------------------------------------------------------------
    matched: list[str] = []
    weight = 0.0
    for skill in profile.skills:
        if skill.name in hay:
            matched.append(skill.name)
            weight += skill.weight
    job.matched_skills = matched

    # -- QA relevance ------------------------------------------------------
    if not _is_qa(job, profile, weight):
        return None

    # -- geography ---------------------------------------------------------
    in_target = job.country in profile.target_countries
    on_site_target = in_target and not job.remote
    # Remote roles only count when they're explicitly tied to a target country
    # (a worldwide-remote role isn't a relocation opportunity).
    remote_ok = job.remote and profile.include_remote and in_target
    if not (on_site_target or remote_ok):
        return None

    # -- relocation gating (on-site only) ---------------------------------
    signals = [s for s in profile.relocation_signals if s in hay]
    job.relocation_signals = signals
    if on_site_target and profile.require_relocation_support:
        if _needs_sponsorship(job.country, profile.eu_eea_citizen) and not signals:
            return None

    # -- salary vs standard-of-living floor -------------------------------
    floor = None
    if job.country and job.country in profile.target_countries:
        floor = required_gross_eur(
            job.country, job.city, profile.current_gross_salary,
            margin=profile.standard_of_living_margin,
        )
    job.salary_floor_eur = round(floor) if floor else None

    advertised = job.salary_max or job.salary_min
    if advertised and job.salary_currency:
        eur = to_eur(annualise(advertised, job.salary_period), job.salary_currency)
        if eur:
            job.salary_eur_year = round(eur)
            if floor:
                job.salary_status = "above" if eur >= floor else "below"
            else:
                job.salary_status = "known"
    else:
        job.salary_status = "unknown"

    if job.salary_status == "below":
        return None
    if job.salary_status == "unknown" and not profile.keep_when_salary_unknown:
        return None

    # -- score -------------------------------------------------------------
    score = weight
    if any(kw in job.title.lower() for kw in profile.title_keywords):
        score += 5
    if signals:
        score += 4
    if on_site_target:
        score += 3
    if job.salary_status == "above":
        score += 3
    score += _recency_bonus(job.posted)

    lang = _language_penalty(hay, profile.languages_spoken)
    if lang:
        score -= 3

    job.score = round(score, 2)
    return job


def match_all(jobs: list[Job], profile: Profile) -> list[Job]:
    out = [j for j in (evaluate(job, profile) for job in jobs) if j is not None]
    out.sort(key=lambda j: j.score, reverse=True)
    return out


_NORM_RE = re.compile(r"[^a-z0-9]+")


def _norm(text: str) -> str:
    return _NORM_RE.sub(" ", text.lower()).strip()


def dedupe(jobs: list[Job]) -> list[Job]:
    """Drop cross-source duplicates by (title, company, country)."""
    seen: set[tuple[str, str, str]] = set()
    out: list[Job] = []
    for job in jobs:
        key = (_norm(job.title), _norm(job.company), job.country or "")
        if key in seen:
            continue
        seen.add(key)
        out.append(job)
    return out

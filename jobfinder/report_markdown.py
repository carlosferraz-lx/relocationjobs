"""Generate REPORT.md - a private, GitHub-readable daily digest."""

from __future__ import annotations

from datetime import date, datetime, timezone
from pathlib import Path

from .config import Profile
from .cost_of_living import COUNTRIES, required_gross_eur, required_gross_local
from .models import Job

REPORT = Path(__file__).resolve().parent.parent / "REPORT.md"
COUNTRY_NAMES = {code: econ.name for code, econ in COUNTRIES.items()}


def _fmt_int(n: float | None) -> str:
    return f"{int(n):,}" if n is not None else ""


def _posted_key(job: Job) -> date:
    """Sort key for posted dates; missing dates sink to the bottom."""
    if not job.posted:
        return date.min
    try:
        return date.fromisoformat(job.posted[:10])
    except (ValueError, TypeError):
        return date.min


def _salary_cell(job: Job) -> str:
    if job.salary_eur_year is not None:
        if job.salary_min or job.salary_max:
            lo, hi = job.salary_min, job.salary_max
            raw = (f"{_fmt_int(lo)}–{_fmt_int(hi)}" if lo and hi and lo != hi
                   else _fmt_int(hi or lo))
            base = f"{raw} {job.salary_currency or ''}".strip()
        else:
            base = f"€{_fmt_int(job.salary_eur_year)}/yr"
        mark = " ✅" if job.salary_status == "above" else ""
        return base + mark
    return "_not stated_"


def _reloc_cell(job: Job) -> str:
    if job.relocation_signals:
        return "🛂 yes"
    return "remote" if job.remote else "—"


def _job_row(job: Job) -> str:
    title = job.title.replace("|", "\\|")
    company = (job.company or "").replace("|", "\\|")
    link = f"[{title}]({job.url})" if job.url else title
    loc = ", ".join(x for x in (job.city, COUNTRY_NAMES.get(job.country or "", job.country)) if x)
    skills = ", ".join(job.matched_skills[:5])
    return (f"| {job.score:.0f} | {link}<br><sub>{company} · {skills}</sub> "
            f"| {loc or ('Remote' if job.remote else '—')} | {job.source} "
            f"| {_salary_cell(job)} | {_reloc_cell(job)} | {job.posted or ''} |")


_HEADER = ("| Score | Role | Location | Source | Salary | Reloc | Posted |\n"
           "|------:|------|----------|--------|--------|-------|--------|")


def _floor_table(profile: Profile) -> str:
    rows = ["| Country | Gross floor (local) | ≈ EUR |",
            "|---------|--------------------:|------:|"]
    for code in profile.target_countries:
        eur = required_gross_eur(code, None, profile.current_gross_salary,
                                 margin=profile.standard_of_living_margin)
        local = required_gross_local(code, None, profile.current_gross_salary,
                                     margin=profile.standard_of_living_margin)
        if eur is None or local is None:
            continue
        amount, currency = local
        rows.append(f"| {COUNTRY_NAMES.get(code, code)} | "
                    f"{_fmt_int(amount)} {currency} | €{_fmt_int(eur)} |")
    return "\n".join(rows)


def write_report(
    profile: Profile,
    new_jobs: list[Job],
    all_matches: list[Job],
) -> Path:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines: list[str] = [
        "# QA Relocation Job Digest",
        "",
        f"_Updated {now} · {len(new_jobs)} new · {len(all_matches)} active matches_",
        "",
        (
            f"Baseline: **{_fmt_int(profile.current_gross_salary)} "
            f"{profile.current_currency}/yr** in {profile.current_country}. "
            "A ✅ marks pay that meets the standard-of-living floor."
        ),
        "",
        "## Standard-of-living salary floor",
        "",
        _floor_table(profile),
        "",
        "## New since last run",
        "",
    ]

    if new_jobs:
        lines.append(_HEADER)
        lines += [_job_row(j) for j in sorted(new_jobs, key=_posted_key, reverse=True)]
    else:
        lines.append("_No new roles today._")

    lines += ["", "## All active matches", ""]
    countries = sorted({j.country or "Remote" for j in all_matches})
    for code in countries:
        group = [j for j in all_matches if (j.country or "Remote") == code]
        if not group:
            continue
        lines.append(f"### {COUNTRY_NAMES.get(code, code)} ({len(group)})")
        lines.append("")
        lines.append(_HEADER)
        lines += [_job_row(j) for j in sorted(group, key=_posted_key, reverse=True)]
        lines.append("")

    REPORT.write_text("\n".join(lines).rstrip() + "\n", "utf-8")
    return REPORT

"""Load and validate the user profile (profile.yaml)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PROFILE = REPO_ROOT / "profile.yaml"


@dataclass
class Skill:
    name: str
    weight: int = 1


@dataclass
class Profile:
    raw: dict[str, Any]

    # candidate
    name: str
    current_country: str
    current_city: str
    current_gross_salary: float
    current_currency: str
    eu_eea_citizen: bool

    # targets
    title_keywords: list[str]
    skills: list[Skill]
    seniority: list[str]
    languages_spoken: list[str]

    # relocation
    require_relocation_support: bool
    relocation_signals: list[str]

    # geography
    target_countries: list[str]
    include_remote: bool

    # salary
    standard_of_living_margin: float
    keep_when_salary_unknown: bool

    # sources
    sources_enabled: dict[str, bool]
    results_per_source: int

    @classmethod
    def load(cls, path: Path | str | None = None) -> "Profile":
        path = Path(path) if path else DEFAULT_PROFILE
        with open(path, "r", encoding="utf-8") as fh:
            raw = yaml.safe_load(fh) or {}

        cand = raw.get("candidate", {})
        roles = raw.get("target_roles", {})
        reloc = raw.get("relocation", {})
        sal = raw.get("salary", {})

        skills = []
        for item in roles.get("skills", []):
            if isinstance(item, dict):
                skills.append(Skill(name=str(item["name"]).lower(),
                                    weight=int(item.get("weight", 1))))
            else:
                skills.append(Skill(name=str(item).lower()))

        return cls(
            raw=raw,
            name=cand.get("name", "Candidate"),
            current_country=str(cand.get("current_country", "PT")).upper(),
            current_city=cand.get("current_city", ""),
            current_gross_salary=float(cand.get("current_gross_salary", 60000)),
            current_currency=str(cand.get("current_currency", "EUR")).upper(),
            eu_eea_citizen=bool(cand.get("eu_eea_citizen", True)),
            title_keywords=[k.lower() for k in roles.get("title_keywords", [])],
            skills=skills,
            seniority=[s.lower() for s in roles.get("seniority", [])],
            languages_spoken=[s.lower() for s in roles.get("languages_spoken", [])],
            require_relocation_support=bool(reloc.get("require_relocation_support", True)),
            relocation_signals=[s.lower() for s in reloc.get("signals", [])],
            target_countries=[c.upper() for c in raw.get("target_countries", [])],
            include_remote=bool(raw.get("include_remote", True)),
            standard_of_living_margin=float(sal.get("standard_of_living_margin", 1.0)),
            keep_when_salary_unknown=bool(sal.get("keep_when_salary_unknown", True)),
            sources_enabled=dict(raw.get("sources", {})),
            results_per_source=int(raw.get("results_per_source", 100)),
        )

    def source_on(self, name: str) -> bool:
        return bool(self.sources_enabled.get(name, False))

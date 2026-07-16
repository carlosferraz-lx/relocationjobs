"""Core data structures shared across the pipeline."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field, asdict
from datetime import date
from typing import Any, Optional

_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")


def strip_html(text: Optional[str]) -> str:
    """Turn an HTML fragment into plain, collapsed text."""
    if not text:
        return ""
    no_tags = _TAG_RE.sub(" ", text)
    no_tags = (
        no_tags.replace("&nbsp;", " ")
        .replace("&amp;", "&")
        .replace("&lt;", "<")
        .replace("&gt;", ">")
        .replace("&#39;", "'")
        .replace("&quot;", '"')
    )
    return _WS_RE.sub(" ", no_tags).strip()


@dataclass
class Job:
    """A normalised job posting from any source."""

    source: str
    external_id: str
    title: str
    company: str
    url: str
    description: str = ""
    country: Optional[str] = None          # ISO alpha-2, best effort
    city: Optional[str] = None
    remote: bool = False
    tags: list[str] = field(default_factory=list)
    posted: Optional[str] = None           # ISO date string

    # Salary as advertised (may be missing).
    salary_min: Optional[float] = None
    salary_max: Optional[float] = None
    salary_currency: Optional[str] = None
    salary_period: str = "year"            # "year" | "month" | "hour"

    # Filled in by the matcher.
    score: float = 0.0
    matched_skills: list[str] = field(default_factory=list)
    relocation_signals: list[str] = field(default_factory=list)
    salary_eur_year: Optional[float] = None      # normalised annual gross in EUR
    salary_floor_eur: Optional[float] = None      # required floor for its country
    salary_status: str = "unknown"                # unknown | above | below

    @property
    def uid(self) -> str:
        """Stable de-duplication id."""
        raw = f"{self.source}:{self.external_id}".lower()
        return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]

    @property
    def haystack(self) -> str:
        """Lower-cased blob used for keyword matching."""
        return " ".join(
            [self.title, self.description, " ".join(self.tags), self.company]
        ).lower()

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["uid"] = self.uid
        return d


def today_iso() -> str:
    return date.today().isoformat()

"""Persistence of already-seen jobs so each digest only shows what's new."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .models import Job, today_iso

DEFAULT_STATE = Path(__file__).resolve().parent.parent / "data" / "seen_jobs.json"


class SeenStore:
    """A tiny JSON-backed store mapping job uid -> metadata."""

    def __init__(self, path: Path | str | None = None):
        self.path = Path(path) if path else DEFAULT_STATE
        self.seen: dict[str, dict[str, Any]] = {}
        self._load()

    def _load(self) -> None:
        if self.path.exists():
            try:
                self.seen = json.loads(self.path.read_text("utf-8")).get("seen", {})
            except (json.JSONDecodeError, OSError):
                self.seen = {}

    def is_new(self, job: Job) -> bool:
        return job.uid not in self.seen

    def mark(self, job: Job) -> None:
        self.seen[job.uid] = {
            "title": job.title,
            "company": job.company,
            "country": job.country,
            "first_seen": today_iso(),
        }

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"updated": today_iso(), "count": len(self.seen), "seen": self.seen}
        self.path.write_text(json.dumps(payload, indent=1, ensure_ascii=False), "utf-8")

    def partition(self, jobs: list[Job]) -> tuple[list[Job], list[Job]]:
        """Split into (new, already-seen) without mutating the store."""
        new = [j for j in jobs if self.is_new(j)]
        old = [j for j in jobs if not self.is_new(j)]
        return new, old

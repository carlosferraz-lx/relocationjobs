"""Pipeline entry point: fetch -> match -> persist -> dashboard."""

from __future__ import annotations

import argparse
import logging
from concurrent.futures import ThreadPoolExecutor

from .config import Profile
from .matching import dedupe, match_all
from .models import Job
from .report import write_dashboard
from .sources import enabled_sources
from .store import SeenStore

log = logging.getLogger("jobfinder")


def fetch_all(profile: Profile) -> list[Job]:
    sources = enabled_sources(profile)
    jobs: list[Job] = []
    with ThreadPoolExecutor(max_workers=min(8, len(sources) or 1)) as pool:
        for result in pool.map(lambda s: s.safe_fetch(), sources):
            jobs.extend(result)
    return jobs


def run(profile_path: str | None = None, state_path: str | None = None,
        dry_run: bool = False) -> dict:
    profile = Profile.load(profile_path)
    log.info("Loaded profile for %s; sources=%s",
             profile.name,
             [n for n, on in profile.sources_enabled.items() if on])

    raw = fetch_all(profile)
    log.info("Fetched %d raw postings", len(raw))

    matches = dedupe(match_all(raw, profile))
    log.info("%d postings match the profile", len(matches))

    store = SeenStore(state_path)
    new_jobs, _ = store.partition(matches)
    new_uids = {j.uid for j in new_jobs}
    log.info("%d of them are new since last run", len(new_jobs))

    write_dashboard(profile, new_jobs, matches, new_uids)

    if not dry_run:
        for job in matches:
            store.mark(job)
        store.save()

    for job in new_jobs[:25]:
        loc = job.city or job.country or ("remote" if job.remote else "?")
        log.info("  NEW  [%5.1f] %-45.45s %-22.22s %s",
                 job.score, job.title, job.company, loc)

    return {"raw": len(raw), "matches": len(matches), "new": len(new_jobs)}


def main() -> None:
    parser = argparse.ArgumentParser(description="Daily relocation-aware QA job finder")
    parser.add_argument("--profile", default=None, help="path to profile.yaml")
    parser.add_argument("--state", default=None, help="path to seen_jobs.json")
    parser.add_argument("--dry-run", action="store_true",
                        help="don't update the seen-jobs state file")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    summary = run(args.profile, args.state, args.dry_run)
    log.info("Done: %(raw)d fetched, %(matches)d matched, %(new)d new", summary)


if __name__ == "__main__":
    main()

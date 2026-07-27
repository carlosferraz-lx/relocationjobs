"""Job source registry."""

from __future__ import annotations

from ..config import Profile
from .adzuna import Adzuna
from .arbeitnow import Arbeitnow
from .base import Source
from .himalayas import Himalayas
from .landingjobs import LandingJobs
from .nav import Nav
from .platsbanken import Platsbanken
from .remoteok import RemoteOK

_ALL: dict[str, type[Source]] = {
    "platsbanken": Platsbanken,
    "nav": Nav,
    "arbeitnow": Arbeitnow,
    "landingjobs": LandingJobs,
    "remoteok": RemoteOK,
    "himalayas": Himalayas,
    "adzuna": Adzuna,
}


def enabled_sources(profile: Profile) -> list[Source]:
    """Instantiate every source toggled on in the profile."""
    out: list[Source] = []
    for name, cls in _ALL.items():
        if profile.source_on(name):
            out.append(cls(profile))
    return out


__all__ = ["Source", "enabled_sources"]

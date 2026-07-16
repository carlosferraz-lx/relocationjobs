import pytest

from jobfinder.config import Profile


@pytest.fixture
def profile() -> Profile:
    """The real profile.yaml shipped in the repo."""
    return Profile.load()

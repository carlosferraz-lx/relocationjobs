from jobfinder.models import Job
from jobfinder.store import SeenStore


def test_profile_loads_expected_fields(profile):
    assert profile.current_gross_salary == 60000
    assert "GB" in profile.target_countries
    assert any(s.name == "playwright" for s in profile.skills)
    assert profile.source_on("platsbanken") is True


def test_seen_store_roundtrip(tmp_path):
    path = tmp_path / "seen.json"
    store = SeenStore(path)
    job = Job(source="nav", external_id="1", title="QA", company="c", url="u")

    assert store.is_new(job)
    store.mark(job)
    store.save()

    reopened = SeenStore(path)
    assert not reopened.is_new(job)


def test_partition_splits_new_and_seen(tmp_path):
    store = SeenStore(tmp_path / "seen.json")
    a = Job(source="nav", external_id="1", title="A", company="c", url="u")
    b = Job(source="nav", external_id="2", title="B", company="c", url="u")
    store.mark(a)
    new, old = store.partition([a, b])
    assert [j.external_id for j in new] == ["2"]
    assert [j.external_id for j in old] == ["1"]

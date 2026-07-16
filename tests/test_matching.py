from jobfinder.matching import dedupe, evaluate, match_all
from jobfinder.models import Job


def mk(**kw) -> Job:
    base = dict(source="test", external_id="1", title="QA Engineer",
                company="Acme", url="http://x", description="", country="SE")
    base.update(kw)
    return Job(**base)


def test_qa_in_eea_matches_without_relocation_signal(profile):
    # EU citizen + Sweden (EEA) -> no sponsorship needed, no signal required.
    job = mk(title="QA Automation Engineer",
             description="Selenium and Playwright test automation")
    res = evaluate(job, profile)
    assert res is not None
    assert "playwright" in res.matched_skills


def test_uk_requires_visa_sponsorship(profile):
    without = mk(title="SDET", country="GB",
                 description="Cypress and Playwright automation")
    assert evaluate(without, profile) is None

    with_visa = mk(title="SDET", country="GB", external_id="2",
                   description="Cypress automation. We offer visa sponsorship "
                               "and relocation support.")
    res = evaluate(with_visa, profile)
    assert res is not None
    assert res.relocation_signals


def test_non_qa_role_is_rejected(profile):
    job = mk(title="Head Chef", description="cooking pasta")
    assert evaluate(job, profile) is None


def test_non_target_country_rejected(profile):
    job = mk(title="QA Engineer", country="DE",
             description="Playwright automation")
    assert evaluate(job, profile) is None


def test_salary_below_floor_rejected(profile):
    job = mk(title="QA Engineer", city="Stockholm",
             description="Playwright automation",
             salary_min=100000, salary_max=100000, salary_currency="SEK",
             salary_period="year")
    assert evaluate(job, profile) is None


def test_salary_above_floor_flagged_above(profile):
    job = mk(title="QA Engineer", city="Stockholm",
             description="Playwright automation",
             salary_min=900000, salary_max=1000000, salary_currency="SEK",
             salary_period="year")
    res = evaluate(job, profile)
    assert res is not None
    assert res.salary_status == "above"
    assert res.salary_eur_year is not None


def test_remote_worldwide_without_country_rejected(profile):
    # A worldwide-remote role is not a relocation opportunity.
    job = mk(title="QA Automation Engineer", country=None, remote=True,
             description="Playwright automation, worldwide")
    assert evaluate(job, profile) is None


def test_remote_tied_to_target_country_included(profile):
    job = mk(title="QA Automation Engineer", country="GB", remote=True,
             description="Playwright automation, visa sponsorship available")
    res = evaluate(job, profile)
    assert res is not None
    assert res.remote


def test_language_requirement_penalised(profile):
    fluent = mk(title="QA Engineer", external_id="a",
                description="Playwright automation. Flytande svenska kravs.")
    plain = mk(title="QA Engineer", external_id="b",
               description="Playwright automation.")
    r1 = evaluate(fluent, profile)
    r2 = evaluate(plain, profile)
    assert r1.score < r2.score


def test_match_all_sorts_by_score_desc(profile):
    jobs = [
        mk(title="Tester", external_id="1", description="manual testing"),
        mk(title="QA Automation Engineer", external_id="2",
           description="Playwright Cypress Selenium api testing python"),
    ]
    ranked = match_all(jobs, profile)
    assert [j.external_id for j in ranked] == ["2", "1"]


def test_dedupe_removes_cross_source_duplicates():
    a = Job(source="nav", external_id="1", title="QA Engineer",
            company="Acme", url="u", country="NO")
    b = Job(source="himalayas", external_id="2", title="QA  Engineer",
            company="ACME", url="u2", country="NO")
    out = dedupe([a, b])
    assert len(out) == 1

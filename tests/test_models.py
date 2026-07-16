from jobfinder.models import Job, strip_html


def test_strip_html_collapses_and_unescapes():
    html = "<p>Hello&nbsp;&amp; welcome to <b>QA</b>   testing</p>"
    assert strip_html(html) == "Hello & welcome to QA testing"


def test_strip_html_handles_none():
    assert strip_html(None) == ""


def test_uid_is_stable_and_source_scoped():
    a = Job(source="nav", external_id="123", title="t", company="c", url="u")
    b = Job(source="nav", external_id="123", title="different", company="x", url="y")
    c = Job(source="platsbanken", external_id="123", title="t", company="c", url="u")
    assert a.uid == b.uid          # same source+id -> same uid
    assert a.uid != c.uid          # different source -> different uid


def test_haystack_is_lowercased_blob():
    j = Job(source="s", external_id="1", title="SDET Role", company="Acme",
            url="u", description="Playwright & Cypress", tags=["Automation"])
    hay = j.haystack
    assert "sdet" in hay and "playwright" in hay and "automation" in hay

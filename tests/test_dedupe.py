"""Duplicates: same link, or same company + same role; multi-city copies become one post."""

from conftest import make_post
from fresherjobs.dedupe import canon_url, dedupe, job_id


def test_merges_reposts_and_multi_city(rules):
    posts = [
        make_post("Software Engineer Intern (2026)", "Bengaluru", url="https://a.com/1?utm_source=x"),
        make_post("Software Engineer Intern - Hyderabad", "Hyderabad", url="https://a.com/2"),
        make_post("Software Engineer Intern", "Pune", company="Acme Pvt. Ltd.", url="https://a.com/3"),
        make_post("Data Analyst Intern", "Bengaluru", url="https://a.com/1"),        # same link as #1
        make_post("Software Engineer Intern", "Pune", company="Other Co", url="https://b.com/9"),
    ]
    out, merged = dedupe(posts, rules)
    assert merged == 3 and len(out) == 2
    acme = next(p for p in out if p["company"] == "Acme")
    assert rules.cities_in(acme["location"]) == ["Bengaluru", "Hyderabad", "Pune"]


def test_a_clear_copy_beats_an_unclear_one(rules):
    a = dict(make_post("Analyst", "Pune", url="https://a.com/1"), needs_ai=True)
    b = dict(make_post("Analyst", "Mumbai", url="https://a.com/2"), needs_ai=False)
    out, _ = dedupe([a, b], rules)
    assert out[0]["needs_ai"] is False


def test_id_is_stable_across_days(rules):
    assert job_id("Acme Pvt Ltd", "SDE Intern (2026) - Pune", rules) == job_id("Acme", "SDE Intern", rules)


def test_canon_url():
    assert canon_url("https://WWW.A.com/1/?utm_source=x&gh_jid=5") == "https://a.com/1?gh_jid=5"

"""Each source parses its provider's real response shape into the same RawPost fields."""

from fresherjobs import sources
from fresherjobs.sources import ashby, greenhouse, http, lever, smartrecruiters

RESPONSES = {
    "https://boards-api.greenhouse.io/v1/boards/acme": {"name": "Acme Labs"},
    "https://boards-api.greenhouse.io/v1/boards/acme/jobs": {"jobs": [{
        "title": "Software Engineer Intern", "absolute_url": "https://job-boards.greenhouse.io/acme/jobs/1",
        "location": {"name": "Bengaluru, India"}, "first_published": "2026-11-12T10:00:00Z",
        "content": "&lt;p&gt;Python &amp;amp; SQL&lt;/p&gt;"}]},
    "https://api.lever.co/v0/postings/acme": [{
        "text": "Marketing Intern", "hostedUrl": "https://jobs.lever.co/acme/2", "createdAt": 1794528000000,
        "categories": {"location": "Mumbai", "allLocations": ["Mumbai", "Pune"], "commitment": "Intern"},
        "descriptionPlain": "Social media", "workplaceType": "onsite"}],
    "https://api.ashbyhq.com/posting-api/job-board/acme": {"organizationName": "Acme", "jobs": [{
        "title": "Data Analyst Intern", "location": "Hyderabad", "secondaryLocations": [{"location": "Remote"}],
        "jobUrl": "https://jobs.ashbyhq.com/acme/3", "publishedAt": "2026-11-11T00:00:00Z",
        "descriptionPlain": "SQL", "isRemote": True, "compensation": {"compensationTierSummary": "₹30K/month"}}]},
    "https://api.smartrecruiters.com/v1/companies/Acme/postings": {"totalFound": 1, "content": [{
        "id": "77", "name": "HR Intern", "location": {"city": "Pune", "region": "MH", "remote": False},
        "releasedDate": "2026-11-09T00:00:00Z", "company": {"name": "Acme SR"}, "ref": "https://api/ref/77",
        "typeOfEmployment": {"label": "Internship"}}]},
}


def _fake_get(url, **kwargs):
    return RESPONSES[url]


def test_parsers(monkeypatch):
    for mod in (greenhouse, lever, ashby, smartrecruiters):
        monkeypatch.setattr(mod, "get_json", _fake_get)
    g = greenhouse.fetch("acme")[0]
    assert g["company"] == "Acme Labs" and g["description"] == "Python & SQL" and g["posted"] == "2026-11-12"
    lv = lever.fetch("acme")[0]
    assert lv["location"] == "Mumbai; Pune" and lv["posted"] == "2026-11-13"
    a = ashby.fetch("acme")[0]
    assert "(remote)" in a["location"] and a["pay"] == "₹30K/month"
    s = smartrecruiters.fetch("Acme", delay=0)[0]
    assert s["url"] == "https://jobs.smartrecruiters.com/Acme/77" and "India" in s["location"]


def test_dates_and_html():
    assert http.to_date(1794528000000) == "2026-11-13"
    assert http.to_date("2026-11-12T10:00:00Z") == "2026-11-12"
    assert http.to_date(None) == ""
    assert http.html_to_text("<p>One</p><p>Two &amp; three</p>") == "One\nTwo & three"


def test_one_bad_board_does_not_stop_the_run(monkeypatch):
    def down(slug):
        raise ConnectionError("down")

    def refused(slug):
        raise RuntimeError("429 Client Error: Too Many Requests")

    monkeypatch.setattr(sources, "FETCHERS", {"greenhouse": down, "lever": refused})
    monkeypatch.setattr(sources.time, "sleep", lambda s: None)
    logs = []
    posts, status = sources.fetch_all({"greenhouse": ["a"], "lever": ["b"]}, log=logs.append)
    assert posts == [] and status == {"greenhouse:a": False, "lever:b": False}
    assert any("refused automated requests (429)" in line for line in logs)

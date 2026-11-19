"""Each source parses its provider's real response shape into the same RawPost fields."""

from fresherjobs import sources
from fresherjobs.sources import ashby, breezy, greenhouse, http, keka, lever, recruitee, smartrecruiters, workable

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
    # shapes copied from real responses on 19 Nov 2026 (trimmed)
    "https://apply.workable.com/api/v1/widget/accounts/acme": {"name": "Acme W", "jobs": [{
        "title": "Design Intern", "url": "https://apply.workable.com/j/AB12", "published_on": "2026-11-15",
        "employment_type": "Full-time", "telecommuting": False, "experience": "Internship",
        "country": "India", "city": "Bengaluru", "state": "Karnataka",
        "locations": [{"country": "India", "countryCode": "IN", "city": "Bengaluru", "region": "Karnataka",
                       "hidden": False}],
        "description": "<p>Figma</p>"}]},
    "https://acme.recruitee.com/api/offers/": {"offers": [{
        "title": "Junior Analyst", "careers_url": "https://acme.recruitee.com/o/junior-analyst",
        "company_name": "Acme R", "published_at": "2026-11-14 09:00:00 UTC", "experience_code": "entry_level",
        "employment_type_code": "fulltime", "remote": False,
        "description": "<p>Excel</p>", "requirements": "<p>SQL</p>",
        "locations": [{"city": "Bangalore", "state": "Karnataka", "country": "India"}], "salary": {}}]},
    "https://acme.breezy.hr/json": [{
        "name": "HR Intern", "url": "https://acme.breezy.hr/p/1-hr-intern", "published_date": "2026-11-13T06:38:58Z",
        "type": {"name": "Internship"}, "company": {"name": "Acme B"}, "salary": "",
        "location": {"name": "India", "country": {"name": "India", "id": "IN"}, "is_remote": True},
        "locations": [{"name": "India", "country": {"name": "India", "id": "IN"}, "is_remote": True}]}],
    "https://acme.keka.com/careers/api/embedjobs/default/active/19d678f6-8b79-4532-a5f0-d57b593a822e": [{
        "id": 169089, "title": "Intern - Software Development", "description": "<div>Python</div>",
        "jobLocations": [{"city": "Bengaluru", "state": "Karnataka", "countryName": "India"}],
        "experience": "0 - 1 Years", "publishedOn": "2026-11-10T10:46:13.013Z", "salaryRangeFormat": ""}],
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


def test_new_platform_parsers(monkeypatch):
    for mod in (workable, recruitee, breezy, keka):
        monkeypatch.setattr(mod, "get_json", _fake_get)
    monkeypatch.setattr(keka, "portal_id", lambda t: "19d678f6-8b79-4532-a5f0-d57b593a822e")
    w = workable.fetch("acme")[0]
    assert w["company"] == "Acme W" and w["location"] == "Bengaluru, Karnataka, India"
    assert w["description"].startswith("Experience level: Internship") and w["posted"] == "2026-11-15"
    r = recruitee.fetch("acme")[0]
    assert r["location"] == "Bangalore, Karnataka, India" and "SQL" in r["description"] and r["posted"] == "2026-11-14"
    b = breezy.fetch("acme")[0]
    assert b["location"] == "India (remote)" and b["employment_type"] == "Internship"
    k = keka.fetch("acme")[0]
    assert k["url"] == "https://acme.keka.com/careers/jobdetails/169089"
    assert k["location"] == "Bengaluru, Karnataka, India"
    assert k["description"].startswith("Experience: 0 - 1 Years")


def test_keka_experience_line_feeds_the_years_rule():
    """Keka's "Experience: 2 - 4 Years" field must let the free rule drop experienced roles."""
    from fresherjobs.config import Paths, load_settings
    from fresherjobs.filters import Rules
    rules = Rules(load_settings(Paths()))
    post = {"title": "Associate - Business Operations", "location": "Bengaluru, India", "url": "https://x.keka.com/1",
            "description": "Experience: 2 - 4 Years\nRun weekly reports."}
    assert rules.entry_level(post)[0] is False


def test_keka_portal_id_from_careers_page(monkeypatch):
    class Page:
        text = "<script>fetch('/ats/documents/19d678f6-8b79-4532-a5f0-d57b593a822e/careerportal/x.html')</script>"
        def raise_for_status(self):
            pass
    monkeypatch.setattr(keka.requests, "get", lambda *a, **k: Page())
    assert keka.portal_id("acme") == "19d678f6-8b79-4532-a5f0-d57b593a822e"


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

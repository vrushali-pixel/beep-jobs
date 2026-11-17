"""Offline tests: no internet, no API key needed.   Run:  python -m pytest -q"""
import json
import os
import shutil
import subprocess
import sys
from types import SimpleNamespace

import pytest
import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)

from pipeline import fetch, tag  # noqa: E402
from pipeline.clean import Rules, canon_url, dedupe  # noqa: E402

CFG = yaml.safe_load(open("config.yaml"))
RULES = Rules(CFG)


def post(title, loc="Bengaluru, India", desc="", company="Acme", url=None, source="greenhouse", board="acme"):
    return {"source": source, "board": board, "company": company, "title": title,
            "url": url or f"https://x.com/{abs(hash(title + loc)) % 10**8}", "location": loc,
            "posted": "2026-11-10", "description": desc, "employment_type": "", "pay": ""}


# ---------- parsers: each API's real response shape ----------
def test_parsers(monkeypatch):
    responses = {
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
    monkeypatch.setattr(fetch, "_get", lambda url, **kw: responses[url])
    g = fetch.greenhouse("acme")[0]
    assert g["company"] == "Acme Labs" and g["description"] == "Python & SQL" and g["posted"] == "2026-11-12"
    lv = fetch.lever("acme")[0]
    assert lv["location"] == "Mumbai; Pune" and lv["posted"] == "2026-11-13"
    a = fetch.ashby("acme")[0]
    assert "(remote)" in a["location"] and a["pay"] == "₹30K/month"
    s = fetch.smartrecruiters("Acme", delay=0)[0]
    assert s["url"] == "https://jobs.smartrecruiters.com/Acme/77" and "India" in s["location"]


def test_one_bad_board_does_not_stop_run(monkeypatch):
    def boom(slug):
        raise ConnectionError("down")
    monkeypatch.setattr(fetch, "FETCHERS", {"greenhouse": boom})
    monkeypatch.setattr(fetch.time, "sleep", lambda s: None)
    posts, status = fetch.fetch_all({"greenhouse": ["a", "b"]}, log=lambda *a: None)
    assert posts == [] and status == {"greenhouse:a": False, "greenhouse:b": False}


# ---------- filters ----------
@pytest.mark.parametrize("p,why", [
    (post("Software Engineer Intern"), ""),
    (post("Graduate Engineer Trainee", "Pune, IN"), ""),
    (post("Senior Software Engineer"), "senior title"),
    (post("Engineering Manager"), "senior title"),
    (post("Software Engineer II"), "senior title"),
    (post("Software Engineer Intern", "San Francisco, CA"), "not in India"),
    (post("Software Engineer Intern", "Remote"), "not in India"),
    (post("Software Engineer Intern", "Remote", desc="Open to candidates across India"), ""),
    (post("Analyst", desc="Freshers welcome, 2026 batch"), ""),
    (post("Analyst", desc="3+ years experience"), "ai"),          # unclear: the LLM reads it
    (post("Operations Specialist", "The Philippines (Remote)", desc="We hire across India"), "not in India"),
    (post("Software Engineer Intern", "Remote - Anywhere", desc="team in India"), ""),
    (post("Data Entry Intern", desc="Pay a registration fee of Rs 999"), "asks for money (scam sign)"),
    (post("Software Engineer Intern", "Gurgaon"), ""),
])
def test_rules(p, why):
    assert RULES.check(p) == why


def test_tidy_company():
    from pipeline.clean import tidy_company
    assert [tidy_company(x) for x in ["Rubrik Job Board", "HackerRank Careers", "Stable Money1",
                                      "ZoomInfo Technologies LLC", "Bosch Group"]] == \
        ["Rubrik", "HackerRank", "Stable Money", "ZoomInfo Technologies", "Bosch Group"]


def test_city_aliases():
    assert RULES.cities_in("Bangalore; Gurgaon, Haryana; Navi Mumbai") == ["Bengaluru", "Mumbai", "Gurugram"]


# ---------- de-dupe ----------
def test_dedupe_merges_reposts_and_multi_city():
    ps = [
        post("Software Engineer Intern (2026)", "Bengaluru", url="https://a.com/1?utm_source=x"),
        post("Software Engineer Intern - Hyderabad", "Hyderabad", url="https://a.com/2"),
        post("Software Engineer Intern", "Pune", company="Acme Pvt. Ltd.", url="https://a.com/3"),
        post("Data Analyst Intern", "Bengaluru", url="https://a.com/1"),            # same link as #1
        post("Software Engineer Intern", "Pune", company="Other Co", url="https://b.com/9"),
    ]
    out, dups = dedupe(ps, RULES)
    assert dups == 3 and len(out) == 2
    merged = next(p for p in out if p["company"] == "Acme")
    assert RULES.cities_in(merged["location"]) == ["Bengaluru", "Hyderabad", "Pune"]
    assert canon_url("https://WWW.A.com/1/?utm_source=x") == "https://a.com/1"


# ---------- LLM tagging (mocked client) ----------
def test_tagger_uses_llm_output_and_caches(tmp_path, monkeypatch):
    calls = []

    class FakeClient:
        class messages:
            @staticmethod
            def create(**kw):
                calls.append(kw)
                ids = [p["id"] for p in json.loads(kw["messages"][0]["content"].split("\n", 1)[1])]
                out = [{"id": i, "entry_level": True, "role_group": "data_ai", "clean_title": "Data Analyst Intern",
                        "cities": ["Bengaluru", "Atlantis"], "job_type": "internship", "skills": ["SQL"],
                        "eligibility": "", "pay": "", "red_flags": []} for i in ids[:-1]]  # drops last one
                return SimpleNamespace(usage=SimpleNamespace(input_tokens=1000, output_tokens=200),
                                       content=[SimpleNamespace(type="tool_use", input={"posts": out})])

    t = tag.Tagger(CFG, RULES, cache_path=str(tmp_path / "c.json"))
    t.client = FakeClient()
    ps, _ = dedupe([post("Data Analyst Intern", c) for c in ("Bengaluru", "Delhi")] +
                   [post("HR Intern"), post("Coding Intern")], RULES)
    res = t.tag(ps, log=lambda *a: None)
    assert len(calls) == 1 and t.usage["input_tokens"] == 1000
    llm = [r for r in res.values() if r["tagger"] == CFG["llm"]["model"]]
    assert llm and all(r["cities"] == ["Bengaluru"] for r in llm)       # invalid city dropped
    assert t.usage["posts_fallback"] == 1                                 # missing one -> keyword tagger
    assert calls[0]["tool_choice"]["name"] == "save_tags"
    # Every argument we send must exist in the REAL SDK (a fake client hid a bug once).
    import inspect
    import anthropic
    real = set(inspect.signature(anthropic.resources.Messages.create).parameters)
    assert set(calls[0]) <= real, set(calls[0]) - real
    t.tag(ps, log=lambda *a: None)                                       # cached -> only retries fallback
    assert len(calls) == 2 and len(json.loads(calls[1]["messages"][0]["content"].split("\n", 1)[1])) == 1


def test_prompt_lists_every_role_and_city():
    p = tag.build_prompt(CFG)
    assert all(k in p for k in CFG["roles"]) and all(c in p for c in CFG["cities"]) and "{" not in p


# ---------- full run over two days, offline ----------
def test_end_to_end_two_days(tmp_path):
    work = tmp_path / "repo"
    shutil.copytree(ROOT, work, ignore=shutil.ignore_patterns(".git", "data", "__pycache__", ".pytest_cache"))
    os.makedirs(work / "data")
    day1 = [post("Software Engineer Intern", "Bengaluru", board="acme"),
            post("Software Engineer Intern (2026)", "Hyderabad", board="acme"),
            post("Marketing Intern", "Mumbai", board="acme"),
            post("Senior Data Scientist", "Pune", board="acme"),
            post("Business Analyst", "Pune", board="acme"),      # unclear title, no LLM key -> held back
            post("HR Intern", "Pune", board="beta", source="lever", company="Beta")]
    day2 = [day1[0], post("Finance Trainee", "Chennai", board="acme")]   # marketing gone; beta board not fetched
    (work / "d1.json").write_text(json.dumps(day1))
    (work / "d2.json").write_text(json.dumps(day2))
    env = {k: v for k, v in os.environ.items() if k != "ANTHROPIC_API_KEY"}
    run = lambda f, d: subprocess.run([sys.executable, "-m", "pipeline.run", "--offline", f, "--today", d],
                                      cwd=work, env=env, capture_output=True, text=True, check=True)
    run("d1.json", "2026-11-17")
    s1 = json.load(open(work / "site/jobs.json"))
    assert s1["stats"]["live"] == 3 and s1["stats"]["duplicates_merged"] == 1
    assert s1["stats"]["rejected_by_rules"]["unclear title (no LLM key to check)"] == 1
    run("d2.json", "2026-11-18")
    s2 = json.load(open(work / "site/jobs.json"))
    titles = sorted(j["original_title"] for j in s2["jobs"])
    # Marketing closed (its board answered without it); HR kept (its board was not checked today)
    assert titles == ["Finance Trainee", "HR Intern", "Software Engineer Intern"]
    sw = next(j for j in s2["jobs"] if j["original_title"] == "Software Engineer Intern")
    assert sw["first_seen"] == "2026-11-17" and sorted(sw["cities"]) == ["Bengaluru", "Hyderabad"]
    assert s2["stats"]["new_today"] == 1 and s2["stats"]["closed_today"] == 1
    assert len((work / "data/runs.jsonl").read_text().splitlines()) == 2

"""End to end over two days, offline: new, kept, closed, held-back posts; plus store and CLI."""

import json
import os
import shutil
import subprocess
import sys

from conftest import ROOT, make_post
from fresherjobs import store


def _copy_repo(tmp_path):
    work = tmp_path / "repo"
    shutil.copytree(ROOT, work, ignore=shutil.ignore_patterns(".git", "data", "__pycache__", ".pytest_cache",
                                                             "*.egg-info", "eval"))
    os.makedirs(work / "data")
    return work


def _read(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def test_end_to_end_two_days(tmp_path):
    work = _copy_repo(tmp_path)
    day1 = [make_post("Software Engineer Intern", "Bengaluru"),
            make_post("Software Engineer Intern (2026)", "Hyderabad"),
            make_post("Marketing Intern", "Mumbai"),
            make_post("Senior Data Scientist", "Pune"),
            make_post("Business Analyst", "Pune"),                       # unclear, no LLM key -> held back
            make_post("HR Intern", "Pune", board="beta", source="lever", company="Beta")]
    day2 = [day1[0], make_post("Finance Trainee", "Chennai")]           # marketing gone; beta not fetched
    (work / "d1.json").write_text(json.dumps(day1))
    (work / "d2.json").write_text(json.dumps(day2))
    env = {k: v for k, v in os.environ.items() if k not in ("ANTHROPIC_API_KEY", "GEMINI_API_KEY")}
    env["PYTHONPATH"] = str(work / "src")

    def run(file, day):
        subprocess.run([sys.executable, "-m", "fresherjobs", "run", "--offline", file, "--today", day],
                       cwd=work, env=env, capture_output=True, text=True, check=True)

    run("d1.json", "2026-11-17")
    s1 = _read(work / "site/jobs.json")
    assert s1["stats"]["live"] == 3 and s1["stats"]["duplicates_merged"] == 1
    assert s1["stats"]["rejected_by_rules"] == {"senior title": 1, "unclear title (no LLM key to check)": 1}

    run("d2.json", "2026-11-18")
    s2 = _read(work / "site/jobs.json")
    titles = sorted(j["original_title"] for j in s2["jobs"])
    assert titles == ["Finance Trainee", "HR Intern", "Software Engineer Intern"]
    sw = next(j for j in s2["jobs"] if j["original_title"] == "Software Engineer Intern")
    assert sw["first_seen"] == "2026-11-17" and sw["cities"] == ["Bengaluru"]   # Hyderabad copy is gone
    assert s2["stats"]["new_today"] == 1 and s2["stats"]["closed_today"] == 1
    assert len((work / "data/runs.jsonl").read_text().splitlines()) == 2
    assert (work / "data/jobs.csv").read_text().count("\n") == 4             # header + 3 live posts


def test_store_expires_posts_from_a_board_that_stays_down(cfg, rules):
    db = {"jobs": {"x": {"id": "x", "source": "lever", "board": "b", "status": "active",
                         "last_seen": "2026-10-01", "first_seen": "2026-10-01", "posted": ""}}}
    counts = store.merge(db, [], {"lever:b": False}, cfg, rules, "2026-11-17")
    assert counts == {"new": 0, "closed": 0, "expired": 1} and db["jobs"]["x"]["status"] == "expired"


def test_store_closes_posts_from_a_removed_source(cfg, rules):
    db = {"jobs": {"w": {"id": "w", "source": "workday", "board": "kaleris", "status": "active",
                         "last_seen": "2026-11-16", "first_seen": "2026-11-16", "posted": ""}}}
    counts = store.merge(db, [], {"lever:b": True}, cfg, rules, "2026-11-17", configured={"lever:b"})
    assert counts["closed"] == 1 and db["jobs"]["w"]["status"] == "closed"


def test_cli_version():
    out = subprocess.run([sys.executable, "-m", "fresherjobs", "--version"], capture_output=True, text=True,
                         env={**os.environ, "PYTHONPATH": os.path.join(ROOT, "src")}, check=True)
    assert out.stdout.strip() == "1.0.0"

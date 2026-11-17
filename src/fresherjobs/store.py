"""Step 6, MERGE WITH YESTERDAY: keep first_seen, mark gone posts closed, expire stale ones.

A post missing today is "closed" only if its board answered today. If the board was down,
the post is kept (it is probably still open) until `expire_after_days` without being seen.
A post from a board that is no longer in config/companies.yaml is closed (source removed).
"""

from __future__ import annotations

import json
import os
from datetime import date, timedelta
from typing import Any

from fresherjobs.filters import Rules
from fresherjobs.models import Job, RawPost, Tags


def load_db(path: str) -> dict[str, Any]:
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return {"jobs": {}}


def to_job(p: RawPost, t: Tags, cfg: dict[str, Any], rules: Rules, today: str, old: Job | None) -> Job:
    return {
        "id": p["id"], "title": t["clean_title"] or p["title"], "original_title": p["title"],
        "company": p["company"], "location": p["location"],
        "cities": t["cities"] or rules.cities_in(p["location"]),
        "role": t["role_group"], "role_label": cfg["roles"][t["role_group"]]["label"],
        "type": t["job_type"], "type_label": cfg["job_types"][t["job_type"]],
        "skills": t["skills"], "eligibility": t["eligibility"], "pay": t["pay"] or p.get("pay", ""),
        "url": p["url"], "source": p["source"], "board": p["board"], "posted": p["posted"],
        "tagger": t.get("tagger", ""),
        "first_seen": old["first_seen"] if old else today, "last_seen": today, "status": "active",
    }


def merge(db: dict[str, Any], accepted: list[tuple[RawPost, Tags]], board_status: dict[str, bool],
          cfg: dict[str, Any], rules: Rules, today: str, configured: set[str] | None = None) -> dict[str, int]:
    """Update db in place. Returns counts: new, closed, expired.

    configured: every board the run tried (None in offline tests, where it is unknown).
    """
    jobs: dict[str, Job] = db["jobs"]
    seen: set[str] = set()
    new = 0
    for p, t in accepted:
        old = jobs.get(p["id"])
        new += old is None or old.get("status") != "active"
        jobs[p["id"]] = to_job(p, t, cfg, rules, today, old)
        seen.add(p["id"])

    closed = expired = 0
    limit = (date.fromisoformat(today) - timedelta(days=cfg["refresh"]["expire_after_days"])).isoformat()
    for j in jobs.values():
        if j["id"] in seen or j["status"] != "active":
            continue
        key = f"{j['source']}:{j['board']}"
        if board_status.get(key) or (configured is not None and key not in configured):
            j["status"], j["closed_on"] = "closed", today       # board answered without it, or source removed
            closed += 1
        elif j["last_seen"] < limit:
            j["status"] = "expired"                              # board down for too long
            expired += 1
    return {"new": new, "closed": closed, "expired": expired}


def live_jobs(db: dict[str, Any]) -> list[Job]:
    """Active posts, newest first."""
    return sorted((j for j in db["jobs"].values() if j["status"] == "active"),
                  key=lambda j: (j["first_seen"], j["posted"] or ""), reverse=True)

"""Workday career-site search (large MNCs).

This is the search the public careers page itself sends; Workday has no documented public API.
In practice every Workday site refused requests from GitHub's servers with HTTP 429, so this
source is OFF (`workday_enabled: false`). See docs/decisions/0003-workday.md.
"""

from __future__ import annotations

import time
from typing import Any

from fresherjobs.models import RawPost
from fresherjobs.sources.http import get_json, html_to_text, post_json, to_date

QUERIES = ("intern", "graduate", "trainee", "fresher", "apprentice")


def fetch(entry: dict[str, Any], delay: float = 0.5) -> list[RawPost]:
    host, tenant, site = entry["host"], entry["tenant"], entry["site"]
    api = f"https://{host}/wday/cxs/{tenant}/{site}"
    seen: set[str] = set()
    out: list[RawPost] = []
    for q in QUERIES:
        body = {"appliedFacets": {}, "limit": 20, "offset": 0, "searchText": q}
        for j in post_json(f"{api}/jobs", body).get("jobPostings", []):
            path = j.get("externalPath")
            if not path or path in seen:
                continue
            seen.add(path)
            out.append({
                "source": "workday", "board": tenant, "company": entry["company"],
                "title": j.get("title", ""), "url": f"https://{host}/{site}{path}",
                "location": j.get("locationsText", ""), "posted": "",
                "description": "", "_detail": f"{api}{path}",
                "employment_type": "", "pay": "",
            })
        time.sleep(delay)
    return out


def detail(post: RawPost) -> RawPost:
    info = get_json(post["_detail"]).get("jobPostingInfo") or {}
    post["description"] = html_to_text(info.get("jobDescription"))
    locs = [info.get("location"), *(info.get("additionalLocations") or [])]
    post["location"] = ", ".join(x for x in locs if x) or post["location"]
    post["posted"] = to_date(info.get("startDate"))
    return post

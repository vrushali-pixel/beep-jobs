"""Ashby Job Postings API: https://api.ashbyhq.com/posting-api/job-board/<slug>"""

from __future__ import annotations

from fresherjobs.models import RawPost
from fresherjobs.sources.http import get_json, html_to_text, to_date

API = "https://api.ashbyhq.com/posting-api/job-board"


def fetch(slug: str) -> list[RawPost]:
    data = get_json(f"{API}/{slug}", params={"includeCompensation": "true"})
    out: list[RawPost] = []
    for j in data.get("jobs", []):
        locs = [j.get("location", "")] + [s.get("location", "") for s in j.get("secondaryLocations") or []]
        out.append({
            "source": "ashby", "board": slug, "company": data.get("organizationName") or slug.title(),
            "title": j.get("title", ""), "url": j.get("jobUrl", ""),
            "location": "; ".join(x for x in locs if x) + (" (remote)" if j.get("isRemote") else ""),
            "posted": to_date(j.get("publishedAt")),
            "description": j.get("descriptionPlain") or html_to_text(j.get("descriptionHtml")),
            "employment_type": j.get("employmentType", ""),
            "pay": (j.get("compensation") or {}).get("compensationTierSummary") or "",
        })
    return out

"""Greenhouse Job Board API: https://boards-api.greenhouse.io/v1/boards/<slug>/jobs"""

from __future__ import annotations

from fresherjobs.models import RawPost
from fresherjobs.sources.http import get_json, html_to_text, to_date

API = "https://boards-api.greenhouse.io/v1/boards"


def fetch(slug: str) -> list[RawPost]:
    meta = get_json(f"{API}/{slug}")
    data = get_json(f"{API}/{slug}/jobs", params={"content": "true"})
    company = meta.get("name") or slug
    return [
        {
            "source": "greenhouse", "board": slug, "company": company,
            "title": j.get("title", ""), "url": j.get("absolute_url", ""),
            "location": (j.get("location") or {}).get("name", ""),
            "posted": to_date(j.get("first_published") or j.get("updated_at")),
            "description": html_to_text(j.get("content")),
            "employment_type": "", "pay": "",
        }
        for j in data.get("jobs", [])
    ]

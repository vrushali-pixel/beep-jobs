"""Workable public jobs widget: https://apply.workable.com/api/v1/widget/accounts/<slug>?details=true

This is the endpoint Workable documents for showing a company's published jobs on its own
website (no key, no login). One call returns the whole board, descriptions included.
"""

from __future__ import annotations

from typing import Any

from fresherjobs.models import RawPost
from fresherjobs.sources.http import get_json, html_to_text, to_date

API = "https://apply.workable.com/api/v1/widget/accounts"


def _place(loc: dict[str, Any]) -> str:
    return ", ".join(x for x in (loc.get("city"), loc.get("region") or loc.get("state"), loc.get("country")) if x)


def fetch(slug: str) -> list[RawPost]:
    data = get_json(f"{API}/{slug}", params={"details": "true"})
    out: list[RawPost] = []
    for j in data.get("jobs", []):
        places = [_place(x) for x in j.get("locations") or [] if not x.get("hidden")] or [_place(j)]
        level = j.get("experience") or ""
        desc = html_to_text(j.get("description"))
        company = data.get("name") or slug.replace("-", " ").title()
        remote = " (remote)" if j.get("telecommuting") else ""
        out.append({
            "source": "workable", "board": slug, "company": company,
            "title": j.get("title", ""), "url": j.get("url") or j.get("shortlink", ""),
            "location": "; ".join(dict.fromkeys(p for p in places if p)) + remote,
            "posted": to_date(j.get("published_on") or j.get("created_at")),
            # Workable's own level ("Entry level", "Internship", "Mid-Senior level") helps the AI decide
            "description": (f"Experience level: {level}\n" if level else "") + desc,
            "employment_type": j.get("employment_type", ""), "pay": "",
        })
    return out

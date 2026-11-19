"""Breezy HR public job feed: https://<slug>.breezy.hr/json

The JSON the company's Breezy careers page is built from. It has no description text, so for
unclear titles the AI decides from the title, company and location only.
"""

from __future__ import annotations

from typing import Any

from fresherjobs.models import RawPost
from fresherjobs.sources.http import get_json, to_date


def _place(loc: dict[str, Any]) -> str:
    country = (loc.get("country") or {}).get("name", "")
    name = loc.get("name") or ""
    return name if country and country in name else ", ".join(x for x in (name, country) if x)


def fetch(slug: str) -> list[RawPost]:
    out: list[RawPost] = []
    for j in get_json(f"https://{slug}.breezy.hr/json"):
        locs = j.get("locations") or [j.get("location") or {}]
        remote = any(x.get("is_remote") for x in locs)
        out.append({
            "source": "breezy", "board": slug, "company": (j.get("company") or {}).get("name") or slug.title(),
            "title": j.get("name", ""), "url": j.get("url", ""),
            "location": "; ".join(dict.fromkeys(p for p in map(_place, locs) if p)) + (" (remote)" if remote else ""),
            "posted": to_date(j.get("published_date")),
            "description": "",
            "employment_type": (j.get("type") or {}).get("name", ""),
            "pay": j.get("salary") or "",
        })
    return out

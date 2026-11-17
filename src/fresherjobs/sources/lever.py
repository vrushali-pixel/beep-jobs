"""Lever Postings API: https://api.lever.co/v0/postings/<slug>?mode=json (slugs can be case-sensitive)."""

from __future__ import annotations

from typing import Any

from fresherjobs.models import RawPost
from fresherjobs.sources.http import get_json, html_to_text, to_date

API = "https://api.lever.co/v0/postings"


def _pay(sr: dict[str, Any] | None) -> str:
    if not sr or not sr.get("min"):
        return ""
    return f"{sr.get('currency', '')} {sr['min']}-{sr.get('max', '')} {sr.get('interval', '')}".strip()


def fetch(slug: str) -> list[RawPost]:
    out: list[RawPost] = []
    for j in get_json(f"{API}/{slug}", params={"mode": "json"}):
        cat = j.get("categories") or {}
        locs = cat.get("allLocations") or [cat.get("location", "")]
        out.append({
            "source": "lever", "board": slug, "company": slug.replace("-", " ").title(),
            "title": j.get("text", ""), "url": j.get("hostedUrl", ""),
            "location": "; ".join(x for x in locs if x) + (" (remote)" if j.get("workplaceType") == "remote" else ""),
            "posted": to_date(j.get("createdAt")),
            "description": j.get("descriptionPlain") or html_to_text(j.get("description")),
            "employment_type": cat.get("commitment", ""),
            "pay": _pay(j.get("salaryRange")),
        })
    return out

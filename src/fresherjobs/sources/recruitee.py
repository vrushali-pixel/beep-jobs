"""Recruitee Careers Site API: https://<slug>.recruitee.com/api/offers/

Recruitee documents this as public ("does not require authorization"); it is what a company's
own careers site reads. One call returns every published offer with its description.
"""

from __future__ import annotations

from typing import Any

from fresherjobs.models import RawPost
from fresherjobs.sources.http import get_json, html_to_text, to_date


def _place(loc: dict[str, Any]) -> str:
    return ", ".join(x for x in (loc.get("city"), loc.get("state") or loc.get("state_name"), loc.get("country")) if x)


def _pay(s: dict[str, Any] | None) -> str:
    if not s or not s.get("min"):
        return ""
    return f"{s.get('currency', '')} {s['min']}-{s.get('max') or ''} {s.get('period', '')}".strip()


def fetch(slug: str) -> list[RawPost]:
    data = get_json(f"https://{slug}.recruitee.com/api/offers/")
    out: list[RawPost] = []
    for j in data.get("offers", []):
        places = [_place(x) for x in j.get("locations") or []] or [_place(j) or j.get("location", "")]
        level = (j.get("experience_code") or "").replace("_", " ")
        desc = html_to_text((j.get("description") or "") + "\n" + (j.get("requirements") or ""))
        out.append({
            "source": "recruitee", "board": slug, "company": j.get("company_name") or slug.title(),
            "title": j.get("title", ""), "url": j.get("careers_url", ""),
            "location": "; ".join(dict.fromkeys(p for p in places if p)) + (" (remote)" if j.get("remote") else ""),
            "posted": to_date(j.get("published_at") or j.get("created_at")),
            "description": (f"Experience level: {level}\n" if level else "") + desc,
            "employment_type": (j.get("employment_type_code") or "").replace("_", " "),
            "pay": _pay(j.get("salary")),
        })
    return out

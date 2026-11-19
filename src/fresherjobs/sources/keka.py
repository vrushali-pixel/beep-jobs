"""Keka Hire careers portal (used by many Indian startups): https://<tenant>.keka.com/careers/

Keka's robots.txt says "Disallow: /" but "Allow: /careers/", so we read ONLY under /careers/:
  1. the careers page itself, to find the portal id (a GUID in the page's own links)
  2. /careers/api/embedjobs/default/active/<portal id>, the job list Keka's "Embed jobs"
     widget gives companies for their websites
"""

from __future__ import annotations

import re
from typing import Any

import requests

from fresherjobs.models import RawPost
from fresherjobs.sources.http import HEADERS, TIMEOUT, get_json, html_to_text, to_date

_PORTAL_ID = re.compile(r"/ats/documents/([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})/")


def portal_id(tenant: str) -> str:
    r = requests.get(f"https://{tenant}.keka.com/careers/", headers=HEADERS, timeout=TIMEOUT)
    r.raise_for_status()
    m = _PORTAL_ID.search(r.text)
    if not m:
        raise ValueError("no Keka portal id on the careers page (older Keka page)")
    return m.group(1)


def _place(loc: Any) -> str:
    if isinstance(loc, str):
        return loc
    if not isinstance(loc, dict):
        return ""
    parts = [loc.get(k) for k in ("city", "state", "countryName", "country")]
    parts = [p for p in parts if isinstance(p, str) and p]
    return ", ".join(dict.fromkeys(parts)) or str(loc.get("name") or loc.get("label") or "")


def fetch(tenant: str) -> list[RawPost]:
    pid = portal_id(tenant)
    jobs = get_json(f"https://{tenant}.keka.com/careers/api/embedjobs/default/active/{pid}")
    out: list[RawPost] = []
    for j in jobs:
        places = [p for p in map(_place, j.get("jobLocations") or []) if p]
        exp = (j.get("experience") or "").strip()
        out.append({
            "source": "keka", "board": tenant, "company": tenant.replace("-", " ").title(),
            "title": j.get("title", ""), "url": f"https://{tenant}.keka.com/careers/jobdetails/{j.get('id')}",
            "location": "; ".join(dict.fromkeys(places)),
            "posted": to_date(j.get("publishedOn")),
            # "Experience: 2 - 4 Years" lets the plain years rule drop experienced roles for free
            "description": (f"Experience: {exp}\n" if exp else "") + html_to_text(j.get("description")),
            "employment_type": "", "pay": j.get("salaryRangeFormat") or "",
        })
    return out

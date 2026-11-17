"""SmartRecruiters Posting API, filtered to India: /v1/companies/<id>/postings?country=in

The list has no description, so `detail()` fetches it, but only for posts that pass the
cheap filters first (saves hundreds of requests a day).
"""

from __future__ import annotations

import time

from fresherjobs.models import RawPost
from fresherjobs.sources.http import get_json, html_to_text, to_date

API = "https://api.smartrecruiters.com/v1/companies"


def fetch(company_id: str, delay: float = 0.5) -> list[RawPost]:
    out: list[RawPost] = []
    offset = 0
    while True:
        data = get_json(f"{API}/{company_id}/postings", params={"country": "in", "limit": 100, "offset": offset})
        items = data.get("content", [])
        for j in items:
            loc = j.get("location") or {}
            out.append({
                "source": "smartrecruiters", "board": company_id,
                "company": (j.get("company") or {}).get("name") or company_id,
                "title": j.get("name", ""),
                "url": f"https://jobs.smartrecruiters.com/{company_id}/{j.get('id')}",
                "location": ", ".join(x for x in [loc.get("city"), loc.get("region"), "India"] if x)
                + (" (remote)" if loc.get("remote") else ""),
                "posted": to_date(j.get("releasedDate")),
                "description": "", "_detail": j.get("ref"),
                "employment_type": (j.get("typeOfEmployment") or {}).get("label", ""),
                "pay": "",
            })
        offset += len(items)
        if not items or offset >= data.get("totalFound", 0):
            return out
        time.sleep(delay)


def detail(post: RawPost) -> RawPost:
    if post.get("_detail"):
        sections = (get_json(post["_detail"]).get("jobAd") or {}).get("sections") or {}
        post["description"] = html_to_text(" ".join((sections.get(k) or {}).get("text", "")
                                                    for k in ("jobDescription", "qualifications")))
    return post

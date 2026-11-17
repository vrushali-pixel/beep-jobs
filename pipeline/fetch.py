"""Step 1: FETCH. Read each company's official job board through its public postings API.

Every fetcher returns a list of "raw posts" with the same fields:
  source, board, company, title, url, location, posted (YYYY-MM-DD or ""),
  description (plain text), employment_type, pay
"""
import html
import re
import time
from datetime import datetime, timezone

import requests

HEADERS = {"User-Agent": "beep-fresher-jobs/1.0 (student job finder; contact via repo)"}
TIMEOUT = 20


def _get(url, **kw):
    r = requests.get(url, headers=HEADERS, timeout=TIMEOUT, **kw)
    r.raise_for_status()
    return r.json()


def html_to_text(s):
    if not s:
        return ""
    s = html.unescape(s)                      # Greenhouse sends escaped HTML
    s = re.sub(r"<(br|/p|/li|/h\d)[^>]*>", "\n", s, flags=re.I)
    s = re.sub(r"<[^>]+>", " ", s)
    s = html.unescape(s)
    return re.sub(r"[ \t\r\f\v]+", " ", re.sub(r"\n\s*\n+", "\n", s)).strip()


def _date(value):
    """Accept ISO strings or epoch milliseconds; return YYYY-MM-DD."""
    if not value:
        return ""
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value / 1000, tz=timezone.utc).date().isoformat()
    return str(value)[:10]


def greenhouse(slug):
    meta = _get(f"https://boards-api.greenhouse.io/v1/boards/{slug}")
    data = _get(f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs", params={"content": "true"})
    company = meta.get("name") or slug
    out = []
    for j in data.get("jobs", []):
        out.append({
            "source": "greenhouse", "board": slug, "company": company,
            "title": j.get("title", ""), "url": j.get("absolute_url", ""),
            "location": (j.get("location") or {}).get("name", ""),
            "posted": _date(j.get("first_published") or j.get("updated_at")),
            "description": html_to_text(j.get("content")),
            "employment_type": "", "pay": "",
        })
    return out


def _lever_pay(sr):
    if not sr or not sr.get("min"):
        return ""
    return f"{sr.get('currency', '')} {sr['min']}-{sr.get('max', '')} {sr.get('interval', '')}".strip()


def lever(slug):
    data = _get(f"https://api.lever.co/v0/postings/{slug}", params={"mode": "json"})
    out = []
    for j in data:
        cat = j.get("categories") or {}
        locs = cat.get("allLocations") or [cat.get("location", "")]
        out.append({
            "source": "lever", "board": slug, "company": slug.replace("-", " ").title(),
            "title": j.get("text", ""), "url": j.get("hostedUrl", ""),
            "location": "; ".join(l for l in locs if l) + (" (remote)" if j.get("workplaceType") == "remote" else ""),
            "posted": _date(j.get("createdAt")),
            "description": j.get("descriptionPlain") or html_to_text(j.get("description")),
            "employment_type": cat.get("commitment", ""),
            "pay": _lever_pay(j.get("salaryRange")),
        })
    return out


def ashby(slug):
    data = _get(f"https://api.ashbyhq.com/posting-api/job-board/{slug}", params={"includeCompensation": "true"})
    out = []
    for j in data.get("jobs", []):
        locs = [j.get("location", "")] + [s.get("location", "") for s in j.get("secondaryLocations") or []]
        comp = (j.get("compensation") or {}).get("compensationTierSummary") or ""
        out.append({
            "source": "ashby", "board": slug, "company": data.get("organizationName") or slug.title(),
            "title": j.get("title", ""), "url": j.get("jobUrl", ""),
            "location": "; ".join(l for l in locs if l) + (" (remote)" if j.get("isRemote") else ""),
            "posted": _date(j.get("publishedAt")),
            "description": j.get("descriptionPlain") or html_to_text(j.get("descriptionHtml")),
            "employment_type": j.get("employmentType", ""), "pay": comp,
        })
    return out


def smartrecruiters(company_id, delay=0.5):
    """List endpoint filtered to India; the description needs one extra call per post."""
    out, offset = [], 0
    while True:
        data = _get(f"https://api.smartrecruiters.com/v1/companies/{company_id}/postings",
                    params={"country": "in", "limit": 100, "offset": offset})
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
                "posted": _date(j.get("releasedDate")),
                "description": "", "_detail": j.get("ref"),
                "employment_type": (j.get("typeOfEmployment") or {}).get("label", ""),
                "pay": "",
            })
        offset += len(items)
        if not items or offset >= data.get("totalFound", 0):
            break
        time.sleep(delay)
    return out


def smartrecruiters_detail(post):
    """Called only for posts that passed the cheap filters, to save requests."""
    if not post.get("_detail"):
        return post
    d = _get(post["_detail"])
    sections = (d.get("jobAd") or {}).get("sections") or {}
    post["description"] = html_to_text(" ".join((sections.get(k) or {}).get("text", "")
                                                for k in ("jobDescription", "qualifications")))
    return post


def workday(entry, delay=0.5, queries=("intern", "graduate", "trainee", "fresher", "apprentice")):
    """Workday careers-site search. Off by default; see companies.yaml."""
    host, tenant, site = entry["host"], entry["tenant"], entry["site"]
    api = f"https://{host}/wday/cxs/{tenant}/{site}"
    seen, out = set(), []
    for q in queries:
        r = requests.post(f"{api}/jobs", json={"appliedFacets": {}, "limit": 20, "offset": 0, "searchText": q},
                          headers=HEADERS, timeout=TIMEOUT)
        r.raise_for_status()
        for j in r.json().get("jobPostings", []):
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


def workday_detail(post):
    info = (_get(post["_detail"]).get("jobPostingInfo") or {})
    post["description"] = html_to_text(info.get("jobDescription"))
    post["location"] = ", ".join(x for x in [info.get("location"), *(info.get("additionalLocations") or [])] if x) or post["location"]
    post["posted"] = _date(info.get("startDate"))
    return post


FETCHERS = {"greenhouse": greenhouse, "lever": lever, "ashby": ashby, "smartrecruiters": smartrecruiters}
DETAIL = {"smartrecruiters": smartrecruiters_detail, "workday": workday_detail}


def fetch_all(companies, delay=0.5, log=print):
    """Return (posts, source_status). source_status[key] is True when that board answered.

    A board that fails today is remembered as failed, so its old posts are NOT expired
    just because the site was down (that bug would wipe good posts).
    """
    posts, status = [], {}
    for kind, fn in FETCHERS.items():
        for slug in companies.get(kind) or []:
            key = f"{kind}:{slug}"
            try:
                got = fn(slug) if kind != "smartrecruiters" else fn(slug, delay)
                posts += got
                status[key] = True
            except Exception as e:  # one bad board must never stop the run
                status[key] = False
                log(f"  ! {key}: {type(e).__name__} {str(e)[:80]}")
            time.sleep(delay)
    if companies.get("workday_enabled"):
        for entry in companies.get("workday") or []:
            key = f"workday:{entry['tenant']}"
            try:
                posts += workday(entry, delay)
                status[key] = True
            except Exception as e:
                status[key] = False
                if "429" in str(e):     # the site asked us to stop: respect it, no retries
                    log(f"  ! {key}: site refused automated requests (429), skipped")
                else:
                    log(f"  ! {key}: {type(e).__name__} {str(e)[:80]}")
    return posts, status

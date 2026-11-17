"""Step 4, DE-DUPLICATE.

Two posts are the same job when they share a link (after removing tracking parameters), or
when the same company lists the same role after removing years, cities and brackets.
Multi-city copies ("Intern - Bengaluru", "Intern - Pune") become ONE post listing every city.
The id comes from company + cleaned title, so tomorrow's copy of a job matches today's.
"""

from __future__ import annotations

import hashlib
import re
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from fresherjobs.filters import Rules
from fresherjobs.models import RawPost


def canon_url(url: str) -> str:
    p = urlsplit(url.strip())
    query = [(k, v) for k, v in parse_qsl(p.query) if not k.lower().startswith(("utm_", "source", "ref"))]
    return urlunsplit(("https", p.netloc.lower().removeprefix("www."), p.path.rstrip("/"), urlencode(query), ""))


def norm_company(name: str) -> str:
    s = re.sub(r"\(.*?\)", " ", name.lower())
    s = re.sub(r"\b(pvt|private|ltd|limited|llp|inc|corp|corporation|technologies|technology|india|group)\b\.?", " ", s)
    return re.sub(r"[^a-z0-9]", "", s)


def norm_title(title: str, rules: Rules) -> str:
    t = title.lower()
    t = re.sub(r"\(.*?\)|\[.*?\]", " ", t)                          # "(2026)", "[Remote]"
    t = re.sub(r"\b20\d\d\b|\bsummer\b|\bwinter\b|\bfall\b|\bspring\b", " ", t)
    for alias, _ in rules.city_aliases:                               # "Intern - Bangalore"
        t = re.sub(r"\b" + re.escape(alias) + r"\b", " ", t)
    t = re.sub(r"\bindia\b|\bremote\b|\bhybrid\b|\bonsite\b|\bon-site\b", " ", t)
    return " ".join(re.sub(r"[^a-z0-9+#]+", " ", t).split())


def job_id(company: str, title: str, rules: Rules) -> str:
    key = norm_company(company) + "|" + norm_title(title, rules)
    return hashlib.sha1(key.encode()).hexdigest()[:12]


def dedupe(posts: list[RawPost], rules: Rules) -> tuple[list[RawPost], int]:
    """Return (unique posts, number of duplicates merged)."""
    by_id: dict[str, RawPost] = {}
    by_url: dict[str, str] = {}
    merged = 0
    for p in posts:
        p = dict(p)  # type: ignore[assignment]
        p["id"] = job_id(p["company"], p["title"], rules)
        cu = canon_url(p["url"])
        hit = by_id.get(p["id"]) or by_id.get(by_url.get(cu, ""))
        if hit is None:
            by_id[p["id"]] = p
            by_url[cu] = p["id"]
            continue
        merged += 1
        hit["needs_ai"] = bool(hit.get("needs_ai")) and bool(p.get("needs_ai"))   # any clear copy wins
        if p["location"] and p["location"] not in hit["location"]:
            hit["location"] = f"{hit['location']}; {p['location']}".strip("; ")
        if len(p["description"]) > len(hit["description"]):
            hit["description"] = p["description"]
        if p["posted"] and (not hit["posted"] or p["posted"] > hit["posted"]):
            hit["posted"] = p["posted"]
        by_url[cu] = hit["id"]
    return list(by_id.values()), merged

"""Small HTTP and text helpers shared by every source."""

from __future__ import annotations

import html
import re
from datetime import datetime, timezone
from typing import Any

import requests

HEADERS = {"User-Agent": "fresherjobs/1.0 (student job finder; see github.com/vrushali-pixel/beep-jobs)"}
TIMEOUT = 20


def get_json(url: str, **kwargs: Any) -> Any:
    r = requests.get(url, headers=HEADERS, timeout=TIMEOUT, **kwargs)
    r.raise_for_status()
    return r.json()


def post_json(url: str, body: dict[str, Any]) -> Any:
    r = requests.post(url, json=body, headers=HEADERS, timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()


def html_to_text(s: str | None) -> str:
    """Turn job-description HTML (sometimes escaped twice, as Greenhouse sends it) into plain text."""
    if not s:
        return ""
    s = html.unescape(s)
    s = re.sub(r"<(br|/p|/li|/h\d)[^>]*>", "\n", s, flags=re.I)
    s = re.sub(r"<[^>]+>", " ", s)
    s = html.unescape(s)
    s = re.sub(r"[ \t\r\f\v]+", " ", re.sub(r"\n\s*\n+", "\n", s))
    return re.sub(r" *\n *", "\n", s).strip()


def to_date(value: Any) -> str:
    """Accept ISO strings or epoch milliseconds (Lever); return YYYY-MM-DD or ""."""
    if not value:
        return ""
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value / 1000, tz=timezone.utc).date().isoformat()
    return str(value)[:10]

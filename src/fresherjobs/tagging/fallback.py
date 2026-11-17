"""Keyword tagger: used when there is no LLM key or a call fails, and as the baseline the
LLM is compared against. It reads only the title, so it cannot judge unclear titles."""

from __future__ import annotations

import re
from typing import Any

from fresherjobs.filters import Rules
from fresherjobs.models import RawPost, Tags


def _job_type(title: str) -> str:
    if re.search(r"\bintern", title):
        return "internship"
    if re.search(r"trainee|apprentice|articleship|naps", title):
        return "apprentice"
    return "fulltime"


def keyword_tag(p: RawPost, cfg: dict[str, Any], rules: Rules) -> Tags:
    """Pick the role whose keywords match the title best; longer phrases count more."""
    title = " ".join(re.sub(r"[^a-z0-9&+ ]+", " ", p["title"].lower()).split())
    best, score = "other", 0
    for key, role in cfg["roles"].items():
        s = sum(len(w.split()) for w in role.get("words", [])
                if re.search(r"(?<![a-z0-9])" + re.escape(w) + r"(?![a-z0-9])", title))
        if s > score:
            best, score = key, s
    return {
        "id": p["id"],
        "entry_level": not p.get("needs_ai"),   # without reading the description, unclear = no
        "role_group": best, "clean_title": p["title"][:60].strip(),
        "cities": rules.cities_in(p["location"]), "job_type": _job_type(title),
        "skills": [], "eligibility": "", "pay": p.get("pay", ""), "red_flags": [], "tagger": "keywords",
    }

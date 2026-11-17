"""Steps 2-3, CLEAN + FILTER: plain rules, no AI, so they are free and predictable.

Every post gets one of three answers:
  ""      keep: India, clearly entry-level, no scam signs
  "ai"    unclear title ("Software Developer"): only the LLM, reading the description, may decide
  reason  drop, and the reason is logged (e.g. "senior title", "not in India")
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from typing import Any

from fresherjobs.models import RawPost

KEEP, ASK_AI = "", "ai"

_INDIA_WORD = re.compile(r"\bindia\b", re.I)
_INDIA_CODE = re.compile(r"\bIND?\b(?=\s*[-,;)]|\s*$)|\bIN-[A-Z]{2}\b")   # "Pune, IN", "IND", "IN-MH"


def mentions_india(text: str) -> bool:
    return bool(_INDIA_WORD.search(text) or _INDIA_CODE.search(text))


def word_pattern(words: Iterable[str]) -> re.Pattern[str]:
    """One regex matching any of the words as whole words (case-insensitive input expected)."""
    parts = []
    for w in words:
        w = w.strip().lower()
        if not w:
            continue
        left = r"\b" if w[0].isalnum() else ""
        right = r"\b" if w[-1].isalnum() else ""
        parts.append(left + re.escape(w) + right)
    return re.compile("|".join(parts)) if parts else re.compile(r"(?!x)x")


def tidy_company(name: str) -> str:
    """Board names are sometimes 'Rubrik Job Board', 'HackerRank Careers', 'Stable Money1'."""
    s = re.sub(r"\s*\b(job board|careers?|jobs|recruiting portal)\s*$", "", name.strip(), flags=re.I)
    s = re.sub(r"(?<=[a-z])\d+$", "", s)
    s = re.sub(r",?\s*\b(LLC|Inc\.?|Ltd\.?)$", "", s).strip()
    return s or "Unknown company"


class Rules:
    """All filter rules, built from config/settings.yaml."""

    def __init__(self, cfg: dict[str, Any]) -> None:
        self.entry = word_pattern(cfg["entry_title_words"])
        self.senior = word_pattern(cfg["senior_title_words"])
        self.fresher = word_pattern(cfg["fresher_desc_phrases"])
        self.fraud = word_pattern(cfg["fraud_phrases"])
        self.city_aliases = [(alias, city) for city, aliases in cfg["cities"].items() for alias in aliases]
        self.city_re = {city: word_pattern(aliases) for city, aliases in cfg["cities"].items()}

    def cities_in(self, text: str) -> list[str]:
        t = text.lower()
        return [c for c, rx in self.city_re.items() if rx.search(t)]

    def is_india(self, post: RawPost) -> bool:
        loc = post["location"]
        if mentions_india(loc) or [c for c in self.cities_in(loc) if c != "Remote"]:
            return True
        # "Remote" alone could be anywhere: accept only if the location names no other
        # place (not "The Philippines (Remote)") and the post itself says India.
        if "Remote" in self.cities_in(loc):
            rest = self.city_re["Remote"].sub(" ", loc.lower())
            rest = re.sub(r"[^a-z]+", " ", rest).replace("only", " ").replace("anywhere", " ").strip()
            return not rest and mentions_india(post["description"][:3000])
        return False

    def entry_level(self, post: RawPost) -> tuple[bool | str, str]:
        """(True, "") clearly entry-level, (False, reason) clearly not, ("ai", reason) unclear."""
        title = post["title"].lower()
        if self.senior.search(title):
            return False, "senior title"
        if self.entry.search(title) or self.fresher.search(post["description"].lower()):
            return True, ""
        return ASK_AI, "unclear title (AI decides)"

    def check(self, post: RawPost) -> str:
        """KEEP, ASK_AI, or the reason the post is dropped."""
        if not post["title"].strip() or not post["url"].startswith("http"):
            return "missing title or link"
        if not self.is_india(post):
            return "not in India"
        ok, why = self.entry_level(post)
        if ok is False:
            return why
        if self.fraud.search((post["title"] + " " + post["description"]).lower()):
            return "asks for money (scam sign)"
        return ASK_AI if ok == ASK_AI else KEEP

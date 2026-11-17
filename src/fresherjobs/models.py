"""The shapes of the data moving through the pipeline (for readers and type checkers)."""

from __future__ import annotations

from typing import TypedDict


class RawPost(TypedDict, total=False):
    """One post as fetched from a job board, before any judgement."""

    source: str            # greenhouse | lever | ashby | smartrecruiters | workday
    board: str             # the company's board name at that provider
    company: str
    title: str
    url: str               # link to the original post (students apply there)
    location: str
    posted: str            # YYYY-MM-DD or ""
    description: str       # plain text
    employment_type: str
    pay: str
    id: str                # added by de-duplication: stable across days
    needs_ai: bool         # title is unclear: only the LLM may decide if freshers can apply


class Tags(TypedDict, total=False):
    """What the LLM (or the keyword fallback) says about one post."""

    id: str
    entry_level: bool
    role_group: str        # a key from config/settings.yaml -> roles
    clean_title: str
    cities: list[str]      # canonical names from config/settings.yaml -> cities
    job_type: str          # internship | apprentice | fulltime
    skills: list[str]
    eligibility: str
    pay: str
    red_flags: list[str]
    tagger: str            # model name, or "keywords"


class Job(TypedDict, total=False):
    """A post as stored in data/db.json and shown on the page."""

    id: str
    title: str
    original_title: str
    company: str
    location: str
    cities: list[str]
    role: str
    role_label: str
    type: str
    type_label: str
    skills: list[str]
    eligibility: str
    pay: str
    url: str
    source: str
    board: str
    posted: str
    tagger: str
    first_seen: str
    last_seen: str
    status: str            # active | closed | expired
    closed_on: str

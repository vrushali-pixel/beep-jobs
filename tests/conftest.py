"""Shared test helpers. All tests run offline: no internet, no API key."""

from __future__ import annotations

import os

import pytest

from fresherjobs.config import Paths, load_settings
from fresherjobs.filters import Rules

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@pytest.fixture(scope="session")
def paths() -> Paths:
    return Paths(ROOT)


@pytest.fixture(scope="session")
def cfg(paths: Paths) -> dict:
    return load_settings(paths)


@pytest.fixture(scope="session")
def rules(cfg: dict) -> Rules:
    return Rules(cfg)


def make_post(title: str, loc: str = "Bengaluru, India", desc: str = "", company: str = "Acme",
              url: str | None = None, source: str = "greenhouse", board: str = "acme") -> dict:
    return {"source": source, "board": board, "company": company, "title": title,
            "url": url or f"https://x.com/{abs(hash(title + loc + company)) % 10**8}", "location": loc,
            "posted": "2026-11-10", "description": desc, "employment_type": "", "pay": ""}

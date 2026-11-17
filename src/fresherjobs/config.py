"""Where things live, and how settings are loaded.

Everything a person might change (cities, roles, filter words, model, company list, prompt)
is in the `config/` folder, so most changes never touch the code.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

import yaml

IST = timezone(timedelta(hours=5, minutes=30))


@dataclass(frozen=True)
class Paths:
    """All file locations, relative to the repository root."""

    root: str = "."

    def _p(self, *parts: str) -> str:
        return os.path.join(self.root, *parts)

    @property
    def settings(self) -> str:
        return self._p("config", "settings.yaml")

    @property
    def companies(self) -> str:
        return self._p("config", "companies.yaml")

    @property
    def data_dir(self) -> str:
        return self._p("data")

    @property
    def db(self) -> str:
        return self._p("data", "db.json")                  # every post ever seen, with its status

    @property
    def tag_cache(self) -> str:
        return self._p("data", "tags_cache.json")          # LLM answers, so each post is paid for once

    @property
    def runs_log(self) -> str:
        return self._p("data", "runs.jsonl")               # one line of stats per run (tokens, counts)

    @property
    def rejected(self) -> str:
        return self._p("data", "rejected_latest.json")     # what was filtered out today, and why

    @property
    def jobs_csv(self) -> str:
        return self._p("data", "jobs.csv")                 # live posts for a spreadsheet

    @property
    def site_json(self) -> str:
        return self._p("site", "jobs.json")                # what the web page reads

    @property
    def sample_csv(self) -> str:
        return self._p("eval", "sample_50.csv")


def load_yaml(path: str) -> Any:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_settings(paths: Paths) -> dict[str, Any]:
    cfg = load_yaml(paths.settings)
    prompt = cfg["llm"]["prompt_file"]
    if not os.path.isabs(prompt):
        cfg["llm"]["prompt_file"] = os.path.join(paths.root, prompt)
    return cfg


def today_ist() -> str:
    return datetime.now(IST).date().isoformat()

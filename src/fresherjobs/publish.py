"""Step 7, PUBLISH: write what the page reads, plus files for audits and spreadsheets."""

from __future__ import annotations

import csv
import json
import os
from typing import Any

from fresherjobs.config import Paths
from fresherjobs.models import Job

PAGE_FIELDS = ["id", "title", "original_title", "company", "location", "cities", "role", "role_label",
               "type", "type_label", "skills", "eligibility", "pay", "url", "posted", "first_seen"]
CSV_FIELDS = ["id", "title", "original_title", "company", "location", "cities", "role_label", "type_label",
              "skills", "eligibility", "pay", "url", "posted", "first_seen", "tagger"]


def _dump(path: str, obj: Any, indent: int | None = None) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=indent)


def write_all(paths: Paths, cfg: dict[str, Any], db: dict[str, Any], live: list[Job],
              rejected: list[dict[str, str]], stats: dict[str, Any], today: str) -> None:
    _dump(paths.site_json, {
        "updated": today, "stats": stats,
        "roles": {k: v["label"] for k, v in cfg["roles"].items()}, "types": cfg["job_types"],
        "jobs": [{k: j.get(k) for k in PAGE_FIELDS} for j in live],
    })
    _dump(paths.db, db, indent=1)
    _dump(paths.rejected, rejected, indent=1)
    with open(paths.runs_log, "a", encoding="utf-8") as f:
        f.write(json.dumps(stats) + "\n")
    with open(paths.jobs_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["id", "title", "original_title", "company", "location", "cities", "role", "type",
                    "skills", "eligibility", "pay", "url", "posted", "first_seen", "tagger"])
        for j in live:
            row = {**j, "cities": "; ".join(j["cities"]), "skills": "; ".join(j["skills"])}
            w.writerow([row.get(k, "") for k in CSV_FIELDS])

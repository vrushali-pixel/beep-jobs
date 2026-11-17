"""The prompt, the answer schema, and validation of what the model returns."""

from __future__ import annotations

import json
import re
from typing import Any

from fresherjobs.models import RawPost, Tags

JOB_TYPES = ["internship", "apprentice", "fulltime"]


def build_prompt(cfg: dict[str, Any]) -> str:
    """Fill the prompt file's {ROLE_LIST} and {CITY_LIST} from config, so they never drift apart."""
    with open(cfg["llm"]["prompt_file"], encoding="utf-8") as f:
        text = f.read()
    roles = "\n".join(f"  - {key}: {r['hint']}" for key, r in cfg["roles"].items())
    return text.replace("{ROLE_LIST}", roles).replace("{CITY_LIST}", ", ".join(cfg["cities"]))


def answer_schema(cfg: dict[str, Any]) -> dict[str, Any]:
    """JSON schema of the answer. role_group and cities are ENUMS: the model cannot invent them."""
    post = {
        "type": "object",
        "properties": {
            "id": {"type": "string"},
            "entry_level": {"type": "boolean"},
            "role_group": {"type": "string", "enum": list(cfg["roles"])},
            "clean_title": {"type": "string"},
            "cities": {"type": "array", "items": {"type": "string", "enum": list(cfg["cities"])}},
            "job_type": {"type": "string", "enum": JOB_TYPES},
            "skills": {"type": "array", "items": {"type": "string"}, "maxItems": 5},
            "eligibility": {"type": "string"},
            "pay": {"type": "string"},
            "red_flags": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["id", "entry_level", "role_group", "clean_title", "cities", "job_type",
                     "skills", "eligibility", "pay", "red_flags"],
    }
    return {"type": "object", "properties": {"posts": {"type": "array", "items": post}}, "required": ["posts"]}


def post_for_llm(p: RawPost, max_chars: int) -> dict[str, Any]:
    """Only what the model needs; the description is cut short to keep cost down."""
    return {"id": p["id"], "title": p["title"], "company": p["company"], "location": p["location"],
            "check_experience": bool(p.get("needs_ai")),
            "employment_type": p.get("employment_type", ""), "pay": p.get("pay", ""),
            "description": re.sub(r"\s+", " ", p["description"])[:max_chars]}


def user_message(batch: list[RawPost], max_chars: int) -> str:
    return "Tag these posts:\n" + json.dumps([post_for_llm(p, max_chars) for p in batch], ensure_ascii=False)


def validate(t: dict[str, Any], cfg: dict[str, Any]) -> Tags:
    """Never trust model output blindly: drop unknown cities, fix unknown roles/types, cap skills."""
    t["cities"] = [c for c in t.get("cities", []) if c in cfg["cities"]]
    if t.get("role_group") not in cfg["roles"]:
        t["role_group"] = "other"
    if t.get("job_type") not in JOB_TYPES:
        t["job_type"] = "fulltime"
    t["skills"] = [s for s in t.get("skills", []) if s][:5]
    return t  # type: ignore[return-value]

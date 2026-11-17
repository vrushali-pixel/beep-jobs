"""How good is the tagging, and what does it cost?

1. `fresherjobs sample`  -> eval/sample_50.csv: 50 random live posts (fixed seed = repeatable)
2. A person reads each original post and fills true_role and true_cities (before looking at ai_*)
3. `fresherjobs score eval/sample_50_checked.csv` -> % correct for role, city, both; the mistakes;
   and cost per 1,000 posts from the real token counts in data/runs.jsonl
"""

from __future__ import annotations

import collections
import csv
import json
import os
import random
from collections.abc import Callable
from typing import Any

from fresherjobs.config import Paths, load_settings

SAMPLE_HEADER = ["id", "original_title", "company", "location", "url",
                 "ai_role", "ai_cities", "true_role", "true_cities", "notes"]


def make_sample(paths: Paths, n: int = 50, seed: int = 20) -> int:
    with open(paths.site_json, encoding="utf-8") as f:
        jobs = json.load(f)["jobs"]
    random.Random(seed).shuffle(jobs)
    os.makedirs(os.path.dirname(paths.sample_csv), exist_ok=True)
    with open(paths.sample_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(SAMPLE_HEADER)
        for j in jobs[:n]:
            w.writerow([j["id"], j["original_title"], j["company"], j["location"], j["url"],
                        j["role"], "; ".join(j["cities"]), "", "", ""])
    return min(n, len(jobs))


def _cities(s: str) -> frozenset[str]:
    return frozenset(c.strip().lower() for c in (s or "").replace(",", ";").split(";") if c.strip())


def score_rows(rows: list[dict[str, str]]) -> dict[str, Any]:
    """Accuracy over rows that have true_role filled in. City = exact set match."""
    rows = [r for r in rows if r.get("true_role", "").strip()]
    n = len(rows)
    role_ok = [r["ai_role"].strip() == r["true_role"].strip() for r in rows]
    city_ok = [_cities(r["ai_cities"]) == _cities(r["true_cities"]) for r in rows]
    both = [a and b for a, b in zip(role_ok, city_ok, strict=True)]
    pct = (lambda xs: round(100 * sum(xs) / n, 1)) if n else (lambda xs: 0.0)
    return {
        "checked": n, "role_pct": pct(role_ok), "city_pct": pct(city_ok), "both_pct": pct(both),
        "role_mistakes": collections.Counter((r["true_role"], r["ai_role"])
                                             for r, ok in zip(rows, role_ok, strict=True) if not ok),
        "city_mistakes": [(r["original_title"], r["ai_cities"], r["true_cities"])
                          for r, ok in zip(rows, city_ok, strict=True) if not ok],
    }


def cost_per_1000(paths: Paths) -> dict[str, Any]:
    """Average tokens per LLM-tagged post from all runs, priced from config (None if no prices)."""
    llm = load_settings(paths)["llm"]
    runs = []
    if os.path.exists(paths.runs_log):
        with open(paths.runs_log, encoding="utf-8") as f:
            runs = [json.loads(line) for line in f if line.strip()]
    posts = sum(r.get("llm_posts_llm", 0) for r in runs)
    if not posts:
        return {"posts": 0}
    tin = sum(r.get("llm_input_tokens", 0) for r in runs) / posts
    tout = sum(r.get("llm_output_tokens", 0) for r in runs) / posts
    pin, pout = llm.get("price_input_per_mtok_usd"), llm.get("price_output_per_mtok_usd")
    usd = None if pin is None or pout is None else (tin * pin + tout * pout) / 1e6 * 1000
    return {"posts": posts, "in_per_post": round(tin), "out_per_post": round(tout), "usd_per_1000": usd,
            "model": llm["model"]}


def score(paths: Paths, checked_csv: str, log: Callable[[str], None] = print) -> dict[str, Any]:
    with open(checked_csv, encoding="utf-8") as f:
        res = score_rows(list(csv.DictReader(f)))
    if not res["checked"]:
        log("No rows with true_role filled in.")
        return res
    n = res["checked"]
    log(f"Checked posts : {n}")
    log(f"Role correct  : {res['role_pct']}%")
    log(f"City correct  : {res['city_pct']}%")
    log(f"Both correct  : {res['both_pct']}%")
    for (true, ai), c in res["role_mistakes"].most_common():
        log(f"  role should be {true}, AI said {ai}: {c}")
    for title, ai, true in res["city_mistakes"]:
        log(f"  city: {title[:50]} | AI {ai} | true {true}")
    cost = cost_per_1000(paths)
    if cost["posts"]:
        log(f"\n{cost['model']}: {cost['in_per_post']} input + {cost['out_per_post']} output tokens per post "
            f"(over {cost['posts']} LLM-tagged posts)")
        if cost["usd_per_1000"] is None:
            log("Add llm.price_*_per_mtok_usd to config/settings.yaml to get the dollar cost.")
        else:
            log(f"Cost per 1,000 posts at paid-tier prices: ${cost['usd_per_1000']:.3f} "
                "(free tier: $0 actually spent)")
    res["cost"] = cost
    return res

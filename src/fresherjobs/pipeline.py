"""The daily run, end to end:

    fetch -> filter -> de-duplicate -> tag -> merge with yesterday -> publish

Each step lives in its own module; this file only connects them and counts what happened.
"""

from __future__ import annotations

import collections
import json
import os
import re
import time
from collections.abc import Callable
from typing import Any

from fresherjobs import sources, store
from fresherjobs.config import Paths, load_settings, load_yaml, today_ist
from fresherjobs.dedupe import dedupe, job_id
from fresherjobs.filters import ASK_AI, KEEP, Rules, tidy_company
from fresherjobs.models import RawPost, Tags
from fresherjobs.publish import write_all
from fresherjobs.tagging import Tagger

MULTI_LOCATION = re.compile(r"^\d+ Locations?$", re.I)     # Workday hides cities behind "3 Locations"


def _filter(raw: list[RawPost], rules: Rules, tagger: Tagger, offline: bool, delay: float,
            log: Callable[[str], None]) -> tuple[list[RawPost], list[dict[str, str]], collections.Counter]:
    """Cheap rules first; a description is fetched only when it can change the answer."""
    kept: list[RawPost] = []
    rejected: list[dict[str, str]] = []
    reasons: collections.Counter = collections.Counter()
    for p in raw:
        p["company"] = tidy_company(p["company"])
        verdict = rules.check(p)
        multi = (p["source"] == "workday" and MULTI_LOCATION.match(p["location"])
                 and rules.entry_level(p)[0] is True)
        known = tagger.already_tagged(job_id(p["company"], p["title"], rules))   # LLM judged it earlier
        useful = verdict == KEEP or (verdict == ASK_AI and tagger.available) or multi
        if useful and p.get("_detail") and not p["description"] and not offline and not known:
            try:
                sources.DETAIL[p["source"]](p)
                time.sleep(delay)
            except Exception as e:  # noqa: BLE001
                log(f"  ! detail {p['url']}: {type(e).__name__}")
            verdict = rules.check(p)
        p.pop("_detail", None)  # type: ignore[misc]
        if verdict == ASK_AI and known:
            verdict = KEEP
        if verdict == ASK_AI and not tagger.available:
            verdict = "unclear title (no LLM key to check)"
        if verdict not in (KEEP, ASK_AI):
            reasons[verdict] += 1
            rejected.append({"title": p["title"], "company": p["company"], "location": p["location"],
                             "url": p["url"], "reason": verdict})
        else:
            p["needs_ai"] = verdict == ASK_AI
            kept.append(p)
    return kept, rejected, reasons


def run(paths: Paths, offline_file: str | None = None, today: str | None = None,
        log: Callable[[str], None] = print) -> dict[str, Any]:
    t0 = time.time()
    cfg = load_settings(paths)
    rules = Rules(cfg)
    today = today or today_ist()
    delay = cfg["refresh"]["request_delay_sec"]
    os.makedirs(paths.data_dir, exist_ok=True)
    log(f"Run for {today}")

    # 1. FETCH
    if offline_file:
        with open(offline_file, encoding="utf-8") as f:
            raw: list[RawPost] = json.load(f)
        status = {sources.board_key(p): True for p in raw}
    else:
        raw, status = sources.fetch_all(load_yaml(paths.companies), delay, log)
    log(f"1 fetched {len(raw)} posts from {sum(status.values())}/{len(status)} boards")

    # 2-3. FILTER
    tagger = Tagger(cfg, rules, paths.tag_cache)
    kept, rejected, reasons = _filter(raw, rules, tagger, bool(offline_file), delay, log)
    n_ai = sum(p["needs_ai"] for p in kept)
    log(f"2 kept {len(kept)} India posts ({len(kept) - n_ai} clearly entry-level, {n_ai} for the AI to judge); "
        f"rejected {dict(reasons)}")

    # 4. DE-DUPLICATE
    posts, merged = dedupe(kept, rules)
    log(f"3 merged {merged} duplicates -> {len(posts)} unique")

    # 5. TAG
    tags = tagger.tag(posts, log)
    accepted: list[tuple[RawPost, Tags]] = []
    ai_rejected = 0
    for p in posts:
        t = tags[p["id"]]
        why = "AI: not entry-level" if not t.get("entry_level", True) else \
              ("AI: " + "; ".join(t["red_flags"])) if t.get("red_flags") else ""
        if why:
            ai_rejected += 1
            rejected.append({"title": p["title"], "company": p["company"], "location": p["location"],
                             "url": p["url"], "reason": why})
        else:
            accepted.append((p, t))
    log(f"4 tagged {len(posts)} (LLM {tagger.usage['posts_llm']}, keyword fallback "
        f"{tagger.usage['posts_fallback']}); {len(accepted)} passed the AI check")

    # 6. MERGE WITH YESTERDAY
    db = store.load_db(paths.db)
    counts = store.merge(db, accepted, status, cfg, rules, today,
                         configured=None if offline_file else set(status))
    live = store.live_jobs(db)

    # 7. PUBLISH
    stats: dict[str, Any] = {
        "date": today, "boards_ok": sum(status.values()), "boards_failed": len(status) - sum(status.values()),
        "fetched": len(raw), "rejected_by_rules": dict(reasons), "duplicates_merged": merged,
        "ai_rejected": ai_rejected, "new_today": counts["new"], "closed_today": counts["closed"],
        "expired_today": counts["expired"], "live": len(live),
        **{f"llm_{k}": v for k, v in tagger.usage.items()}, "llm_cost_usd": tagger.cost_usd(),
        "seconds": round(time.time() - t0, 1),
    }
    write_all(paths, cfg, db, live, rejected, stats, today)
    log(f"5 published {len(live)} live posts ({counts['new']} new, {counts['closed']} closed, "
        f"{counts['expired']} expired)")
    log(json.dumps(stats))
    return stats

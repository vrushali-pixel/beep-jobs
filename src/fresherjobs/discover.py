"""Check every board in config/companies.yaml and report how many India entry-level posts it has.

Use it after adding companies, to see which boards exist and whether you will reach your target.
"""

from __future__ import annotations

import time
from collections.abc import Callable

from fresherjobs import sources
from fresherjobs.config import Paths, load_settings, load_yaml
from fresherjobs.filters import Rules


def discover(paths: Paths, target: int = 200, log: Callable[[str], None] = print) -> int:
    cfg = load_settings(paths)
    companies = load_yaml(paths.companies)
    rules, delay = Rules(cfg), cfg["refresh"]["request_delay_sec"]
    total = 0
    for kind, fn in sources.FETCHERS.items():
        for slug in companies.get(kind) or []:
            try:
                posts = fn(slug, delay) if kind == "smartrecruiters" else fn(slug)
            except Exception as e:  # noqa: BLE001
                log(f"{kind:16} {slug:26} missing  ({type(e).__name__})")
                time.sleep(delay)
                continue
            india = [p for p in posts if rules.is_india(p)]
            clear = [p for p in india if rules.entry_level(p)[0] is True]
            unclear = [p for p in india if rules.entry_level(p)[0] == "ai"]
            total += len(clear)
            log(f"{kind:16} {slug:26} all={len(posts):<5} india={len(india):<5} "
                f"entry={len(clear):<4} unclear={len(unclear)}")
            time.sleep(delay)
    log(f"\nAbout {total} clearly entry-level India posts before de-duplication "
        f"(unclear ones need the LLM). Target: {target}.")
    return total

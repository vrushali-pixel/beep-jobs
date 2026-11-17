"""Check every candidate board in sources/companies.yaml once.

Keeps boards that exist AND have at least one India post today, and writes
sources/companies_verified.yaml for the daily run. Prints how many India entry-level
posts each board has, so you know if you will reach 200.

    python -m pipeline.discover
"""
import time

import yaml

from pipeline import fetch
from pipeline.clean import Rules


def main():
    cfg = yaml.safe_load(open("config.yaml"))
    cands = yaml.safe_load(open("sources/companies.yaml"))
    rules, delay = Rules(cfg), cfg["refresh"]["request_delay_sec"]
    verified = {k: [] for k in fetch.FETCHERS}
    rows, total_entry = [], 0
    for kind, fn in fetch.FETCHERS.items():
        for slug in cands.get(kind) or []:
            try:
                posts = fn(slug) if kind != "smartrecruiters" else fn(slug, delay)
            except Exception as e:
                rows.append((kind, slug, "missing", 0, 0, type(e).__name__))
                time.sleep(delay)
                continue
            india = [p for p in posts if rules.is_india(p)]
            entry = [p for p in india if rules.entry_level(p)[0]]
            total_entry += len(entry)
            rows.append((kind, slug, "ok", len(posts), len(india), len(entry)))
            if india:
                verified[kind].append(slug)
            time.sleep(delay)
    for r in rows:
        print("{:<16} {:<22} {:<8} all={:<5} india={:<5} entry={}".format(*r))
    verified["workday_enabled"] = cands.get("workday_enabled", False)
    verified["workday"] = cands.get("workday", [])
    with open("sources/companies_verified.yaml", "w") as f:
        f.write("# Written by `python -m pipeline.discover`. Boards that exist and have India posts.\n")
        yaml.safe_dump(verified, f, sort_keys=False, allow_unicode=True)
    n = sum(len(v) for k, v in verified.items() if isinstance(v, list) and k != "workday")
    print(f"\n{n} boards with India posts; about {total_entry} India entry-level posts before AI check.")
    if total_entry < 230:
        print("Below target: add more companies to sources/companies.yaml (or decide on Workday) and re-run.")


if __name__ == "__main__":
    main()

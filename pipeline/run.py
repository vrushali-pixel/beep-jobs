"""The daily run: fetch -> filter -> de-dupe -> tag -> merge with yesterday -> publish.

    python -m pipeline.run                 # normal daily run
    python -m pipeline.run --offline FILE  # use saved raw posts (testing, no internet)
"""
import argparse
import collections
import csv
import json
import os
import time
from datetime import date, datetime, timedelta, timezone

import yaml

from pipeline import fetch
from pipeline.clean import Rules, dedupe
from pipeline.tag import Tagger

IST = timezone(timedelta(hours=5, minutes=30))
DB, SITE_JSON, RUNS, REJECTED, CSV_OUT = ("data/db.json", "site/jobs.json", "data/runs.jsonl",
                                          "data/rejected_latest.json", "data/jobs.csv")


def load_yaml(path):
    return yaml.safe_load(open(path, encoding="utf-8"))


def board_key(p):
    return f"{p['source']}:{p['board']}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--offline", help="JSON file of raw posts instead of fetching")
    ap.add_argument("--today", help="override date (YYYY-MM-DD), for testing")
    args = ap.parse_args()

    t0 = time.time()
    cfg = load_yaml("config.yaml")
    companies = load_yaml("sources/companies_verified.yaml" if os.path.exists("sources/companies_verified.yaml")
                          else "sources/companies.yaml")
    rules = Rules(cfg)
    os.makedirs("data", exist_ok=True)
    today = args.today or datetime.now(IST).date().isoformat()
    delay = cfg["refresh"]["request_delay_sec"]
    print(f"Run for {today}")

    # 1. FETCH
    if args.offline:
        raw = json.load(open(args.offline, encoding="utf-8"))
        status = {board_key(p): True for p in raw}
    else:
        raw, status = fetch.fetch_all(companies, delay)
    print(f"1 fetched {len(raw)} posts from {sum(status.values())}/{len(status)} boards")

    # 2-3. CLEAN + FILTER (cheap rules first; extra detail calls only for survivors)
    reasons, kept, rejected = collections.Counter(), [], []
    for p in raw:
        why = rules.check(p)
        if not why and p.get("_detail") and not p["description"] and not args.offline:
            try:
                fetch.DETAIL[p["source"]](p)
                time.sleep(delay)
            except Exception as e:
                print(f"  ! detail {p['url']}: {type(e).__name__}")
            why = rules.check(p)
        p.pop("_detail", None)
        if why:
            reasons[why] += 1
            rejected.append({"title": p["title"], "company": p["company"], "location": p["location"],
                             "url": p["url"], "reason": why})
        else:
            kept.append(p)
    print(f"2 kept {len(kept)} India entry-level posts; rejected {dict(reasons)}")

    # 4. DE-DUPE
    posts, dups = dedupe(kept, rules)
    print(f"3 merged {dups} duplicates -> {len(posts)} unique")

    # 5. TAG (LLM, new posts only)
    tagger = Tagger(cfg, rules)
    tags = tagger.tag(posts)
    final = []
    for p in posts:
        t = tags[p["id"]]
        if not t.get("entry_level", True):
            reasons["AI: not entry-level"] += 1
            rejected.append({"title": p["title"], "company": p["company"], "location": p["location"],
                             "url": p["url"], "reason": "AI: not entry-level"})
            continue
        if t.get("red_flags"):
            reasons["AI: scam signs"] += 1
            rejected.append({"title": p["title"], "company": p["company"], "location": p["location"],
                             "url": p["url"], "reason": "AI: " + "; ".join(t["red_flags"])})
            continue
        final.append((p, t))
    print(f"4 tagged {len(posts)} (LLM {tagger.usage['posts_llm']}, keyword fallback {tagger.usage['posts_fallback']}); "
          f"{len(final)} passed the AI check")

    # 6. MERGE WITH YESTERDAY + EXPIRE
    db = json.load(open(DB)) if os.path.exists(DB) else {"jobs": {}}
    seen_today, new_today = set(), 0
    for p, t in final:
        old = db["jobs"].get(p["id"])
        rec = {
            "id": p["id"], "title": t["clean_title"] or p["title"], "original_title": p["title"],
            "company": p["company"], "location": p["location"],
            "cities": t["cities"] or [c for c in rules.cities_in(p["location"])],
            "role": t["role_group"], "role_label": cfg["roles"][t["role_group"]]["label"],
            "type": t["job_type"], "type_label": cfg["job_types"][t["job_type"]],
            "skills": t["skills"], "eligibility": t["eligibility"], "pay": t["pay"] or p.get("pay", ""),
            "url": p["url"], "source": p["source"], "board": p["board"], "posted": p["posted"],
            "tagger": t.get("tagger", ""),
            "first_seen": old["first_seen"] if old else today, "last_seen": today, "status": "active",
        }
        new_today += old is None or old.get("status") != "active"
        db["jobs"][p["id"]] = rec
        seen_today.add(p["id"])

    closed = expired = 0
    limit = (date.fromisoformat(today) - timedelta(days=cfg["refresh"]["expire_after_days"])).isoformat()
    for j in db["jobs"].values():
        if j["id"] in seen_today or j["status"] != "active":
            continue
        if status.get(f"{j['source']}:{j['board']}"):
            j["status"], j["closed_on"] = "closed", today        # board answered, post is gone
            closed += 1
        elif j["last_seen"] < limit:
            j["status"] = "expired"                               # board down for too long
            expired += 1
        # else: board failed today -> keep the post, it is probably still open

    # 7. PUBLISH
    live = sorted((j for j in db["jobs"].values() if j["status"] == "active"),
                  key=lambda j: (j["first_seen"], j["posted"] or ""), reverse=True)
    keep_fields = ["id", "title", "original_title", "company", "location", "cities", "role", "role_label",
                   "type", "type_label", "skills", "eligibility", "pay", "url", "posted", "first_seen"]
    stats = {
        "date": today, "boards_ok": sum(status.values()), "boards_failed": len(status) - sum(status.values()),
        "fetched": len(raw), "rejected_by_rules": {k: v for k, v in reasons.items() if not k.startswith("AI")},
        "duplicates_merged": dups, "ai_rejected": reasons["AI: not entry-level"] + reasons["AI: scam signs"],
        "new_today": new_today, "closed_today": closed, "expired_today": expired, "live": len(live),
        **{f"llm_{k}": v for k, v in tagger.usage.items()}, "llm_cost_usd": tagger.cost_usd(),
        "seconds": round(time.time() - t0, 1),
    }
    os.makedirs("site", exist_ok=True)
    json.dump({"updated": today, "stats": stats, "roles": {k: v["label"] for k, v in cfg["roles"].items()},
               "types": cfg["job_types"], "jobs": [{k: j.get(k) for k in keep_fields} for j in live]},
              open(SITE_JSON, "w", encoding="utf-8"), ensure_ascii=False)
    json.dump(db, open(DB, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    json.dump(rejected, open(REJECTED, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    with open(RUNS, "a", encoding="utf-8") as f:
        f.write(json.dumps(stats) + "\n")
    with open(CSV_OUT, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["id", "title", "original_title", "company", "location", "cities", "role", "type",
                    "skills", "eligibility", "pay", "url", "posted", "first_seen", "tagger"])
        for j in live:
            w.writerow([j["id"], j["title"], j["original_title"], j["company"], j["location"], "; ".join(j["cities"]),
                        j["role_label"], j["type_label"], "; ".join(j["skills"]), j["eligibility"], j["pay"],
                        j["url"], j["posted"], j["first_seen"], j["tagger"]])
    print(f"5 published {len(live)} live posts ({new_today} new, {closed} closed, {expired} expired)")
    print(json.dumps(stats))


if __name__ == "__main__":
    main()

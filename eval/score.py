"""Score the hand-checked sample and compute cost per 1,000 posts.

    python -m eval.score eval/sample_50_checked.csv

Role: correct if ai_role == true_role.
City: correct if the SET of cities matches exactly (order ignored).
Also prints the mistakes, so you can improve the prompt and re-run.
"""
import collections
import csv
import json
import sys

import yaml


def cities(s):
    return frozenset(c.strip().lower() for c in (s or "").replace(",", ";").split(";") if c.strip())


def main(path):
    rows = [r for r in csv.DictReader(open(path, encoding="utf-8")) if r["true_role"].strip()]
    n = len(rows)
    if not n:
        sys.exit("No rows with true_role filled in.")
    role_ok = [r["ai_role"].strip() == r["true_role"].strip() for r in rows]
    city_ok = [cities(r["ai_cities"]) == cities(r["true_cities"]) for r in rows]
    both = [a and b for a, b in zip(role_ok, city_ok)]
    pct = lambda xs: f"{100 * sum(xs) / n:.0f}% ({sum(xs)}/{n})"
    print(f"Checked posts : {n}")
    print(f"Role correct  : {pct(role_ok)}")
    print(f"City correct  : {pct(city_ok)}")
    print(f"Both correct  : {pct(both)}")
    conf = collections.Counter((r["true_role"], r["ai_role"]) for r, ok in zip(rows, role_ok) if not ok)
    if conf:
        print("\nRole mistakes (should be -> AI said):")
        for (t, a), c in conf.most_common():
            print(f"  {t} -> {a}: {c}")
    bad_city = [(r["original_title"], r["ai_cities"], r["true_cities"]) for r, ok in zip(rows, city_ok) if not ok]
    if bad_city:
        print("\nCity mistakes (title | AI | true):")
        for t, a, tr in bad_city:
            print(f"  {t[:50]} | {a} | {tr}")
    cost_report()


def cost_report():
    cfg = yaml.safe_load(open("config.yaml"))["llm"]
    runs = [json.loads(l) for l in open("data/runs.jsonl", encoding="utf-8") if l.strip()]
    posts = sum(r.get("llm_posts_llm", 0) for r in runs)
    tin = sum(r.get("llm_input_tokens", 0) for r in runs)
    tout = sum(r.get("llm_output_tokens", 0) for r in runs)
    if not posts:
        print("\nNo LLM-tagged posts in data/runs.jsonl yet.")
        return
    print(f"\nLLM-tagged posts so far: {posts}")
    print(f"Tokens per post: {tin / posts:.0f} in, {tout / posts:.0f} out")
    pi, po = cfg.get("price_input_per_mtok_usd"), cfg.get("price_output_per_mtok_usd")
    if pi is None or po is None:
        print("Add the model's prices to config.yaml (llm.price_*_per_mtok_usd) to get the cost.")
        return
    per_1000 = (tin / posts * pi + tout / posts * po) / 1e6 * 1000
    print(f"Cost per 1,000 posts: ${per_1000:.3f}  (multiply by today's USD-INR rate for rupees)")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "eval/sample_50.csv")

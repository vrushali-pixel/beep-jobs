"""Pick 50 random live posts for hand-checking.

    python -m eval.make_sample            # writes eval/sample_50.csv

Open the CSV in Google Sheets. For each row, read the original post (url) and fill
true_role and true_cities yourself BEFORE looking at the ai_ columns if you can.
Allowed role keys are listed in config.yaml. Cities: ';'-separated canonical names.
"""
import csv
import json
import random

import yaml


def main(n=50, seed=20):
    cfg = yaml.safe_load(open("config.yaml"))
    jobs = json.load(open("site/jobs.json"))["jobs"]
    random.Random(seed).shuffle(jobs)          # fixed seed = same 50 every time you run it
    with open("eval/sample_50.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["id", "original_title", "company", "location", "url",
                    "ai_role", "ai_cities", "true_role", "true_cities", "notes"])
        for j in jobs[:n]:
            w.writerow([j["id"], j["original_title"], j["company"], j["location"], j["url"],
                        j["role"], "; ".join(j["cities"]), "", "", ""])
    print(f"Wrote eval/sample_50.csv ({min(n, len(jobs))} posts). Role keys: {', '.join(cfg['roles'])}")


if __name__ == "__main__":
    main()

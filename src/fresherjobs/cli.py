"""Command line:

    fresherjobs run [--offline FILE] [--today YYYY-MM-DD]   daily pipeline
    fresherjobs discover                                    check every company board
    fresherjobs sample                                      50 posts to hand-check
    fresherjobs score FILE                                  accuracy + cost per 1,000 posts

(`python -m fresherjobs ...` works too.)
"""

from __future__ import annotations

import argparse

from fresherjobs import __version__
from fresherjobs.config import Paths


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(prog="fresherjobs", description="Fresher jobs & internships in India, daily.")
    ap.add_argument("--version", action="version", version=__version__)
    ap.add_argument("--root", default=".", help="repository root (default: current folder)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run", help="fetch, filter, de-duplicate, tag and publish")
    r.add_argument("--offline", help="JSON file of raw posts instead of fetching (testing)")
    r.add_argument("--today", help="override the date, YYYY-MM-DD (testing)")
    sub.add_parser("discover", help="check every board in config/companies.yaml")
    sub.add_parser("sample", help="write eval/sample_50.csv for hand-checking")
    s = sub.add_parser("score", help="score a hand-checked sample")
    s.add_argument("csv", nargs="?", default="eval/sample_50.csv")
    args = ap.parse_args(argv)
    paths = Paths(args.root)

    if args.cmd == "run":
        from fresherjobs.pipeline import run
        run(paths, offline_file=args.offline, today=args.today)
    elif args.cmd == "discover":
        from fresherjobs.discover import discover
        discover(paths)
    elif args.cmd == "sample":
        from fresherjobs.evaluation import make_sample
        n = make_sample(paths)
        print(f"Wrote {paths.sample_csv} ({n} posts). Fill true_role and true_cities, then run `fresherjobs score`.")
    elif args.cmd == "score":
        from fresherjobs.evaluation import score
        score(paths, args.csv)


if __name__ == "__main__":
    main()

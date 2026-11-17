# 5. No server: GitHub Actions + a JSON file + GitHub Pages

**Status:** accepted · 17 Nov 2026

## Context
The page must refresh every day on its own and be live. The data is small (a few hundred posts)
and changes once a day.

## Decision
- A scheduled GitHub Actions workflow (6:10 AM IST) runs the pipeline.
- State lives in the repo as JSON (`data/db.json`, `data/tags_cache.json`, `data/runs.jsonl`),
  committed back by the run. The run pulls before saving, so a code push during the run cannot
  break it.
- The page is one static HTML file that reads `site/jobs.json`, deployed to GitHub Pages.

## Consequences
- Free, no server or database to run, and every day's data change is visible in git history.
- Not built for thousands of updates a minute; fine for a daily feed. A database and an API
  would be the next step if the feed were embedded in an app.

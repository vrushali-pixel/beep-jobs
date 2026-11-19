# CLAUDE.md: notes for Claude Code on this repo

## What this is
A daily feed of real internship/fresher jobs in India from official company job boards,
de-duplicated, LLM-tagged (role, city, type, skills, red flags), shown on a static page.
Built for Beep's Gen AI & Engineering assignment (deadline Fri 20 Nov 2026, 11:59 PM IST).
Live: https://vrushali-pixel.github.io/beep-jobs/

## Commands
- `pip install -e ".[dev]"`, then `make test` (44 offline tests) and `make lint` (ruff)
- `fresherjobs run` (needs internet; `GEMINI_API_KEY` for AI tagging), `fresherjobs discover`,
  `fresherjobs sample`, `fresherjobs score FILE`
- `make serve` serves `site/` at http://localhost:8000

## Layout
- `config/` holds everything a person edits: `settings.yaml` (roles, cities, filter words, LLM),
  `companies.yaml` (job boards), `prompts/tagger_v2.md`
- `src/fresherjobs/` has one module per pipeline step: `sources/` → `filters.py` → `dedupe.py` →
  `tagging/` → `store.py` → `publish.py`; `pipeline.py` connects them; `cli.py` is the entry point
- `site/index.html` is the whole page; `data/` is written by the daily run (do not edit by hand)
- `docs/`: ARCHITECTURE, STORIES (S1–S19 = GitHub issues #1–#19), decisions/, BUILD_LOG

## Rules for changes
- Only official job-board APIs. Never scrape LinkedIn/Naukri/Indeed/Internshala/Glassdoor;
  never retry a 429 or work around a site's refusal (see docs/decisions/).
- Keep behaviour config-driven: prefer a change in `config/` over code.
- Every change: `make lint` and `make test` must pass; add a test for new behaviour.
- Add any real problem and its fix to `docs/BUILD_LOG.md` (it is the video's "what broke" script).
- Update the story status in `docs/STORIES.md` and its GitHub issue when a story is done.
- The daily bot commits `data/` and `site/jobs.json` every morning: always `git pull` before pushing.
- Commits: author Vrushali Patil, with a `Co-Authored-By: Claude` line.
- Explain each change in simple words: the owner must be able to explain and change it live.

## Open work (in order)
1. S1/S11/S12: add the free `GEMINI_API_KEY` repo secret, run the workflow, confirm 200+ live posts
   and LLM tags in `site/jobs.json`.
2. S11: `fresherjobs sample`, hand-check 50 posts (true_role, true_cities), `fresherjobs score`.
3. S12: put Gemini paid-tier prices in `config/settings.yaml` (llm.price_*) and report cost per 1,000.
4. Update README "Numbers", refresh `docs/img/` screenshots with LLM-tagged data.
5. Submission: Google Sheet/doc with data + AI tools + prompts; 5-min Loom (architecture, what broke).

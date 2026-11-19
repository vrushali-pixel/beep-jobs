# CLAUDE.md: notes for Claude Code on this repo

## What this is
A daily feed of real internship/fresher jobs in India from official company job boards,
de-duplicated, LLM-tagged (role, city, type, skills, red flags), shown on a static page.
Built for Beep's Gen AI & Engineering assignment (deadline Fri 20 Nov 2026, 11:59 PM IST).
Live: https://vrushali-pixel.github.io/beep-jobs/

## Commands
- `pip install -e ".[dev]"`, then `make test` (57 offline tests) and `make lint` (ruff)
- `fresherjobs run` (needs internet; `GEMINI_API_KEY` for AI tagging), `fresherjobs discover`,
  `fresherjobs sample`, `fresherjobs score FILE`
- `make serve` serves `site/` at http://localhost:8000

## Layout
- `config/` holds everything a person edits: `settings.yaml` (roles, cities, filter words, LLM),
  `companies.yaml` (job boards), `prompts/tagger_v3.md`
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

## Open work (in order, as of 19 Nov 2026)
Done: Gemini key + LLM tagging (S1/S3/S12), accuracy samples (S11, checked by Claude), README numbers,
screenshots, `docs/SUBMISSION.md`, `docs/VIDEO_SCRIPT.md`. Live: 243 posts after adding Workable/Recruitee/Breezy/Keka (BUILD_LOG #28, 19 Nov).
1. Owner spot-checks 5–10 rows of `eval/sample_50.csv` and `eval/sample_v2.csv`, then close issue #11.
2. Owner puts `docs/SUBMISSION.md` into the Google Doc/Sheet and records the Loom from `docs/VIDEO_SCRIPT.md`.
3. Just before submitting (deadline Fri 20 Nov 2026, 11:59 PM IST): `gh workflow disable daily.yml` to freeze the numbers.
4. Local note: this PC needs `git -c http.sslBackend=schannel pull/push` (certificate store).

# First Jobs India: fresher jobs and internships, refreshed daily

A live page of 200+ real internship and fresher job posts in India. Every post comes from a
company's **own official job board**. Duplicates are merged, an LLM tags each post by role and
city, and a scheduled job refreshes everything every morning at 6:10 AM IST.

- Live page: `https://<your-github-username>.github.io/<repo-name>/`
- Data: `site/jobs.json` (what the page shows), `data/jobs.csv` (same, for Sheets)

## How it works

```
 GitHub Actions, every day 6:10 AM IST
 ┌───────────────────────────────────────────────────────────────────────────┐
 │ 1 FETCH    official job-board APIs (Greenhouse, Lever, Ashby, SmartRecruiters)│
 │ 2 FILTER   India only · entry-level only · scam phrases   (free rules)       │
 │ 3 DE-DUPE  same link, or same company + same role → one post, all cities     │
 │ 4 TAG      LLM, new posts only, 20 per call → role, city, type, skills, flags │
 │ 5 MERGE    with yesterday: new / still open / closed                          │
 │ 6 PUBLISH  site/jobs.json → GitHub Pages; data committed back to the repo     │
 └───────────────────────────────────────────────────────────────────────────┘
                                   ↓
            index.html (static page: search, role tabs, city, job type)
```

| File | What it does |
|---|---|
| `config.yaml` | Role groups, cities, filter words, model, batch size. **Most changes happen here.** |
| `sources/companies.yaml` | Candidate company boards. `python -m pipeline.discover` keeps the real ones. |
| `pipeline/fetch.py` | One small function per job-board provider. |
| `pipeline/clean.py` | India / entry-level / scam rules and de-duplication. |
| `pipeline/tag.py` | LLM tagging: prompt, JSON schema, batching, cache, token count, fallback. |
| `prompts/tagger_v1.md` | The exact prompt sent to the model. |
| `pipeline/run.py` | The daily run, steps 1–6. |
| `site/index.html` | The page students see. |
| `eval/` | Pick 50 posts to hand-check, then score accuracy and cost. |
| `tests/` | Offline tests (no internet or API key needed): `python -m pytest -q` |

## Respecting each site's terms

- **Sources used:** each company's own job board, read through the provider's public postings API
  (Greenhouse Job Board API, Lever Postings API, Ashby Job Postings API, SmartRecruiters Posting API).
  These APIs exist so companies can show their open jobs publicly. No login, no scraping of pages.
- **Not used:** LinkedIn, Naukri, Indeed, Internshala, Glassdoor or any aggregator. Their terms
  forbid automated collection, and copying another job board's listings is not ours to republish.
- **Workday** (used by large MNCs like Cisco, Genpact, NTT DATA) has no documented public API. It is
  turned **on** (`workday_enabled: true`) because big graduate programmes live there: the run
  only sends the same search the public careers page sends (keywords like "intern", "graduate"),
  at most 5 searches per company, half a second apart, and keeps only basic fields. One line in
  `sources/companies.yaml` turns it off.
- Only title, company, place, date, pay and a short description are kept. Every Apply button
  links back to the original post. Requests are spaced out (`request_delay_sec`) and identify the tool.

## Keeping out fake and spam jobs

1. **Source-level:** only posts a company published on its own board.
2. **Clear rules first, AI for the grey zone:** clearly senior titles are dropped; titles that do not
   say the level ("Software Developer") are only kept if the LLM, reading the description, confirms
   0–1 years / students / new graduates can apply. Without an API key they are held back.
3. **Scam rules:** posts mentioning a registration fee, deposit, training fee and similar are rejected.
4. **LLM check:** the model returns `entry_level` and `red_flags`; posts failing either are hidden.
5. **Freshness:** a post missing from its board on the next run is marked closed and disappears.
   If a board is *down*, its posts are kept (not wiped) for up to 30 days.

Every rejected post and the reason is saved in `data/rejected_latest.json`.

## De-duplication

- Same link (after removing tracking parameters like `utm_*`) → duplicate.
- Same company (ignoring "Pvt Ltd", "India"…) and same role title (ignoring years, cities,
  brackets) → duplicate. A role listed separately for Bengaluru, Pune and Hyderabad becomes one
  card that lists all three cities.
- The post ID is built from company + cleaned title, so tomorrow's copy matches today's.

## LLM tagging

- Model: `gemini-2.5-flash-lite` on Google's **free tier** (set in `config.yaml`). Small and fast is
  enough for classification. Switch `provider: anthropic` + `model: claude-haiku-5-5` to use Claude;
  the code supports both.
- Free tier: no card needed, rate-limited. Calls are paced (`seconds_between_calls`) and the run stops
  calling after 3 failed batches in a row (quota used up); untagged posts are retried the next day.
  Only public job-post text is sent, never personal data.
- The model must answer in a strict JSON schema (Gemini `responseSchema`, Claude tool schema). `role_group` and `cities`
  are **enums**, so it cannot invent a role or spell a city two ways.
- 20 posts per call; only the first 900 characters of each description are sent.
- Results are cached per post and prompt version, so each post is paid for once.
  Changing the prompt file name (v1 → v2) re-tags everything.
- If there is no API key or a call fails twice, a keyword tagger fills in so the run never breaks
  (marked `tagger: keywords` in the data).

## Accuracy and cost

```bash
python -m eval.make_sample                      # eval/sample_50.csv: 50 random live posts
# open in Google Sheets, fill true_role and true_cities by reading each post, save as CSV
python -m eval.score eval/sample_50_checked.csv  # % correct for role, city, both + mistakes + cost
```

On the free tier the money actually spent is **$0**. The script also reports what the same tokens
would cost on the paid tier, so the number is comparable. Cost per 1,000 posts = (average input tokens × input price + average output tokens × output
price) per post × 1,000. Token counts come from the API's own usage numbers saved in
`data/runs.jsonl`. Put the model's prices in `config.yaml` (`llm.price_*_per_mtok_usd`).

## Setup (about 20 minutes)

1. Install Python 3.11+ and Git. Create a new **public** GitHub repo and push this folder to it.
2. `pip install -r requirements.txt`
3. `python -m pipeline.discover` checks the company boards and prints how many India entry-level posts exist.
   Commit the `sources/companies_verified.yaml` it writes.
4. Get a free key at aistudio.google.com (Get API key). GitHub repo → **Settings → Secrets and
   variables → Actions → New secret**: `GEMINI_API_KEY` = your key.
5. **Settings → Pages → Source: GitHub Actions.**
6. **Actions → Daily job refresh → Run workflow.** After 5–15 minutes the page is live at the URL
   shown in the run. From then on it runs by itself every morning.

Local run instead: `export ANTHROPIC_API_KEY=...` (Windows: `set ANTHROPIC_API_KEY=...`),
`python -m pipeline.run`, then `cd site && python -m http.server` and open http://localhost:8000.

## Changing things quickly

| Ask | Change |
|---|---|
| Add a city | `config.yaml → cities` (name + spellings) |
| Add or rename a role group | `config.yaml → roles` (key, label, hint) |
| Add a company | `sources/companies.yaml`, then run discover |
| Stricter fresher filter | `config.yaml → senior_title_words / entry_title_words` |
| Different refresh time | `.github/workflows/daily.yml → cron` (UTC) |
| Improve tagging | edit the prompt, save as `prompts/tagger_v2.md`, point `prompt_file` at it |
| Cheaper / better model | `config.yaml → llm.model` |

## What's next

- **Beep's own hiring partners** posting directly would be the best source: richer and fully trusted.
- Alerts ("3 new marketing internships in Pune") inside the app.
- A small "Report this job" button feeding the red-flag list.

# Submission: First Jobs India

Copy these sections into the Google Doc / Sheet for Beep's Gen AI & Engineering assignment.

## Links
- **Live page:** https://vrushali-pixel.github.io/beep-jobs/
- **Code:** https://github.com/vrushali-pixel/beep-jobs
- **Data (refreshed daily):** `site/jobs.json` (what the page shows) and `data/jobs.csv` (spreadsheet-friendly)
- **Video:** *(Loom link)*

## What it does
Every morning a GitHub Action reads ~11,600 posts from 127 companies' **official** job boards
(Greenhouse, Lever, Ashby, SmartRecruiters public APIs), keeps India roles a fresher can really
apply to, merges duplicates, tags each post with an LLM (role, city, type, skills, eligibility,
pay, scam red flags), and publishes a static search page. Closed jobs disappear the next day.

## Numbers (19 Nov 2026)
| Step | Posts |
|---|---|
| Fetched from 127 boards | 11,625 |
| Outside India | 8,905 dropped |
| Senior title | 1,705 dropped |
| Requires 1+ years of experience (plain rule) | 547 dropped |
| Screened by the LLM (after merging 68 duplicates) | 400 |
| **Live** | **93** |

- **Accuracy:** role 94% / city 98% on 50 random posts; role 89% / city 100% on a second, fresh
  sample of 28 posts. Checked by Claude against each full post (owner spot-check).
- **Cost:** $0.39 per 1,000 posts at Gemini 3.5 Flash-Lite paid prices (280 input + 121 output
  tokens per post, measured over 2,148 LLM-tagged posts). Actually paid: $0 (free tier). Only new
  posts are sent to the LLM; answers are cached per prompt version.
- **Why 93, not 200:** fewer than 1% of India posts on these boards are truly fresher in November
  (campus hiring opens Jan–Mar). I chose not to pad the count: a fresh check found 16 of 50 posts
  that asked for 1–8 years of experience, and the pipeline now drops them. More companies = one
  line each in `config/companies.yaml`.

## AI tools used
| Tool | Used for |
|---|---|
| **Gemini 3.5 Flash-Lite** (Google AI Studio, free tier) | In the product: tags every new post (role, city, type, skills, eligibility, pay, red flags) and decides whether an unclear title is open to freshers |
| **Claude Code (Claude Opus 5.5)** | Building it with me: code, tests, docs, debugging the daily runs, probing job boards, checking the 50-post accuracy samples |
| Provider interface | The tagger also runs on Claude (`llm.provider: anthropic`); I moved to Gemini's free tier when the Claude API account had no credit (build log #19) |

## Prompts
- **Tagging prompt:** `config/prompts/tagger_v3.md` (v1 → v2 → v3, each change explained in
  `docs/BUILD_LOG.md` #26 and #27). Roles and cities are filled in from `config/settings.yaml`, and
  the answer must match a strict JSON schema where role and city are enums, so the model cannot
  invent them.
- **What the model gets per post:** title, company, location, the start of the description plus
  every later sentence about experience or eligibility, and `check_experience` when the title
  alone cannot say whether a fresher can apply.

## What broke (highlights from `docs/BUILD_LOG.md`)
1. Cloud sandbox could not reach job APIs → moved the pipeline to GitHub Actions (#1).
2. Workday career sites answered 429 to GitHub's servers → respected it, no retries (#18).
3. Claude API had no credit → provider-agnostic tagger on Gemini's free tier (#19).
4. New Gemini keys get 404 for `gemini-2.5-flash-lite` → one-line config switch to 3.5 (#24).
5. With working AI only 86 posts → probed ~430 boards, added 15; did not relax the rules (#25).
6. Accuracy check found experienced roles slipping through: the AI saw only the first 900
   characters, and sometimes ignored "1–3 years" even when it saw it → plain rule + prompt v3 (#26, #27).

# User stories

Two kinds of users: **students** looking for their first job, and the **maintainer/reviewer** who
runs the feed and must trust it. Each story has "done when" checks, its status, and the code and
tests that satisfy it. The same stories are tracked as GitHub Issues (label `story`).

Status: ✅ done · 🟡 in progress · ⏭ next

## Epic A: a student finds a real first job, fast

| # | Story | Done when | Status | Where |
|---|---|---|---|---|
| [S1](https://github.com/vrushali-pixel/beep-jobs/issues/1) | As a student, I see **200+ real entry-level posts in India** | The page lists 200+ live posts, every one linking to the company's own careers page | 🟡 58 live from clear titles; the LLM step (free Gemini key) judges ~800 unclear titles to pass 200 | `sources/`, `pipeline.py` |
| [S2](https://github.com/vrushali-pixel/beep-jobs/issues/2) | As a student, I **never see the same job twice** | Reposts and multi-city copies merge into one card that lists all cities | ✅ | `dedupe.py` · `test_dedupe.py` |
| [S3](https://github.com/vrushali-pixel/beep-jobs/issues/3) | As a student, I understand **the role, city and what is needed** at a glance | Each card shows a plain role name, company, city, type, skills/eligibility, pay | ✅ (skills/eligibility come from the LLM) | `tagging/`, `site/index.html` |
| [S4](https://github.com/vrushali-pixel/beep-jobs/issues/4) | As a student, I can **search and filter** by role, city and job type | Search box, role tabs with counts, city menu, Internship/Job/Trainee toggle | ✅ | `site/index.html` |
| [S5](https://github.com/vrushali-pixel/beep-jobs/issues/5) | As a student, I am **protected from fake and paid jobs** | Only official boards; posts asking for fees are dropped; LLM red flags hide a post; reasons are logged | ✅ | `filters.py`, `tagging/prompt.py` · `test_filters.py` |
| [S6](https://github.com/vrushali-pixel/beep-jobs/issues/6) | As a student, I see **fresh jobs every day** without anyone updating the site | A scheduled run publishes daily; the page shows the update date | ✅ | `.github/workflows/daily.yml` |
| [S7](https://github.com/vrushali-pixel/beep-jobs/issues/7) | As a student, I **don't click on closed jobs** | Posts missing from a board that answered are closed and hidden next day | ✅ | `store.py` · `test_pipeline.py` |
| [S8](https://github.com/vrushali-pixel/beep-jobs/issues/8) | As a student, I can **spot today's new posts** | NEW badge and "N new today" in the header | ✅ | `site/index.html` |
| [S9](https://github.com/vrushali-pixel/beep-jobs/issues/9) | As a student on a **phone**, the page is easy to use | One column, big tap targets, no sideways scrolling at 375px | ✅ | `site/index.html` |

## Epic B: the maintainer can run, trust and change it

| # | Story | Done when | Status | Where |
|---|---|---|---|---|
| [S10](https://github.com/vrushali-pixel/beep-jobs/issues/10) | As the maintainer, I **respect every site's terms** | Only documented public posting APIs; a 429 is never retried; no login/scraping | ✅ | ADR [0001](decisions/0001-official-job-boards-only.md), [0003](decisions/0003-workday.md) |
| [S11](https://github.com/vrushali-pixel/beep-jobs/issues/11) | As a reviewer, I know **how accurate the tagging is** | 50 random posts hand-checked; % correct for role, city, both; mistakes listed | 🟡 needs LLM tags, then the hand check | `evaluation.py` · `test_evaluation.py` |
| [S12](https://github.com/vrushali-pixel/beep-jobs/issues/12) | As a reviewer, I know **what tagging costs per 1,000 posts** | Real token counts per post from every run, priced at the paid tier | 🟡 needs the first LLM run | `data/runs.jsonl`, `evaluation.py` |
| [S13](https://github.com/vrushali-pixel/beep-jobs/issues/13) | As the maintainer, **one failure never breaks the run** | A dead board, a failed LLM call or a used-up quota is logged and the run still publishes | ✅ | `sources/__init__.py`, `tagging/tagger.py`, `store.py` · tests |
| [S14](https://github.com/vrushali-pixel/beep-jobs/issues/14) | As the maintainer, I can **add a city, role or company without code** | All of these are in `config/` | ✅ | `config/settings.yaml`, `config/companies.yaml` |
| [S15](https://github.com/vrushali-pixel/beep-jobs/issues/15) | As the maintainer, it **costs nothing to run** | GitHub Actions + Pages + Gemini free tier; LLM only for new posts | ✅ | ADR [0004](decisions/0004-free-llm-provider-agnostic.md), [0005](decisions/0005-static-site-on-github.md) |
| [S16](https://github.com/vrushali-pixel/beep-jobs/issues/16) | As a developer, **every change is tested** | Lint + 43 offline tests run on every push (Python 3.10 and 3.12) | ✅ | `.github/workflows/ci.yml` |

## Next

| # | Story | Why |
|---|---|---|
| [S17](https://github.com/vrushali-pixel/beep-jobs/issues/17) | As a student, I can **report a suspicious job** | Feeds the red-flag list from real users |
| [S18](https://github.com/vrushali-pixel/beep-jobs/issues/18) | As Beep, we can **add our hiring partners' jobs directly** | The richest and most trusted source |
| [S19](https://github.com/vrushali-pixel/beep-jobs/issues/19) | As a student, I get **alerts** ("3 new marketing internships in Pune") | Brings students back without effort |

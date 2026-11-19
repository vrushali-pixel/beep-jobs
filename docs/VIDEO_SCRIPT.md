# 5-minute Loom: script

Have open: the live page, the GitHub repo, `docs/BUILD_LOG.md`, the Actions tab.

**0:00–0:30 · The problem**
"Students looking for a first job see fake paid 'jobs' and listings that never say if a fresher
can apply. I built a daily feed of real fresher jobs in India, only from companies' own job boards."

**0:30–1:30 · Demo (live page)**
- Header: number of openings, date, "new today".
- Filter: Internships → a city → a role. Search "Python".
- Open one card: role, city, skills, eligibility, "Official careers page", Apply goes to the company.
- On a phone width (or show `docs/img/page-mobile.png`).

**1:30–2:45 · Architecture (README diagram)**
- GitHub Action every morning → fetch 147 boards on 8 platforms via public feeds → rules (India, senior titles,
  "requires 1+ years", scam phrases) → de-duplicate → Gemini tags only the unclear/new posts →
  merge with yesterday (new / closed) → publish `site/jobs.json` → GitHub Pages.
- "Rules first, LLM for the grey zone": cheap and predictable, LLM only where a title can't say.
- Strict JSON schema with enums; cache per prompt version; if the LLM fails, keyword fallback and
  the run still publishes.
- Everything a person changes is in `config/`: cities, roles, companies, the prompt.

**2:45–4:15 · What broke (BUILD_LOG)**
Pick 3–4:
1. Workday refused GitHub (429): I respect it, no workarounds.
2. Claude had no credit → made the tagger provider-agnostic, moved to Gemini free tier.
3. First Gemini run: every call 404 → new keys can't use 2.5 Flash-Lite → one config line.
4. The best one: my accuracy check showed 16 of 50 "fresher" posts asked for 1–8 years. Cause:
   the AI only saw the first 900 characters, and sometimes ignored "1–3 years" anyway. Fix: send
   the experience sentences + a plain rule in code, with tests from real posts. "I made the same
   mistake myself when I read only the start of the posts."

**4:15–5:00 · Numbers and next**
- 13,274 posts → 243 live; role accuracy 89–94%, city 98–100%; $0.39 per 1,000 posts, $0 paid.
- "It was stuck at 93 because Indian startups don't use the US job-board platforms. I added Workable,
  Recruitee, Breezy and Keka, the feeds their own careers pages use, and it went to 243 with the same
  strict rules. Each company is one config line. Next: Beep's hiring partners as a source, report a
  suspicious job, alerts."

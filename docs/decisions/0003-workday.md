# 3. Workday career sites: tried, refused, switched off

**Status:** superseded by evidence · 17 Nov 2026

## Context
Large MNCs (Cisco, Genpact, NTT DATA, S&P Global…) run their graduate programmes on Workday
career sites. Workday has no documented public API; the public careers page calls an internal
search endpoint. To reach 200+ posts we decided to try it, slowly: 5 keyword searches per
company, half a second apart, basic fields only.

## What happened
Across two runs, almost every Workday site (16 of 17 on the first try) answered **HTTP 429 Too
Many Requests** to the very first request from GitHub's servers. The one or two that answered
gave 9 posts (Kaleris, Piramal Pharma).

## Decision
Treat 429 as the site saying no. No retries, no workarounds (other IPs, browsers, delays).
The fetcher logs "site refused automated requests (429), skipped", and Workday is turned off
in `config/companies.yaml` (`workday_enabled: false`). The code stays, documented, in case a
company offers an official feed.

## Consequences
Those 9 posts are closed once the source is off (BUILD_LOG #23). Fewer MNC graduate posts. Volume has to come from official job-board APIs and from the LLM
judging unclear titles (decision 2).

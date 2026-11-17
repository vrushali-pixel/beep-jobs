# 1. Read only companies' official job boards

**Status:** accepted · 17 Nov 2026

## Context
The tool must collect real fresher posts "from public sources (respect each site's terms)", and
students must be protected from spam and fake jobs. Job aggregators (LinkedIn, Naukri, Indeed,
Internshala, Glassdoor) have the most posts, but their terms forbid automated collection, and
reposting another job board's listings is not ours to do. Fresher-job blogs link to real posts
but mix in ads and stale openings.

## Decision
Read each company's **own** job board through its provider's public postings API: Greenhouse
Job Board API, Lever Postings API, Ashby Job Postings API, SmartRecruiters Posting API. These
APIs exist so companies can show their openings publicly. Keep only title, company, place, date,
pay and a short description; every Apply button links to the original post. Requests are spaced
(`request_delay_sec`) and identify the tool in the User-Agent.

## Consequences
- Every post was published by the company itself, which removes most fake jobs at the source.
- Fewer posts: most of these companies hire mainly outside India (on 17 Nov, 8,000+ of 10,000
  fetched posts were outside India). Volume depends on finding India-heavy boards and on the
  LLM judging unclear titles (decision 2).
- Adding a company is one line in `config/companies.yaml`.

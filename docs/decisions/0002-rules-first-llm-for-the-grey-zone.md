# 2. Cheap rules first, LLM only for the grey zone

**Status:** accepted · 17 Nov 2026

## Context
Out of ~10,000 posts a day, most decisions are obvious from the title or location ("Senior
Engineer", "San Francisco"). Sending everything to an LLM would be slow and cost money for no
gain. But ~800 India posts a day have titles like "Software Developer" or "Business Analyst"
that do not say whether a fresher can apply; only the description does.

## Decision
1. Rules (free, predictable, unit-tested) answer each post with KEEP, DROP + reason, or ASK_AI.
2. Only KEEP and ASK_AI posts go to the LLM, in batches of 25, each post once (cached by
   prompt version + post id).
3. The LLM answers in a **strict JSON schema** where `role_group` and `cities` are enums, so it
   cannot invent a role or spell a city two ways. Output is validated again in code.
4. For ASK_AI posts the prompt sets `check_experience: true`: keep only if the description
   clearly allows 0–1 years, students or new graduates.
5. With no LLM available, a keyword tagger fills in and ASK_AI posts are held back (never
   published unchecked).

## Consequences
- LLM cost scales with *new* posts per day, not with everything fetched.
- The keyword tagger doubles as the baseline to show what the LLM adds.
- Changing the prompt is a new file (`tagger_v2.md`), which re-tags everything under the new version.

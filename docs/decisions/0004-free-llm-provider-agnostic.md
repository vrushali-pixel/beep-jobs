# 4. Provider-agnostic tagging, Gemini free tier by default

**Status:** accepted · 17 Nov 2026

## Context
Tagging started on Claude (claude-haiku-5-5). The API account was on the free evaluation plan
with a $0 balance, so every call was rejected for missing credit. This is a demo with no budget.
GitHub's built-in free models, the other obvious option, were retired on 30 July 2026.

## Decision
- One small `Provider` interface (`tag(system, schema, user) -> answers, input tokens, output tokens`)
  with two implementations: `GeminiProvider` (REST, `responseSchema`) and `AnthropicProvider`
  (Messages API, forced tool call). Adding another is one class.
- Default: `gemini-2.5-flash-lite` on Google's free tier (no card). Calls are paced
  (`seconds_between_calls: 7`); after 3 failed batches in a row the run stops calling, uses the
  keyword fallback, and retries those posts the next day.
- Only public job-post text is sent, never personal data (Google may use free-tier requests to
  improve its products).

## Consequences
- $0 actually spent. Cost per 1,000 posts is still reported from real token counts, priced at
  the paid tier, so the number is comparable and honest.
- Switching to Claude is two lines in `config/settings.yaml` plus an `ANTHROPIC_API_KEY` secret.

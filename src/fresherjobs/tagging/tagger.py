"""Step 5, TAG: send new posts to the LLM in batches, cache the answers, count tokens.

- Each post is tagged once per prompt version (cache key = prompt file name + post id).
- Calls are paced to stay inside free-tier per-minute limits.
- After 3 failed batches in a row (daily quota used up) it stops calling; the keyword
  fallback fills in and those posts are retried on the next run.
"""

from __future__ import annotations

import json
import os
import time
from collections.abc import Callable
from typing import Any

from fresherjobs.filters import Rules
from fresherjobs.models import RawPost, Tags
from fresherjobs.tagging.fallback import keyword_tag
from fresherjobs.tagging.prompt import answer_schema, build_prompt, user_message, validate
from fresherjobs.tagging.providers import Provider, make_provider


class Tagger:
    def __init__(self, cfg: dict[str, Any], rules: Rules, cache_path: str,
                 provider: Provider | None = None, use_env: bool = True) -> None:
        self.cfg, self.rules, self.cache_path = cfg, rules, cache_path
        llm = cfg["llm"]
        self.model = llm["model"]
        self.version = os.path.basename(llm["prompt_file"])
        self.provider = provider or (make_provider(llm) if use_env else None)
        self.cache: dict[str, Tags] = {}
        if os.path.exists(cache_path):
            with open(cache_path, encoding="utf-8") as f:
                self.cache = json.load(f)
        self.usage = {"calls": 0, "input_tokens": 0, "output_tokens": 0, "posts_llm": 0, "posts_fallback": 0}
        self.system = build_prompt(cfg)
        self.schema = answer_schema(cfg)
        self.gap = float(llm.get("seconds_between_calls", 0))
        self._last_call = 0.0

    @property
    def available(self) -> bool:
        return self.provider is not None

    def _key(self, post_id: str) -> str:
        return f"{self.version}:{post_id}"

    def already_tagged(self, post_id: str) -> bool:
        """True if the LLM (not the keyword fallback) has already answered for this post."""
        hit = self.cache.get(self._key(post_id))
        return bool(hit) and hit.get("tagger") != "keywords"

    def _call(self, batch: list[RawPost]) -> dict[str, dict]:
        wait = self.gap - (time.time() - self._last_call)
        if wait > 0:
            time.sleep(wait)
        self._last_call = time.time()
        assert self.provider is not None
        posts, tin, tout = self.provider.tag(self.system, self.schema,
                                             user_message(batch, self.cfg["llm"]["max_desc_chars"]))
        self.usage["calls"] += 1
        self.usage["input_tokens"] += tin
        self.usage["output_tokens"] += tout
        return posts

    def tag(self, posts: list[RawPost], log: Callable[[str], None] = print) -> dict[str, Tags]:
        # keyword tags are free, so they are always redone (and upgraded when an LLM is available)
        todo = [p for p in posts if not self.already_tagged(p["id"])]
        size = self.cfg["llm"]["batch_size"]
        failed_in_a_row = 0
        for i in range(0, len(todo), size):
            batch = todo[i:i + size]
            got: dict[str, dict] = {}
            for attempt in range(2):
                if not self.available or failed_in_a_row >= 3:
                    break
                try:
                    got = self._call(batch)
                    failed_in_a_row = 0
                    break
                except Exception as e:  # noqa: BLE001 - tagging must never stop the run
                    log(f"  ! tag batch {i // size}: {type(e).__name__} {str(e)[:300]}")
                    failed_in_a_row += attempt      # counts once both tries of a batch failed
                    time.sleep(3)
            for p in batch:
                if p["id"] in got:
                    t = validate(dict(got[p["id"]], tagger=self.model), self.cfg)
                    self.usage["posts_llm"] += 1
                else:
                    t = keyword_tag(p, self.cfg, self.rules)
                    self.usage["posts_fallback"] += 1
                self.cache[self._key(p["id"])] = t
        os.makedirs(os.path.dirname(self.cache_path) or ".", exist_ok=True)
        with open(self.cache_path, "w", encoding="utf-8") as f:
            json.dump(self.cache, f, ensure_ascii=False)
        return {p["id"]: self.cache[self._key(p["id"])] for p in posts}

    def cost_usd(self) -> float | None:
        llm = self.cfg["llm"]
        pin, pout = llm.get("price_input_per_mtok_usd"), llm.get("price_output_per_mtok_usd")
        if pin is None or pout is None:
            return None
        return self.usage["input_tokens"] / 1e6 * pin + self.usage["output_tokens"] / 1e6 * pout

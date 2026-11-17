"""Step 5: TAG with an LLM. Only NEW posts are sent, in batches, and results are cached,
so each post is paid for once. Token use is recorded for the cost-per-1,000 number.
If there is no API key, or a batch fails twice, a simple keyword tagger fills in so the
daily run never breaks."""
import json
import os
import re
import time

JOB_TYPES = ["internship", "apprentice", "fulltime"]


def build_prompt(cfg):
    text = open(cfg["llm"]["prompt_file"], encoding="utf-8").read()
    roles = "\n".join(f"  - {k}: {v['hint']}" for k, v in cfg["roles"].items())
    return text.replace("{ROLE_LIST}", roles).replace("{CITY_LIST}", ", ".join(cfg["cities"]))


def tool_schema(cfg):
    return {
        "name": "save_tags",
        "description": "Save the tags for every post in this batch.",
        "input_schema": {
            "type": "object",
            "properties": {"posts": {"type": "array", "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "entry_level": {"type": "boolean"},
                    "role_group": {"type": "string", "enum": list(cfg["roles"])},
                    "clean_title": {"type": "string"},
                    "cities": {"type": "array", "items": {"type": "string", "enum": list(cfg["cities"])}},
                    "job_type": {"type": "string", "enum": JOB_TYPES},
                    "skills": {"type": "array", "items": {"type": "string"}, "maxItems": 5},
                    "eligibility": {"type": "string"},
                    "pay": {"type": "string"},
                    "red_flags": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["id", "entry_level", "role_group", "clean_title", "cities", "job_type",
                             "skills", "eligibility", "pay", "red_flags"],
            }}},
            "required": ["posts"],
        },
    }


def post_for_llm(p, max_chars):
    return {"id": p["id"], "title": p["title"], "company": p["company"], "location": p["location"],
            "check_experience": bool(p.get("needs_ai")),
            "employment_type": p.get("employment_type", ""), "pay": p.get("pay", ""),
            "description": re.sub(r"\s+", " ", p["description"])[:max_chars]}


def validate(t, cfg):
    t["cities"] = [c for c in t.get("cities", []) if c in cfg["cities"]]
    if t.get("role_group") not in cfg["roles"]:
        t["role_group"] = "other"
    if t.get("job_type") not in JOB_TYPES:
        t["job_type"] = "fulltime"
    t["skills"] = [s for s in t.get("skills", []) if s][:5]
    return t


def keyword_tag(p, cfg, rules):
    """Fallback tagger (also our baseline to compare the LLM against)."""
    title = p["title"].lower()
    best, score = "other", 0
    for key, v in cfg["roles"].items():
        words = [w.strip() for w in v["hint"].lower().split(",")]
        s = sum(2 for w in words if w and re.search(r"\b" + re.escape(w) + r"\b", title))
        if s > score:
            best, score = key, s
    jt = "internship" if re.search(r"\bintern", title) else \
         "apprentice" if re.search(r"trainee|apprentice|articleship", title) else "fulltime"
    # Without the LLM we cannot read the description, so unclear titles are not published.
    return {"id": p["id"], "entry_level": not p.get("needs_ai"), "role_group": best, "clean_title": p["title"][:60],
            "cities": rules.cities_in(p["location"]), "job_type": jt, "skills": [], "eligibility": "",
            "pay": p.get("pay", ""), "red_flags": [], "tagger": "keywords"}


class Tagger:
    def __init__(self, cfg, rules, cache_path="data/tags_cache.json"):
        self.cfg, self.rules, self.cache_path = cfg, rules, cache_path
        self.version = os.path.basename(cfg["llm"]["prompt_file"])
        self.cache = json.load(open(cache_path)) if os.path.exists(cache_path) else {}
        self.usage = {"calls": 0, "input_tokens": 0, "output_tokens": 0, "posts_llm": 0, "posts_fallback": 0}
        self.client = None
        if os.environ.get("ANTHROPIC_API_KEY"):
            import anthropic
            self.client = anthropic.Anthropic()
        self.system = build_prompt(cfg)
        self.tool = tool_schema(cfg)

    def already_tagged(self, post_id):
        hit = self.cache.get(f"{self.version}:{post_id}")
        return bool(hit) and hit.get("tagger") != "keywords"

    def _key(self, p):
        return f"{self.version}:{p['id']}"

    def _call(self, batch):
        llm = self.cfg["llm"]
        payload = [post_for_llm(p, llm["max_desc_chars"]) for p in batch]
        msg = self.client.messages.create(
            model=llm["model"], max_tokens=4000,
            system=self.system, tools=[self.tool], tool_choice={"type": "tool", "name": "save_tags"},
            messages=[{"role": "user", "content": "Tag these posts:\n" + json.dumps(payload, ensure_ascii=False)}],
        )
        self.usage["calls"] += 1
        self.usage["input_tokens"] += msg.usage.input_tokens
        self.usage["output_tokens"] += msg.usage.output_tokens
        block = next(b for b in msg.content if b.type == "tool_use")
        return {t["id"]: t for t in block.input.get("posts", [])}

    def tag(self, posts, log=print):
        def needs_tag(p):
            hit = self.cache.get(self._key(p))
            # retry keyword-only tags once a key is available
            return hit is None or (self.client and hit.get("tagger") == "keywords")
        todo = [p for p in posts if needs_tag(p)]
        size = self.cfg["llm"]["batch_size"]
        for i in range(0, len(todo), size):
            batch = todo[i:i + size]
            got = {}
            for attempt in range(2):
                if not self.client:
                    break
                try:
                    got = self._call(batch)
                    break
                except Exception as e:
                    log(f"  ! tag batch {i // size}: {type(e).__name__} {str(e)[:300]}")
                    time.sleep(3)
            for p in batch:
                if p["id"] in got:
                    t = validate(dict(got[p["id"]], tagger=self.cfg["llm"]["model"]), self.cfg)
                    self.usage["posts_llm"] += 1
                else:                                     # missing from reply, or no key
                    t = keyword_tag(p, self.cfg, self.rules)
                    self.usage["posts_fallback"] += 1
                self.cache[self._key(p)] = t
        json.dump(self.cache, open(self.cache_path, "w"), ensure_ascii=False)
        return {p["id"]: self.cache[self._key(p)] for p in posts}

    def cost_usd(self):
        pi, po = self.cfg["llm"].get("price_input_per_mtok_usd"), self.cfg["llm"].get("price_output_per_mtok_usd")
        if pi is None or po is None:
            return None
        return self.usage["input_tokens"] / 1e6 * pi + self.usage["output_tokens"] / 1e6 * po

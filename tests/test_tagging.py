"""LLM tagging with fake providers, the real-SDK guard, the keyword fallback and the prompt."""

import inspect
import json
from types import SimpleNamespace

import pytest

from conftest import make_post
from fresherjobs.dedupe import dedupe
from fresherjobs.tagging import Tagger, keyword_tag
from fresherjobs.tagging.prompt import answer_schema, build_prompt
from fresherjobs.tagging.providers import AnthropicProvider, GeminiProvider, gemini_schema


def _ids(user_text):
    return [p["id"] for p in json.loads(user_text.split("\n", 1)[1])]


class FakeProvider:
    """Answers every post except the last one in each batch (models sometimes skip one)."""
    name = "fake"

    def __init__(self):
        self.calls = []

    def tag(self, system, schema, user):
        self.calls.append(user)
        out = {i: {"id": i, "entry_level": True, "role_group": "data_ai", "clean_title": "Data Analyst Intern",
                   "cities": ["Bengaluru", "Atlantis"], "job_type": "internship", "skills": ["SQL"],
                   "eligibility": "", "pay": "", "red_flags": []} for i in _ids(user)[:-1]}
        return out, 1000, 200


def test_tagger_uses_llm_validates_caches_and_falls_back(cfg, rules, tmp_path):
    fake = FakeProvider()
    t = Tagger(cfg, rules, str(tmp_path / "cache.json"), provider=fake)
    t.gap = 0
    posts, _ = dedupe([make_post("Data Analyst Intern", c) for c in ("Bengaluru", "Delhi")]
                      + [make_post("HR Intern"), make_post("Coding Intern")], rules)
    res = t.tag(posts, log=lambda *a: None)
    llm = [r for r in res.values() if r["tagger"] == cfg["llm"]["model"]]
    assert len(fake.calls) == 1 and t.usage["input_tokens"] == 1000
    assert llm and all(r["cities"] == ["Bengaluru"] for r in llm)          # invented city dropped
    assert t.usage["posts_fallback"] == 1                                   # skipped post -> keywords
    t.tag(posts, log=lambda *a: None)                                       # cached: only the fallback retried
    assert len(fake.calls) == 2 and len(_ids(fake.calls[1])) == 1


def test_no_provider_means_keywords_and_unclear_titles_held_back(cfg, rules, tmp_path):
    t = Tagger(cfg, rules, str(tmp_path / "c.json"), use_env=False)
    posts, _ = dedupe([dict(make_post("Business Analyst"), needs_ai=True), make_post("HR Intern")], rules)
    res = t.tag(posts, log=lambda *a: None)
    by_title = {p["title"]: res[p["id"]] for p in posts}
    assert by_title["Business Analyst"]["entry_level"] is False and by_title["HR Intern"]["role_group"] == "hr"


def test_anthropic_provider_sends_only_arguments_the_real_sdk_accepts(cfg):
    """A fake client once hid a bug (the SDK dropped `temperature`), so check the real signature."""
    import anthropic
    sent = {}

    def create(**kw):
        sent.update(kw)
        return SimpleNamespace(usage=SimpleNamespace(input_tokens=5, output_tokens=2),
                               content=[SimpleNamespace(type="tool_use", input={"posts": [{"id": "a"}]})])

    p = AnthropicProvider("claude-haiku-5-5", client=SimpleNamespace(messages=SimpleNamespace(create=create)))
    posts, tin, tout = p.tag("sys", answer_schema(cfg), "Tag these posts:\n[]")
    real = set(inspect.signature(anthropic.resources.Messages.create).parameters)
    assert set(sent) <= real, set(sent) - real
    assert posts == {"a": {"id": "a"}} and (tin, tout) == (5, 2) and sent["tool_choice"]["name"] == "save_tags"


def test_gemini_provider(cfg, monkeypatch):
    import requests
    sent = {}

    class Resp:
        status_code = 200

        def raise_for_status(self):
            pass

        def json(self):
            out = {"posts": [{"id": "x1", "role_group": "hr"}]}
            return {"candidates": [{"content": {"parts": [{"text": json.dumps(out)}]}}],
                    "usageMetadata": {"promptTokenCount": 900, "candidatesTokenCount": 150, "thoughtsTokenCount": 10}}

    def fake_post(url, headers, json, timeout):
        sent.update(url=url, headers=headers, body=json)
        return Resp()

    monkeypatch.setattr(requests, "post", fake_post)
    posts, tin, tout = GeminiProvider("gemini-3.5-flash-lite", "k").tag("sys", answer_schema(cfg), "hi")
    assert posts == {"x1": {"id": "x1", "role_group": "hr"}} and (tin, tout) == (900, 160)
    schema = sent["body"]["generationConfig"]["responseSchema"]
    assert schema["type"] == "OBJECT" and "enum" in schema["properties"]["posts"]["items"]["properties"]["role_group"]
    assert sent["headers"]["x-goog-api-key"] == "k" and ":generateContent" in sent["url"]


def test_gemini_schema_drops_unsupported_keys():
    assert gemini_schema({"type": "array", "maxItems": 5, "items": {"type": "string"}}) == \
        {"type": "ARRAY", "items": {"type": "STRING"}}


@pytest.mark.parametrize("title,role", [
    ("Software Development Engineer Intern", "coding"),
    ("2026/02: HW Developer for Electronic Control Unit", "core_engg"),
    ("Associate Software Test Engineer (Playwright)", "qa"),
    ("Product  Ops Intern", "product"),
    ("Intern - Talent Acquisition", "hr"),
    ("Payroll Industrial Trainee", "finance"),
    ("Customer Experience Engineer, L1", "support"),
    ("Machine Learning Intern", "data_ai"),
])
def test_keyword_fallback_roles(cfg, rules, title, role):
    assert keyword_tag({"id": "x", "title": title, "location": "", "pay": ""}, cfg, rules)["role_group"] == role


def test_prompt_lists_every_role_and_city(cfg):
    p = build_prompt(cfg)
    assert all(k in p for k in cfg["roles"]) and all(c in p for c in cfg["cities"]) and "{ROLE_LIST}" not in p

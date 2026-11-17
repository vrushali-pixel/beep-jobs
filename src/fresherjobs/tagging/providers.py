"""LLM providers. Each one takes (system prompt, answer schema, user message) and returns
(answers by post id, input tokens, output tokens). Adding a provider = adding one class."""

from __future__ import annotations

import json
import os
import time
from typing import Any, Protocol

import requests


class Provider(Protocol):
    name: str

    def tag(self, system: str, schema: dict[str, Any], user: str) -> tuple[dict[str, dict], int, int]: ...


class AnthropicProvider:
    """Claude via the Messages API; the answer comes back as a forced tool call."""

    name = "anthropic"

    def __init__(self, model: str, client: Any = None) -> None:
        import anthropic
        self.model = model
        self.client = client or anthropic.Anthropic()

    def tag(self, system: str, schema: dict[str, Any], user: str) -> tuple[dict[str, dict], int, int]:
        msg = self.client.messages.create(
            model=self.model, max_tokens=4000, system=system,
            tools=[{"name": "save_tags", "description": "Save the tags for every post in this batch.",
                    "input_schema": schema}],
            tool_choice={"type": "tool", "name": "save_tags"},
            messages=[{"role": "user", "content": user}],
        )
        block = next(b for b in msg.content if b.type == "tool_use")
        posts = {t["id"]: t for t in block.input.get("posts", [])}
        return posts, msg.usage.input_tokens, msg.usage.output_tokens


def gemini_schema(schema: dict[str, Any]) -> dict[str, Any]:
    """Gemini's responseSchema dialect: UPPERCASE types, no maxItems."""
    out: dict[str, Any] = {"type": schema["type"].upper()}
    if "enum" in schema:
        out["enum"] = schema["enum"]
    if "properties" in schema:
        out["properties"] = {k: gemini_schema(v) for k, v in schema["properties"].items()}
        out["required"] = schema.get("required", list(schema["properties"]))
    if "items" in schema:
        out["items"] = gemini_schema(schema["items"])
    return out


class GeminiProvider:
    """Google Gemini via REST, structured JSON output. Works on the free tier."""

    name = "gemini"
    URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

    def __init__(self, model: str, api_key: str) -> None:
        self.model, self.api_key = model, api_key

    def tag(self, system: str, schema: dict[str, Any], user: str) -> tuple[dict[str, dict], int, int]:
        r = requests.post(
            self.URL.format(model=self.model),
            headers={"x-goog-api-key": self.api_key, "Content-Type": "application/json"},
            json={"systemInstruction": {"parts": [{"text": system}]},
                  "contents": [{"role": "user", "parts": [{"text": user}]}],
                  "generationConfig": {"temperature": 0, "responseMimeType": "application/json",
                                       "responseSchema": gemini_schema(schema)}},
            timeout=180)
        if r.status_code == 429:      # free-tier limit: wait so the caller's retry can succeed
            time.sleep(40)
        r.raise_for_status()
        data = r.json()
        usage = data.get("usageMetadata", {})
        text = data["candidates"][0]["content"]["parts"][0]["text"]
        posts = {t["id"]: t for t in json.loads(text).get("posts", [])}
        out_tokens = usage.get("candidatesTokenCount", 0) + usage.get("thoughtsTokenCount", 0)
        return posts, usage.get("promptTokenCount", 0), out_tokens


def make_provider(llm_cfg: dict[str, Any]) -> Provider | None:
    """The provider named in config, or None when its API key is not set."""
    name, model = llm_cfg.get("provider", "gemini"), llm_cfg["model"]
    if name == "gemini" and os.environ.get("GEMINI_API_KEY"):
        return GeminiProvider(model, os.environ["GEMINI_API_KEY"])
    if name == "anthropic" and os.environ.get("ANTHROPIC_API_KEY"):
        return AnthropicProvider(model)
    return None

"""LLM backends for the Forum demo.

Four interchangeable backends (STRATEGY.md §4 — vendor independence is a
legitimacy requirement, and it starts here):

- claude-cli    : shells out to the `claude` CLI; runs on a Claude subscription
                  with no API key.
- anthropic-api : Anthropic SDK; needs ANTHROPIC_API_KEY.
- openai-api    : OpenAI SDK; needs OPENAI_API_KEY.
- mock          : deterministic canned responses so the full loop can be
                  exercised and tested with zero LLM calls.

Select explicitly with FORUM_BACKEND=claude-cli|anthropic-api|openai-api|mock,
or auto-detect (anthropic key -> openai key -> claude CLI -> mock).
Model override: FORUM_MODEL
(defaults: CLI "sonnet", Anthropic "claude-opus-4-8", OpenAI "gpt-5-mini").
"""

import json
import os
import re
import shutil
import subprocess
from typing import Any


class LLMError(RuntimeError):
    pass


def extract_json(text: str) -> Any:
    """Parse JSON out of a model response, tolerating fences and preambles."""
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    fenced = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    if fenced:
        try:
            return json.loads(fenced.group(1).strip())
        except json.JSONDecodeError:
            pass
    for open_ch, close_ch in (("{", "}"), ("[", "]")):
        start = text.find(open_ch)
        end = text.rfind(close_ch)
        if start != -1 and end > start:
            try:
                return json.loads(text[start : end + 1])
            except json.JSONDecodeError:
                continue
    raise LLMError(f"Could not parse JSON from response: {text[:300]}")


class ClaudeCLIBackend:
    """Calls the `claude` CLI in headless print mode."""

    name = "claude-cli"

    def __init__(self, model: str | None = None):
        self.model = model or os.environ.get("FORUM_MODEL", "sonnet")

    def complete_json(self, task: str, prompt: str, context: dict) -> Any:
        env = {
            k: v
            for k, v in os.environ.items()
            # A parent Claude Code session exports these; they point the CLI
            # at a session-scoped proxy that rejects nested calls.
            if k not in ("ANTHROPIC_BASE_URL", "CLAUDECODE", "CLAUDE_CODE_ENTRYPOINT")
        }
        cmd = ["claude", "-p", prompt, "--output-format", "json", "--model", self.model]
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=600, env=env)
        if proc.returncode != 0:
            raise LLMError(f"claude CLI failed ({task}): {proc.stderr[:500] or proc.stdout[:500]}")
        envelope = json.loads(proc.stdout)
        if envelope.get("is_error"):
            raise LLMError(f"claude CLI error ({task}): {envelope.get('result', '')[:500]}")
        return extract_json(envelope["result"])


class AnthropicAPIBackend:
    """Calls the Anthropic API directly (requires ANTHROPIC_API_KEY)."""

    name = "anthropic-api"

    def __init__(self, model: str | None = None):
        import anthropic  # deferred so the demo runs without the package

        self.client = anthropic.Anthropic()
        self.model = model or os.environ.get("FORUM_MODEL", "claude-opus-4-8")

    def complete_json(self, task: str, prompt: str, context: dict) -> Any:
        with self.client.messages.stream(
            model=self.model,
            max_tokens=16000,
            thinking={"type": "adaptive"},
            messages=[{"role": "user", "content": prompt}],
        ) as stream:
            message = stream.get_final_message()
        if message.stop_reason == "refusal":
            raise LLMError(f"model refused request ({task})")
        text = next(b.text for b in message.content if b.type == "text")
        return extract_json(text)


class OpenAIBackend:
    """Calls the OpenAI API (requires OPENAI_API_KEY)."""

    name = "openai-api"

    def __init__(self, model: str | None = None):
        from openai import OpenAI  # deferred so the demo runs without the package

        self.client = OpenAI()
        self.model = model or os.environ.get("FORUM_MODEL", "gpt-5-mini")

    def complete_json(self, task: str, prompt: str, context: dict) -> Any:
        from openai import OpenAIError

        try:
            resp = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
            )
        except OpenAIError as e:
            raise LLMError(f"OpenAI API failed ({task}): {e}") from e
        text = resp.choices[0].message.content
        if not text:
            raise LLMError(f"OpenAI returned empty content ({task}), finish_reason="
                           f"{resp.choices[0].finish_reason}")
        return extract_json(text)


class MockBackend:
    """Deterministic responses shaped like real ones. Approval rises across
    rounds so a full run demonstrates critique -> revision -> consensus."""

    name = "mock"

    def complete_json(self, task: str, prompt: str, context: dict) -> Any:
        from . import mockdata

        return mockdata.respond(task, context)


def make_backend():
    choice = os.environ.get("FORUM_BACKEND", "").strip().lower()
    if choice == "mock":
        return MockBackend()
    if choice == "anthropic-api":
        return AnthropicAPIBackend()
    if choice == "openai-api":
        return OpenAIBackend()
    if choice == "claude-cli":
        return ClaudeCLIBackend()
    if choice:
        raise LLMError(f"Unknown FORUM_BACKEND: {choice}")
    if os.environ.get("ANTHROPIC_API_KEY"):
        return AnthropicAPIBackend()
    if os.environ.get("OPENAI_API_KEY"):
        return OpenAIBackend()
    if shutil.which("claude"):
        return ClaudeCLIBackend()
    return MockBackend()

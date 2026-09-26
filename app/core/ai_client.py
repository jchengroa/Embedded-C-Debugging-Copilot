"""
app/core/ai_client.py

AI integration layer — wraps OpenAI-compatible API calls.

Designed so that:
  - The debugging engine calls high-level methods here.
  - All provider/key configuration is external (env var or config file).
  - If the AI backend is unavailable, every method returns a graceful fallback.
  - The engine never fabricates results; it clearly marks AI responses as INFERRED.
"""
from __future__ import annotations

import json
import os
import re
import textwrap
from typing import Optional

from app.models.investigation import (
    EvidenceItem, EvidenceKind, Hypothesis, RootCause, ProposedFix, FileDiff,
)
from app.models.project import Project


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

def _get_config() -> dict:
    """Read config from environment or config/config.json."""
    cfg: dict = {
        "api_key":   os.environ.get("OPENAI_API_KEY", ""),
        "base_url":  os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1"),
        "model":     os.environ.get("OPENAI_MODEL", "gpt-4o"),
        "max_tokens": int(os.environ.get("MAX_TOKENS", "4096")),
    }
    config_path = os.path.join(os.path.dirname(__file__), "..", "..", "config", "settings.json")
    if os.path.exists(config_path):
        try:
            with open(config_path) as f:
                file_cfg = json.load(f)
            cfg.update({k: v for k, v in file_cfg.items() if v})
        except Exception:
            pass
    return cfg


def is_available() -> bool:
    """Return True if an API key is configured."""
    return bool(_get_config().get("api_key"))


# ---------------------------------------------------------------------------
# Low-level client helper
# ---------------------------------------------------------------------------

def _chat(system_prompt: str, user_prompt: str, max_tokens: Optional[int] = None) -> Optional[str]:
    """
    Call the OpenAI-compatible chat endpoint.
    Returns the response text or None on any failure.
    """
    cfg = _get_config()
    if not cfg.get("api_key"):
        return None

    try:
        from openai import OpenAI
        client = OpenAI(api_key=cfg["api_key"], base_url=cfg["base_url"])
        response = client.chat.completions.create(
            model=cfg["model"],
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": user_prompt},
            ],
            max_tokens=max_tokens or cfg["max_tokens"],
            temperature=0.2,
        )
        return response.choices[0].message.content
    except Exception as exc:
        return f"__AI_ERROR__: {exc}"


# ---------------------------------------------------------------------------
# System prompt (embedded debugging methodology)
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = """\
You are an expert embedded systems debugging assistant.

Your role is to reason methodically about embedded C/C++ firmware bugs by
connecting observed hardware/software symptoms to root causes.

Rules:
- Never fabricate hardware measurements, test results, or compilation output.
- Clearly label each claim as OBSERVED, INFERRED, ASSUMED, or UNVERIFIED.
- Only recommend the minimal fix needed to address the identified root cause.
- Do not rewrite unrelated code.
- Reason about ISR/main concurrency, volatile, atomicity, peripheral timing,
  debounce, communication protocols, register configuration, and memory
  safety — but only introduce these concepts when relevant.
- When evidence is insufficient, state what additional information is needed.
- Respond in structured JSON where requested.
"""


# ---------------------------------------------------------------------------
# High-level AI calls
# ---------------------------------------------------------------------------

def generate_hypotheses(
    project: Project,
    symptom_desc: str,
    expected: str,
    actual: str,
    static_evidence: list[str],
    system_model: str,
) -> list[Hypothesis]:
    """
    Ask the AI to generate/refine hypotheses given the symptom and static analysis.
    Returns a list of Hypothesis objects (kind=INFERRED).
    Falls back to empty list if AI is unavailable.
    """
    source_summary = _build_source_summary(project)

    prompt = textwrap.dedent(f"""
    ## Project
    Platform: {project.detected_platform or 'Unknown'}
    Build system: {project.detected_build_system or 'Unknown'}

    ## System model
    {system_model}

    ## Symptom
    Description: {symptom_desc}
    Expected: {expected}
    Actual: {actual}

    ## Static analysis findings
    {chr(10).join("- " + e for e in static_evidence[:20])}

    ## Source file summary
    {source_summary}

    ## Task
    Generate a ranked list of hypotheses (max 5) for the root cause.
    Respond with JSON array:
    [
      {{
        "title": "...",
        "description": "...",
        "evidence_for": ["..."],
        "evidence_against": ["..."],
        "confidence": 0.0-1.0,
        "verification_method": "..."
      }},
      ...
    ]
    Only JSON, no extra text.
    """).strip()

    raw = _chat(_SYSTEM_PROMPT, prompt, max_tokens=2048)
    if not raw or raw.startswith("__AI_ERROR__"):
        return []

    try:
        data = json.loads(_extract_json(raw))
        hypotheses = []
        for item in data[:5]:
            h = Hypothesis(
                title=item.get("title", ""),
                description=item.get("description", ""),
                evidence_for=item.get("evidence_for", []),
                evidence_against=item.get("evidence_against", []),
                confidence=float(item.get("confidence", 0.5)),
                verification_method=item.get("verification_method", ""),
            )
            hypotheses.append(h)
        return hypotheses
    except Exception:
        return []


def generate_root_cause(
    project: Project,
    symptom_desc: str,
    expected: str,
    actual: str,
    hypotheses: list[Hypothesis],
    evidence_items: list[str],
) -> Optional[RootCause]:
    """
    Ask the AI to produce a root cause statement given confirmed hypotheses.
    """
    h_text = "\n".join(
        f"H{i+1} ({h.confidence_pct()}%): {h.title}\n  {h.description}"
        for i, h in enumerate(hypotheses[:3])
    )

    source_summary = _build_source_summary(project)

    prompt = textwrap.dedent(f"""
    ## Symptom
    {symptom_desc}
    Expected: {expected}
    Actual: {actual}

    ## Top Hypotheses
    {h_text}

    ## Evidence
    {chr(10).join("- " + e for e in evidence_items[:15])}

    ## Source summary
    {source_summary}

    ## Task
    Identify the most likely root cause.
    Respond with JSON:
    {{
      "summary": "one-sentence root cause",
      "mechanism": "step-by-step description referencing file/line when possible",
      "evidence": ["bullet 1", "bullet 2", ...]
    }}
    Only JSON.
    """).strip()

    raw = _chat(_SYSTEM_PROMPT, prompt, max_tokens=1024)
    if not raw or raw.startswith("__AI_ERROR__"):
        return None

    try:
        data = json.loads(_extract_json(raw))
        return RootCause(
            summary=data.get("summary", ""),
            mechanism=data.get("mechanism", ""),
            evidence=data.get("evidence", []),
        )
    except Exception:
        return None


def generate_fix(
    project: Project,
    root_cause: RootCause,
) -> Optional[ProposedFix]:
    """
    Ask the AI to produce a minimal fix for the identified root cause.
    """
    source_texts = []
    for pf in (project.source_files + project.header_files)[:8]:
        content = pf.load_content()
        if content.strip():
            source_texts.append(f"### {pf.rel_path}\n```c\n{content[:3000]}\n```")

    source_block = "\n\n".join(source_texts)

    prompt = textwrap.dedent(f"""
    ## Root cause
    {root_cause.summary}

    Mechanism: {root_cause.mechanism}

    Evidence:
    {chr(10).join("- " + e for e in root_cause.evidence)}

    ## Source files
    {source_block}

    ## Task
    Provide the minimal fix. For each file that needs changes respond with JSON:
    {{
      "summary": "one-sentence fix description",
      "explanation": "why this fixes the root cause",
      "side_effects": "potential side effects or empty string",
      "diffs": [
        {{
          "file": "relative/path.c",
          "before": "exact original code block",
          "after": "corrected code block",
          "explanation": "what changed and why"
        }}
      ]
    }}
    Only JSON.
    """).strip()

    raw = _chat(_SYSTEM_PROMPT, prompt, max_tokens=2048)
    if not raw or raw.startswith("__AI_ERROR__"):
        return None

    try:
        data = json.loads(_extract_json(raw))
        diffs = [
            FileDiff(
                file=d.get("file", ""),
                before=d.get("before", ""),
                after=d.get("after", ""),
                explanation=d.get("explanation", ""),
            )
            for d in data.get("diffs", [])
        ]
        return ProposedFix(
            summary=data.get("summary", ""),
            explanation=data.get("explanation", ""),
            side_effects=data.get("side_effects", ""),
            diffs=diffs,
        )
    except Exception:
        return None


def generate_regression_test(
    root_cause: RootCause,
    symptom_desc: str,
    project: Project,
) -> Optional[str]:
    """
    Ask AI to generate a regression test for the fixed bug.
    Returns source code as a string or None.
    """
    prompt = textwrap.dedent(f"""
    ## Root cause
    {root_cause.summary}

    ## Original symptom
    {symptom_desc}

    ## Project platform
    {project.detected_platform or 'Unknown'}

    ## Task
    Write a minimal unit test (C or Python, choose the most appropriate) that:
    1. Would FAIL before the fix.
    2. Passes after the fix is applied.
    3. Focuses specifically on the root cause.

    Return only the test source code with a comment explaining what it verifies.
    """).strip()

    return _chat(_SYSTEM_PROMPT, prompt, max_tokens=1024)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_source_summary(project: Project) -> str:
    """Return a compact summary of source files for prompt injection."""
    lines = []
    for pf in (project.source_files + project.header_files)[:6]:
        content = pf.load_content()
        preview = content[:600].replace("\n", " ")
        lines.append(f"{pf.rel_path}: {preview}")
    return "\n".join(lines)


def _extract_json(text: str) -> str:
    """Extract the first JSON object or array from a string."""
    text = text.strip()
    # Remove markdown code fences
    text = re.sub(r"```(?:json)?\s*", "", text)
    text = re.sub(r"```", "", text)
    # Find first { or [
    for start_char, end_char in [('{', '}'), ('[', ']')]:
        idx = text.find(start_char)
        if idx >= 0:
            # Find matching close
            depth = 0
            in_str = False
            escape = False
            for i, ch in enumerate(text[idx:], start=idx):
                if escape:
                    escape = False
                    continue
                if ch == "\\" and in_str:
                    escape = True
                    continue
                if ch == '"' and not escape:
                    in_str = not in_str
                    continue
                if not in_str:
                    if ch == start_char:
                        depth += 1
                    elif ch == end_char:
                        depth -= 1
                        if depth == 0:
                            return text[idx:i+1]
    return text

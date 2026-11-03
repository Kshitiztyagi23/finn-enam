"""Gemini wrapper for FINN.

Design notes
------------
- Precompute-first. Every LLM call is cached under ``.cache/llm/`` keyed by a
  SHA-256 of (model, prompt, pdf bytes). The deployed app reads cached JSON;
  it never calls Gemini at runtime.
- Structured output. The caller passes a Pydantic / dict JSON schema and we
  set ``response_mime_type='application/json'`` and ``response_schema``.
- Honest failure. If the model returns malformed JSON after retries, we return
  ``None`` rather than guess. Callers must handle ``None``.
- Token / call counter. A process-level counter lets ``build_evidence.py``
  print a cost summary.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from google import genai
from google.genai import types

ROOT = Path(__file__).resolve().parents[1]
CACHE_DIR = ROOT / ".cache" / "llm"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

load_dotenv(ROOT / ".env")

# Usage counters surfaced to the user via build_evidence.py and the footer.
USAGE: dict[str, int] = {"calls": 0, "cache_hits": 0, "input_tokens": 0, "output_tokens": 0}

_client: genai.Client | None = None


def client() -> genai.Client:
    global _client
    if _client is None:
        key = os.environ.get("GEMINI_API_KEY")
        if not key:
            raise RuntimeError("GEMINI_API_KEY missing. Add it to .env at the project root.")
        _client = genai.Client(api_key=key)
    return _client


def _cache_key(model: str, prompt: str, pdf_bytes: bytes | None, schema: dict | None) -> str:
    h = hashlib.sha256()
    h.update(model.encode())
    h.update(b"\x00")
    h.update(prompt.encode())
    h.update(b"\x00")
    if pdf_bytes is not None:
        h.update(hashlib.sha256(pdf_bytes).digest())
    if schema is not None:
        h.update(json.dumps(schema, sort_keys=True).encode())
    return h.hexdigest()


# Fallback chain: newest first, drop to older stable models on 404 / 503.
MODEL_CHAIN = (
    "gemini-3.5-flash",         # Primary. 3.8-flash is 503-ing persistently on 3 Nov 2026.
    "gemini-flash-latest",      # Alias — follows whichever stable Flash is current.
    "gemini-3.5-flash-lite",    # Lighter variant, usually has more headroom.
    "gemini-flash-lite-latest",
    "gemini-3.8-flash",         # Keep as fallback in case 3.5 is retired.
    "gemini-pro-latest",        # Last resort, slower + pricier but almost never 503s.
)


def extract_json(
    prompt: str,
    *,
    pdf_bytes: bytes | None = None,
    schema: dict | None = None,
    model: str | None = None,
    temperature: float = 0.0,
    retries: int = 2,
    use_cache: bool = True,
) -> Any | None:
    """Call Gemini and return parsed JSON, or ``None`` if parsing fails.

    ``schema`` is a JSON-schema dict for structured output. If ``model`` is
    None, we try each model in ``MODEL_CHAIN`` until one responds. 404 (model
    removed) and 503 (overloaded) advance to the next model; other errors
    retry on the same model.
    """

    chain = [model] if model else list(MODEL_CHAIN)
    key = _cache_key("|".join(chain), prompt, pdf_bytes, schema)
    cache_path = CACHE_DIR / f"{key}.json"
    if use_cache and cache_path.exists():
        USAGE["cache_hits"] += 1
        return json.loads(cache_path.read_text(encoding="utf-8"))

    parts: list[Any] = [prompt]
    if pdf_bytes is not None:
        parts.insert(0, types.Part.from_bytes(data=pdf_bytes, mime_type="application/pdf"))

    config = types.GenerateContentConfig(temperature=temperature)
    if schema is not None:
        config.response_mime_type = "application/json"
        config.response_schema = schema

    last_err: Exception | None = None
    for current_model in chain:
        for attempt in range(retries + 1):
            try:
                response = client().models.generate_content(model=current_model, contents=parts, config=config)
                USAGE["calls"] += 1
                if hasattr(response, "usage_metadata") and response.usage_metadata is not None:
                    USAGE["input_tokens"] += getattr(response.usage_metadata, "prompt_token_count", 0) or 0
                    USAGE["output_tokens"] += getattr(response.usage_metadata, "candidates_token_count", 0) or 0
                text = response.text or ""
                try:
                    parsed = json.loads(text)
                except json.JSONDecodeError:
                    stripped = text.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
                    parsed = json.loads(stripped)
                cache_path.write_text(json.dumps(parsed, ensure_ascii=False, indent=2), encoding="utf-8")
                return parsed
            except Exception as exc:
                last_err = exc
                msg = str(exc)
                print(f"gemini {current_model} attempt {attempt + 1}: {msg[:120]}", file=sys.stderr)
                # 404 (removed) or persistent 503 (overloaded) → next model in chain.
                if "404" in msg or ("503" in msg and attempt == retries):
                    break
                time.sleep(1.5 * (attempt + 1))
    print(f"gemini gave up across {len(chain)} models: {last_err}", file=sys.stderr)
    return None


def usage_summary() -> str:
    return (
        f"{USAGE['calls']} Gemini calls · {USAGE['cache_hits']} cached · "
        f"{USAGE['input_tokens']:,} in / {USAGE['output_tokens']:,} out tokens"
    )

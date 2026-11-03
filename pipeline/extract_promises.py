"""Promise Tracker: match forward statements from a prior earnings call to
actuals in a later company filing. Both PDFs go into one Gemini call so
matching happens with primary sources in hand.

Verdict rules (deterministic, applied by the model under instruction):
  delivered: actual meets or beats the stated target / lower bound of band
  partial:   actual is within 20% below the lower bound
  missed:    actual is more than 20% below the lower bound
  pending:   metric / period / basis in later filing is NOT directly comparable

If no promise can be matched honestly, the model returns [] — never guesses.
"""

from __future__ import annotations

from google.genai import types

from pipeline.llm import extract_json, client, USAGE, MODEL_CHAIN
import json
import sys
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CACHE_DIR = ROOT / ".cache" / "llm"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

PROMPT = """You are reconciling management's prior guidance with the company's later disclosure.

INPUTS: two PDFs. The FIRST is an earlier earnings-call transcript. The SECOND is a later company filing (results outcome / press release / investor presentation).

TASK: find up to 3 strongly-quantified forward statements the management made in the transcript that are now verifiable against the later filing. Return a JSON list.

For each:
- `statement`: the sentence VERBATIM from the transcript. Keep management's exact words.
- `statement_page`: page in the TRANSCRIPT (PDF 1).
- `metric`: what was promised, in plain English (e.g. 'constant-currency revenue growth', 'EBITDA margin', 'Jio ARPU', 'store count').
- `period`: the period management referred to (e.g. 'Q2 FY27', 'FY27 full year', 'next quarter').
- `target`: the target value or band as management stated it (e.g. '15-17%', '≥ 25%', '₹5,500-6,000 cr').
- `actual`: the actual value in the LATER filing (PDF 2). If no comparable number exists, leave empty.
- `actual_page`: page in the LATER filing where you read `actual`. 0 if not found.
- `verdict`: ONE OF 'delivered' | 'partial' | 'missed' | 'pending'. Rules:
    delivered — actual meets or beats the stated target (or the lower bound of a band).
    partial   — actual is below the lower bound by less than 20%.
    missed    — actual is below the lower bound by 20% or more.
    pending   — the later filing does not report the SAME metric for the SAME period on the SAME basis. If the segment, basis or period differs, use pending.
- `reasoning`: one short sentence explaining the verdict (e.g. 'actual 16.3% CC growth sits in the 15-17% guided band').

CRITICAL:
- Never claim an actual that isn't on a specific page of PDF 2.
- Never classify as delivered/partial/missed if the metric/period/basis is not an exact match. Use pending.
- Never invent a quote. If you can't find a strong forward statement, return [].
- Do not use outside knowledge. Both documents are self-contained.

Return only the JSON list. No prose, no code fences.
"""

PROMISES_SCHEMA = {
    "type": "array",
    "items": {
        "type": "object",
        "properties": {
            "statement": {"type": "string"},
            "statement_page": {"type": "integer"},
            "metric": {"type": "string"},
            "period": {"type": "string"},
            "target": {"type": "string"},
            "actual": {"type": "string"},
            "actual_page": {"type": "integer"},
            "verdict": {"type": "string", "enum": ["delivered", "partial", "missed", "pending"]},
            "reasoning": {"type": "string"},
        },
        "required": ["statement", "statement_page", "metric", "period", "target", "verdict", "reasoning"],
    },
}


def match(transcript_pdf: bytes, later_pdf: bytes) -> list[dict] | None:
    """Return the promise list, or None if the LLM call fully failed."""
    # Dual-PDF call needs the raw client because our wrapper hashes a single pdf.
    key = hashlib.sha256(b"promises:" + hashlib.sha256(transcript_pdf).digest() + hashlib.sha256(later_pdf).digest()).hexdigest()
    cache_path = CACHE_DIR / f"promises_{key}.json"
    if cache_path.exists():
        USAGE["cache_hits"] += 1
        return json.loads(cache_path.read_text(encoding="utf-8"))

    parts = [
        types.Part.from_bytes(data=transcript_pdf, mime_type="application/pdf"),
        types.Part.from_bytes(data=later_pdf, mime_type="application/pdf"),
        PROMPT,
    ]
    config = types.GenerateContentConfig(
        temperature=0.0,
        response_mime_type="application/json",
        response_schema=PROMISES_SCHEMA,
    )
    import time
    for sweep in range(3):  # three full sweeps across the model chain
        for model in MODEL_CHAIN:
            try:
                response = client().models.generate_content(model=model, contents=parts, config=config)
                USAGE["calls"] += 1
                if hasattr(response, "usage_metadata") and response.usage_metadata is not None:
                    USAGE["input_tokens"] += getattr(response.usage_metadata, "prompt_token_count", 0) or 0
                    USAGE["output_tokens"] += getattr(response.usage_metadata, "candidates_token_count", 0) or 0
                text = (response.text or "").strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
                parsed = json.loads(text)
                if not isinstance(parsed, list):
                    raise ValueError("expected a JSON list")
                cache_path.write_text(json.dumps(parsed, ensure_ascii=False, indent=2), encoding="utf-8")
                return parsed
            except Exception as exc:
                print(f"promises sweep {sweep + 1} {model}: {str(exc)[:120]}", file=sys.stderr)
                if "404" in str(exc) or "503" in str(exc):
                    continue
                return None  # non-transient error
        if sweep < 2:
            print(f"all models busy; backing off {10 * (sweep + 1)}s", file=sys.stderr)
            time.sleep(10 * (sweep + 1))
    return None

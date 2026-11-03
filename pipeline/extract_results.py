"""Extract a 4-metric results grid from an NSE/BSE Outcome PDF with Gemini.

Returns the ``results`` sub-dict used by data/evidence/{SYMBOL}.json.
Deterministic sanity checks run before the grid is returned; a failure drops
the whole grid rather than publish a wrong number.
"""

from __future__ import annotations

import re
from typing import Any

from pipeline.llm import extract_json

RESULTS_SCHEMA = {
    "type": "object",
    "properties": {
        "period": {"type": "string", "description": "e.g. 'Q2 FY27 · quarter ended 30 Sep 2026'"},
        "unit": {"type": "string", "description": "Must be '₹ crore'. Convert if the filing uses lakhs or millions."},
        "basis": {"type": "string", "description": "e.g. 'Consolidated, reported'."},
        "rows": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "label": {"type": "string", "enum": ["Revenue", "EBITDA", "PBT", "PAT"]},
                    "current": {"type": "number", "nullable": True},
                    "previous": {"type": "number", "nullable": True, "description": "QoQ previous quarter"},
                    "year_ago": {"type": "number", "nullable": True, "description": "YoY same quarter last year"},
                    "page": {"type": "integer", "description": "Page number in the PDF where this row was found"},
                },
                "required": ["label", "page"],
            },
        },
        "insight": {"type": "string", "description": "One sentence summarising the QoQ / YoY move. No speculation."},
        "notes": {"type": "string", "description": "Any derivation note (eg EBITDA computed from half-year less current quarter)."},
    },
    "required": ["period", "unit", "basis", "rows"],
}

PROMPT = """You are extracting a results grid from a listed Indian company's exchange filing.

Read ONLY the attached PDF. Do not use outside knowledge.

Return JSON with four rows: Revenue, EBITDA, PBT, PAT. For each row:
  current   = this reporting quarter's value
  previous  = the immediately previous quarter's value (QoQ)
  year_ago  = the same quarter last fiscal year's value (YoY)
  page      = PDF page number (1-indexed) where you read the row

Rules:
- Values in ₹ crore. If the filing uses lakhs, divide by 100. If millions, divide by 10. If the filing is already in crore, use as-is.
- Prefer CONSOLIDATED figures over standalone when both exist. State the choice in `basis`.
- EBITDA: use the row literally labelled EBITDA. If the filing only publishes 'Operating Profit' or 'Profit from operations', use that and mention it in `notes`.
- PBT = Profit Before Tax (sometimes 'Profit before exceptional items and tax' — note the choice).
- PAT = Total consolidated 'Profit for the period' / 'Net profit' AFTER tax but BEFORE the split between owners of the parent and non-controlling interest. If the filing only reports PAT split as 'attributable to owners' and 'attributable to NCI', ADD them together for PAT and state this in `notes`.
- If a cell is genuinely not disclosed in this PDF, return `null` for that cell. NEVER guess.
- `period` must be in the form 'Q<n> FY<yy> · quarter ended <DD Mon YYYY>'.
- `insight` is one short sentence (<= 180 chars) comparing the current quarter to QoQ and YoY. No forward-looking language.

Return only the JSON. No prose, no code fences.
"""


def _finite(x: Any) -> bool:
    return isinstance(x, (int, float)) and not (isinstance(x, bool))


def sanity_check(grid: dict) -> tuple[bool, str]:
    """Reject obviously wrong grids before we publish them."""
    if not grid or not isinstance(grid.get("rows"), list):
        return False, "no rows"
    if "crore" not in (grid.get("unit") or "").lower():
        return False, f"unit not crore: {grid.get('unit')!r}"
    labels = [row.get("label") for row in grid["rows"]]
    for required in ("Revenue", "EBITDA", "PBT", "PAT"):
        if required not in labels:
            return False, f"missing row: {required}"
    by_label = {row["label"]: row for row in grid["rows"]}
    revenue = by_label["Revenue"].get("current")
    pat = by_label["PAT"].get("current")
    pbt = by_label["PBT"].get("current")
    if _finite(revenue) and revenue <= 0:
        return False, "revenue <= 0"
    if _finite(pat) and _finite(pbt) and pbt < pat - abs(pat) * 0.05:
        # PAT should not exceed PBT by more than rounding noise.
        return False, f"PBT {pbt} < PAT {pat}"
    # Sanity on magnitude: QoQ and YoY within 10x. Guards against unit confusion.
    for row in grid["rows"]:
        cur = row.get("current")
        for other_key in ("previous", "year_ago"):
            other = row.get(other_key)
            if _finite(cur) and _finite(other) and other != 0:
                ratio = abs(cur / other)
                if ratio > 10 or ratio < 0.1:
                    return False, f"{row['label']} {other_key} ratio {ratio:.1f}x — probable unit error"
    return True, "ok"


def extract(pdf_bytes: bytes) -> dict | None:
    grid = extract_json(PROMPT, pdf_bytes=pdf_bytes, schema=RESULTS_SCHEMA)
    if grid is None:
        return None
    ok, reason = sanity_check(grid)
    if not ok:
        print(f"sanity check failed: {reason}")
        return None
    # Normalise unit label for display.
    grid["unit"] = re.sub(r"\s+", " ", grid["unit"]).strip() or "₹ crore"
    return grid

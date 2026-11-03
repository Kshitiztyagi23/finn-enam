"""Extract an appointment / resignation card from an exchange filing.

SEBI LODR Regulation 30 requires the filing to carry a brief profile of the
incoming person; we lift it verbatim from the attached PDF rather than invent
or web-search a bio.
"""

from __future__ import annotations

from pipeline.llm import extract_json

PEOPLE_SCHEMA = {
    "type": "object",
    "properties": {
        "events": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "role": {"type": "string", "description": "e.g. CFO, Independent Director, Managing Director"},
                    "change": {"type": "string", "enum": ["appointed", "resigned", "retired", "re-appointed", "cessation", "other"]},
                    "effective": {"type": "string", "description": "Effective date as stated in the filing (free text)."},
                    "term": {"type": "string", "description": "Length of term if stated, e.g. '5 years'. Empty if not."},
                    "bio": {"type": "string", "description": "A 2-3 sentence profile taken from the filing's 'brief profile' section. Use the filing's own words where possible. Do NOT add anything not in the PDF."},
                    "page": {"type": "integer", "description": "PDF page where the brief profile sits"},
                },
                "required": ["name", "role", "change", "page"],
            },
        }
    },
    "required": ["events"],
}

PROMPT = """You are reading a SEBI LODR Regulation 30 filing about a change in management.

Return every appointment / resignation / retirement / cessation disclosed in this PDF.

For each person:
- `name`: full name as spelled in the filing.
- `role`: the position (CFO, Managing Director, Independent Director, etc.).
- `change`: one of appointed / resigned / retired / re-appointed / cessation / other.
- `effective`: the effective date stated in the filing (free text, as written).
- `term`: term length only if stated (e.g. '5 years from 30 Oct 2026'). Empty string if not stated.
- `bio`: for an appointment, lift 2-3 sentences from the filing's 'brief profile' / 'brief resume' section. Use the filing's own words. Do NOT add outside knowledge. For a resignation/retirement, leave empty.
- `page`: PDF page number where you read this.

If a person's bio is not disclosed in the PDF, leave `bio` empty — never guess.

Return only the JSON. No prose, no code fences.
"""


def extract(pdf_bytes: bytes) -> dict | None:
    out = extract_json(PROMPT, pdf_bytes=pdf_bytes, schema=PEOPLE_SCHEMA)
    if not out or not isinstance(out.get("events"), list):
        return None
    # Reject if every event is blank — probably the model misread the filing.
    good = [e for e in out["events"] if e.get("name") and e.get("role")]
    if not good:
        return None
    return {"events": good}

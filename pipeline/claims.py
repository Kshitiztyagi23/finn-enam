"""Extract page-linked quantitative guidance candidates from public transcripts.

This deliberately does not label statements delivered or missed: that requires
matching the correct metric, business segment, and time period to a later filing.
"""

from __future__ import annotations

import io
import re
import sys
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VENDOR = ROOT / ".vendor"
if VENDOR.exists():
    sys.path.insert(0, str(VENDOR))

import httpx  # noqa: E402
from pypdf import PdfReader  # noqa: E402

FORWARD = re.compile(r"\b(expect|target|guidance|aim|plan|forecast|project|anticipate|intend)\b", re.I)
QUANTITY = re.compile(r"(?:\d+(?:\.\d+)?\s*(?:%|per cent|percent|crore|cr\b|billion|million|bps))", re.I)
BUSINESS_METRIC = re.compile(r"\b(revenue|sales|ebitda|margin|profit|growth|capex|capacity|volume|customers|stores|outlets|market share)\b", re.I)
MANAGEMENT_VOICE = re.compile(r"\b(we|our|us)\b", re.I)


def extract_from_pdf(url: str, title: str, limit: int = 5) -> list[dict]:
    response = httpx.get(url, timeout=25, follow_redirects=True, headers={"User-Agent": "Mozilla/5.0"})
    response.raise_for_status()
    if len(response.content) > 12_000_000 or not response.content.startswith(b"%PDF"):
        return []
    reader = PdfReader(io.BytesIO(response.content))
    candidates = []
    for page_number, page in enumerate(reader.pages[:45], start=1):
        raw = page.extract_text() or ""
        normalized = " ".join(raw.replace("\x00", " ").split())
        for sentence in re.split(r"(?<=[.!?])\s+(?=[A-Z])", normalized):
            sentence = sentence.strip(" -•\t")
            if not (55 <= len(sentence) <= 390 and FORWARD.search(sentence) and QUANTITY.search(sentence) and BUSINESS_METRIC.search(sentence) and MANAGEMENT_VOICE.search(sentence)):
                continue
            if sentence.endswith("?") or re.match(r"^[A-Z][a-z]+(?: [A-Z][a-z]+){0,3}:", sentence) or any(x in sentence.lower() for x in ("copyright", "projection of iea", "analyst estimate", "i will not")):
                continue
            strength = 2 if re.search(r"\b(target|guidance|expect|aim)\b", sentence, re.I) else 1
            candidates.append((strength, {"quote": sentence, "page": page_number, "document": title, "source_url": url}))
    candidates.sort(key=lambda pair: pair[0], reverse=True)
    seen, unique = set(), []
    for _, item in candidates:
        key = re.sub(r"\W", "", item["quote"].lower())[:100]
        if key not in seen:
            seen.add(key)
            unique.append(item)
        if len(unique) >= limit:
            break
    return unique


@lru_cache(maxsize=64)
def claims_for(symbol: str, transcripts: tuple[tuple[str, str], ...]) -> list[dict]:
    claims = []
    for index, (title, url) in enumerate(transcripts[:4], start=1):
        try:
            display_title = title[:65].rstrip() + ("…" if len(title) > 65 else "") if title.lower() != "transcript" else f"Transcript {index}"
            claims.extend(extract_from_pdf(url, display_title, limit=3))
        except Exception as exc:
            print(f"claims {symbol} / {index}: {exc}", file=sys.stderr)
    return claims[:8]

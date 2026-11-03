"""Attach a 'promise' list to each ticker's evidence JSON.

For each ticker: pick the previous-quarter transcript (what management said) and
the latest Outcome / results PDF (what they later delivered). Pass both to
``extract_promises.match``. Write the result back into
``data/evidence/{SYMBOL}.json`` so the UI can render a Promise Tracker beside
the results grid.
"""

from __future__ import annotations

import argparse
import io
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import httpx  # noqa: E402
from pypdf import PdfReader, PdfWriter  # noqa: E402

from pipeline import extract_promises  # noqa: E402
from pipeline.llm import usage_summary  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_DIR = ROOT / "data" / "evidence"
HEADERS = {"User-Agent": "Mozilla/5.0 (FINN prototype)"}


def download(url: str, pages: int = 15) -> bytes:
    """Fetch a PDF and keep only the first N pages. Opening remarks + P&L live
    on the early pages, keeps the dual-PDF upload light enough for Gemini."""
    with httpx.Client(timeout=35, follow_redirects=True, headers=HEADERS) as c:
        r = c.get(url)
        r.raise_for_status()
    data = r.content
    if not data.startswith(b"%PDF"):
        raise RuntimeError("not a PDF")
    try:
        reader = PdfReader(io.BytesIO(data))
        if len(reader.pages) > pages:
            writer = PdfWriter()
            for page in reader.pages[:pages]:
                writer.add_page(page)
            buf = io.BytesIO()
            writer.write(buf)
            data = buf.getvalue()
    except Exception as exc:
        print(f"  slice failed ({exc}); using original {len(data):,} bytes")
    return data


def prior_transcript_url(symbol: str) -> str | None:
    """Second-latest transcript on screener = the quarter BEFORE the latest results."""
    research_file = ROOT / "data" / "research" / f"{symbol}.json"
    if not research_file.exists():
        return None
    research = json.loads(research_file.read_text(encoding="utf-8"))
    transcripts = research.get("transcripts", [])
    # Position 1 = the quarter before the most recent (position 0 is often the current quarter).
    if len(transcripts) >= 2:
        return transcripts[1]["url"]
    if transcripts:
        return transcripts[0]["url"]
    return None


def later_filing_url(symbol: str) -> str | None:
    """The latest results Outcome PDF (preferred) or next investor-presentation
    URL from the digest, as a proxy for 'what the company later disclosed'."""
    digest_file = ROOT / "data" / "digest.json"
    if not digest_file.exists():
        return None
    filings = json.loads(digest_file.read_text(encoding="utf-8"))["filings"]
    hits = [f for f in filings if f["symbol"] == symbol and f["category"] == "results" and f["source_url"].lower().endswith(".pdf")]
    if hits:
        hits.sort(key=lambda f: f["published_at"], reverse=True)
        return hits[0]["source_url"]
    return None


def build_symbol(symbol: str) -> dict:
    evidence_file = EVIDENCE_DIR / f"{symbol}.json"
    evidence = json.loads(evidence_file.read_text(encoding="utf-8")) if evidence_file.exists() else {"symbol": symbol, "results": None, "people": [], "promise": []}

    transcript_url = prior_transcript_url(symbol)
    filing_url = later_filing_url(symbol)
    if not (transcript_url and filing_url):
        print(f"  skip — transcript={bool(transcript_url)} filing={bool(filing_url)}")
        return evidence

    print(f"  transcript: {transcript_url}")
    print(f"  later:      {filing_url}")

    try:
        t_bytes = download(transcript_url)
        f_bytes = download(filing_url)
    except Exception as exc:
        print(f"  download failed: {exc}")
        return evidence

    promises = extract_promises.match(t_bytes, f_bytes)
    if promises is None:
        print("  LLM match failed")
        return evidence

    # Attach source URLs with page anchors to each promise.
    for p in promises:
        p["statement_source"] = {
            "label": f"Prior earnings-call transcript · page {p.get('statement_page', 1)}",
            "url": f"{transcript_url}#page={p.get('statement_page', 1)}",
        }
        if p.get("actual") and p.get("actual_page"):
            p["actual_source"] = {
                "label": f"Latest results filing · page {p['actual_page']}",
                "url": f"{filing_url}#page={p['actual_page']}",
            }
    evidence["promise"] = promises
    evidence.setdefault("sources", {})["promise_transcript"] = transcript_url
    evidence["sources"]["promise_later"] = filing_url
    evidence_file.write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  wrote {len(promises)} promises")
    return evidence


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("symbols", nargs="*", default=["DIXON", "INFY", "RELIANCE"])
    args = parser.parse_args()
    for symbol in args.symbols:
        print(f"\n=== {symbol} ===")
        build_symbol(symbol.upper())
    print(f"\n{usage_summary()}")


if __name__ == "__main__":
    main()

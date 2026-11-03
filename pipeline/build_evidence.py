"""Build data/evidence/{SYMBOL}.json for a given list of tickers.

Driven by the current digest: for each ticker we find the most recent `results`
filing (and, optionally, the most recent `management_change` filing in the same
window), download the PDFs, mirror them to data/pdf-cache/, and run the
extractors.

Each result grid has to pass deterministic sanity checks before being written
(see pipeline.extract_results.sanity_check). An extractor returning None means
the ticker falls through to its existing document trail — never a wrong number.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import httpx  # noqa: E402
from pypdf import PdfReader, PdfWriter  # noqa: E402

from pipeline import extract_people, extract_results  # noqa: E402
from pipeline.llm import USAGE, usage_summary  # noqa: E402

PDF_SOFT_LIMIT = 15_000_000  # above this, keep first ~25 pages — the P&L lives early

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_DIR = ROOT / "data" / "evidence"
PDF_CACHE_DIR = ROOT / "data" / "pdf-cache"
PDF_CACHE_DIR.mkdir(parents=True, exist_ok=True)
EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)

HEADERS = {"User-Agent": "Mozilla/5.0 (FINN prototype; source-linked research)"}


def latest(filings: list[dict], symbol: str, category: str) -> dict | None:
    matches = [f for f in filings if f["symbol"] == symbol and f["category"] == category and f.get("source_url", "").lower().endswith(".pdf")]
    if not matches:
        return None
    matches.sort(key=lambda f: f["published_at"], reverse=True)
    return matches[0]


def mirror(url: str, label: str) -> tuple[bytes, Path | None, bytes]:
    """Download a PDF; mirror the full file but return a slim copy for the LLM.

    Returns ``(full_bytes, cache_path, llm_bytes)``. ``llm_bytes`` equals
    ``full_bytes`` for normal filings; for large ones we send only the first
    25 pages so Gemini accepts the upload. The mirrored file is still the
    full filing so investors clicking a page link see the real document.
    """
    with httpx.Client(timeout=35, follow_redirects=True, headers=HEADERS) as client:
        resp = client.get(url)
        resp.raise_for_status()
    data = resp.content
    if len(data) > 60_000_000 or not data.startswith(b"%PDF"):
        raise RuntimeError(f"{label}: not a PDF or too large ({len(data):,} bytes)")
    name = hashlib.sha256(data).hexdigest()[:16]
    filename = urlparse(url).path.split("/")[-1] or "filing.pdf"
    out_path = PDF_CACHE_DIR / f"{name}_{filename}"
    if not out_path.exists():
        out_path.write_bytes(data)

    llm_bytes = data
    if len(data) > PDF_SOFT_LIMIT:
        try:
            reader = PdfReader(io.BytesIO(data))
            writer = PdfWriter()
            for page in reader.pages[:25]:
                writer.add_page(page)
            buf = io.BytesIO()
            writer.write(buf)
            llm_bytes = buf.getvalue()
            print(f"{label}: sliced {len(data):,} -> {len(llm_bytes):,} bytes (first 25 pages) for LLM upload")
        except Exception as exc:
            print(f"{label}: slicing failed ({exc}); sending full {len(data):,} bytes")
    return data, out_path, llm_bytes


def build_symbol(symbol: str, filings: list[dict], write: bool = True) -> dict:
    report: dict[str, Any] = {"symbol": symbol, "results": None, "people": [], "promise": [], "sources": {}}

    results_filing = latest(filings, symbol, "results")
    if results_filing:
        try:
            _, cached_path, llm_bytes = mirror(results_filing["source_url"], f"{symbol} results")
            grid = extract_results.extract(llm_bytes)
            if grid is None:
                report["results_error"] = "extraction failed or did not pass sanity checks"
            else:
                # Rewrite page-level source URLs to include ?#page=N for the browser PDF viewer.
                sources: list[dict] = []
                pages = sorted({row.get("page") for row in grid["rows"] if row.get("page")})
                for page in pages:
                    sources.append({"label": f"Results filing · page {page}", "url": f"{results_filing['source_url']}#page={page}"})
                grid["sources"] = sources
                grid["cached_pdf"] = f"/pdf-cache/{cached_path.name}" if cached_path else None
                report["results"] = grid
                report["sources"]["results"] = results_filing["source_url"]
        except Exception as exc:
            report["results_error"] = str(exc)
            print(f"{symbol} results: {exc}", file=sys.stderr)

    people_filing = latest(filings, symbol, "management_change")
    if people_filing:
        try:
            _, cached_path, llm_bytes = mirror(people_filing["source_url"], f"{symbol} people")
            events = extract_people.extract(llm_bytes)
            if events:
                for e in events["events"]:
                    e["source"] = {
                        "label": f"Change-in-management filing · page {e.get('page', 1)}",
                        "url": f"{people_filing['source_url']}#page={e.get('page', 1)}",
                    }
                report["people"] = events["events"]
                report["sources"]["people"] = people_filing["source_url"]
        except Exception as exc:
            report["people_error"] = str(exc)
            print(f"{symbol} people: {exc}", file=sys.stderr)

    report["generated_at"] = datetime.now().isoformat(timespec="seconds")
    if write:
        out_path = EVIDENCE_DIR / f"{symbol}.json"
        out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"wrote {out_path} · results={bool(report['results'])} people={len(report['people'])}")
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("symbols", nargs="*", default=["RELIANCE", "INFY", "HDFCBANK", "LT"])
    parser.add_argument("--dry-run", action="store_true", help="do everything but write the output file")
    args = parser.parse_args()

    digest_path = ROOT / "data" / "digest.json"
    filings = json.loads(digest_path.read_text(encoding="utf-8"))["filings"]

    for symbol in args.symbols:
        print(f"\n=== {symbol} ===")
        build_symbol(symbol.upper(), filings, write=not args.dry_run)

    print(f"\n{usage_summary()}")


if __name__ == "__main__":
    main()

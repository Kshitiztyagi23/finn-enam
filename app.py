"""Small API and static host for the FINN prototype."""

from __future__ import annotations

import json
import re
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from urllib.parse import urljoin
from zoneinfo import ZoneInfo

import httpx
from bs4 import BeautifulSoup
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

ROOT = Path(__file__).resolve().parent
app = FastAPI(title="FINN")
app.mount("/static", StaticFiles(directory=ROOT / "web"), name="static")


@app.get("/")
def index():
    return FileResponse(ROOT / "web" / "index.html")


@app.get("/api/digest")
def digest():
    path = ROOT / "data" / "digest.json"
    if not path.exists():
        return {"generated_at": None, "portfolio": [], "prices": {}, "filings": [], "errors": {}, "method": "Run the pipeline to generate the filing cache."}
    return json.loads(path.read_text(encoding="utf-8"))


def text(node) -> str:
    return " ".join(node.get_text(" ", strip=True).split()) if node else ""


def parse_quarters(soup: BeautifulSoup) -> dict:
    table = soup.select_one("#quarters table")
    if not table:
        return {}
    headers = [text(th) for th in table.select("thead th")][1:]
    rows = {}
    for tr in table.select("tbody tr"):
        cells = tr.select("td")
        if cells:
            rows[text(cells[0]).replace("+", "").strip().lower()] = [text(c) for c in cells[1:]]
    wanted = {"revenue": "sales", "ebitda_proxy": "operating profit", "pbt": "profit before tax", "pat": "net profit"}
    values = {}
    for key, label in wanted.items():
        row = rows.get(label, [])
        if len(row) >= 5 and len(headers) >= 5:
            values[key] = {"current": row[-1], "previous": row[-2], "year_ago": row[-5]}
    return {"quarter": headers[-1] if headers else None, "values": values, "source_note": "Screener standardized quarterly table. Operating profit is shown as an EBITDA proxy; verify against the filing."}


def doc_links(soup: BeautifulSoup, base_url: str) -> dict:
    annual, transcripts, recent = [], [], []
    seen = set()
    for anchor in soup.select("#documents a[href]"):
        label, href = text(anchor), urljoin(base_url, anchor["href"])
        if not label or href in seen or href.startswith("javascript:"):
            continue
        seen.add(href)
        entry = {"label": label[:140], "url": href}
        lower = label.lower()
        if "annual report" in lower:
            annual.append(entry)
        elif "transcript" in lower:
            transcripts.append(entry)
        elif len(recent) < 8 and any(term in lower for term in ["financial results", "investor presentation", "press release", "announcement"]):
            recent.append(entry)
    return {"annual_reports": annual[:5], "transcripts": transcripts[:5], "recent_filings": recent[:8]}


@lru_cache(maxsize=128)
def research(symbol: str) -> dict:
    if not re.fullmatch(r"[A-Z0-9&-]{1,20}", symbol):
        raise HTTPException(400, "Enter a valid NSE ticker.")
    url = f"https://www.screener.in/company/{symbol}/consolidated/"
    try:
        response = httpx.get(url, timeout=18, follow_redirects=True, headers={"User-Agent": "Mozilla/5.0 (FINN prototype; source-linked research)"})
        response.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(502, f"Could not load public documents for {symbol}.") from exc
    soup = BeautifulSoup(response.text, "html.parser")
    page_title = text(soup.select_one("h1")) or symbol
    if "404" in response.url.path or not soup.select_one("#documents"):
        raise HTTPException(404, f"No public document page found for {symbol}.")
    links = doc_links(soup, str(response.url))
    about = text(soup.select_one("#top .company-profile")) or text(soup.select_one(".company-profile"))
    return {
        "symbol": symbol,
        "company": page_title,
        "about": about[:450],
        "source_page": str(response.url),
        "fetched_at": datetime.now(ZoneInfo("Asia/Kolkata")).isoformat(timespec="seconds"),
        "quarters": parse_quarters(soup),
        **links,
    }


@app.get("/api/research/{symbol}")
def research_endpoint(symbol: str):
    symbol = symbol.upper()
    if not re.fullmatch(r"[A-Z0-9&-]{1,20}", symbol):
        raise HTTPException(400, "Enter a valid NSE ticker.")
    snapshot = ROOT / "data" / "research" / f"{symbol}.json"
    if snapshot.exists():
        return json.loads(snapshot.read_text(encoding="utf-8"))
    return research(symbol)


@app.get("/api/claims/{symbol}")
def claims_endpoint(symbol: str):
    symbol = symbol.upper()
    if not re.fullmatch(r"[A-Z0-9&-]{1,20}", symbol):
        raise HTTPException(400, "Enter a valid NSE ticker.")
    snapshot = ROOT / "data" / "claims" / f"{symbol}.json"
    if snapshot.exists():
        return json.loads(snapshot.read_text(encoding="utf-8"))
    from pipeline.claims import claims_for
    company = research_endpoint(symbol)
    docs = tuple((item["label"], item["url"]) for item in company["transcripts"][:4])
    return {"symbol": symbol, "claims": claims_for(symbol, docs), "method": "Quantitative forward-looking sentences extracted verbatim from earnings-call transcript PDFs; no outcome judgment is made."}

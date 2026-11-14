"""Refresh FINN's cached NSE filing inbox and end-of-day market signals."""

from __future__ import annotations

import argparse
import importlib
import json
import math
import sys
import warnings
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
VENDOR = ROOT / ".vendor"
if VENDOR.exists():
    sys.path.insert(0, str(VENDOR))

import httpx  # noqa: E402
from nse import NSE  # noqa: E402
from nse.transport import Transport  # noqa: E402
import yfinance as yf  # noqa: E402

warnings.filterwarnings("ignore", category=FutureWarning)

IST = ZoneInfo("Asia/Kolkata")
PORTFOLIO = [
    ("RELIANCE", "Reliance Industries", "Energy & retail"),
    ("HDFCBANK", "HDFC Bank", "Banking"),
    ("INFY", "Infosys", "IT services"),
    ("LT", "Larsen & Toubro", "Industrials"),
    ("BAJFINANCE", "Bajaj Finance", "Lending"),
    ("SUNPHARMA", "Sun Pharma", "Pharma"),
    ("TITAN", "Titan Company", "Consumer"),
    ("TRENT", "Trent", "Retail"),
    ("ETERNAL", "Eternal", "Internet"),
    ("DIXON", "Dixon Technologies", "Electronics"),
    ("POLYCAB", "Polycab India", "Electricals"),
    ("HAL", "Hindustan Aeronautics", "Defence"),
    ("KPITTECH", "KPIT Technologies", "Auto software"),
    ("PERSISTENT", "Persistent Systems", "IT services"),
    ("CDSL", "CDSL", "Capital markets"),
    ("DEEPAKNTR", "Deepak Nitrite", "Chemicals"),
    ("IRCTC", "IRCTC", "Travel"),
    ("SUZLON", "Suzlon Energy", "Renewables"),
]

RULES = [
    ("m&a", 5, ("acquisition", "merger", "demerger", "joint venture", "stake sale", "business transfer agreement")),
    ("litigation", 4, ("litigation", "penalty", "regulatory order", "show cause", "insolvency")),
    ("fund_raise", 4, ("fund raising", "fund raise", "qualified institutions placement", "rights issue", "preferential issue", "commercial paper")),
    ("capex", 4, ("capacity expansion", "capital expenditure", "new plant", "manufacturing facility")),
    ("credit_rating", 3, ("credit rating", "rating action", "rating rationale")),
    ("pledging", 3, ("pledge", "encumbrance")),
    ("dividend", 2, ("dividend",)),
    ("press_release", 2, ("press release", "order win", "bagging/receiving of orders", "rumour verification", "news verification")),
    ("routine", 0, ("trading window", "newspaper", "compliance certificate", "esop", "investor meeting", "postal ballot", "shareholder meeting")),
]


class RedirectingTransport(Transport):
    """Keep the NSE client working when its website redirects its host."""

    def _start_session(self) -> None:
        self._session = httpx.Client(
            headers=self.headers,
            http2=self.use_http2,
            timeout=self.timeout,
            follow_redirects=True,
        )

        cookies = self.cookie_store.load()
        if not cookies.jar:
            cookies = self._fetch_cookies()
            self.cookie_store.save(cookies)

        self._session.cookies.update(cookies)


# nse 5.1.2 constructs Transport internally, so replace that dependency at
# the module boundary rather than changing the installed package.
importlib.import_module("nse.NSE").Transport = RedirectingTransport


def classify(title: str, detail: str) -> tuple[str, int]:
    value = f"{title} {detail}".lower()
    title_lower = title.lower()
    if any(x in value for x in ("newspaper publication", "statutory auditor", "auditor rotation", "certificate under sebi", "stock option", "restricted stock unit")):
        return "routine", 0
    if "change in management" in title_lower or any(x in title_lower for x in ("retirement", "resignation", "cessation")):
        return "management_change", 5
    if any(x in value for x in ("earnings call transcript", "transcript of the discussion", "link of recording", "audio recording")):
        return "earnings_call", 2
    if any(x in value for x in ("financial results", "quarterly results")) and not any(x in title_lower for x in ("press release", "analyst", "presentation")):
        return "results", 5
    if "analyst" in title_lower or "investor presentation" in value:
        return "earnings_call", 2
    for category, score, words in RULES:
        if any(word in value for word in words):
            return category, score
    return "other", 1


def compact(text: str, limit: int = 225) -> str:
    value = " ".join((text or "").split())
    return value if len(value) <= limit else value[: limit - 1].rsplit(" ", 1)[0] + "…"


def fetch_prices(symbols: list[str]) -> dict[str, dict]:
    prices = {}
    for symbol in symbols:
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                frame = yf.Ticker(f"{symbol}.NS").history(period="2mo", timeout=12)
            frame = frame.dropna(subset=["Close", "Volume"])
            if len(frame) < 2:
                continue
            latest, previous = frame.iloc[-1], frame.iloc[-2]
            volume_history = frame["Volume"].iloc[-21:-1]
            average = float(volume_history.mean()) if len(volume_history) else 0
            close = float(latest["Close"])
            move = (close / float(previous["Close"]) - 1) * 100
            ratio = float(latest["Volume"]) / average if average else None
            if not all(math.isfinite(x) for x in [close, move]):
                continue
            prices[symbol] = {
                "as_of": str(frame.index[-1].date()),
                "close": round(close, 2),
                "move_pct": round(move, 2),
                "volume_ratio": round(ratio, 2) if ratio and math.isfinite(ratio) else None,
            }
        except Exception as exc:
            print(f"price {symbol}: {exc}", file=sys.stderr)
    return prices


def fetch_filings(symbols: list[str], since: date, until: date) -> tuple[list[dict], dict[str, str]]:
    filings, errors = [], {}
    with NSE(download_folder=str(ROOT / ".cache")) as nse:
        for symbol in symbols:
            try:
                raw = nse.announcements(symbol=symbol, from_date=since, to_date=until)
                print(f"{symbol}: {len(raw)} filings", flush=True)
                for item in raw:
                    title = compact(item.get("desc") or "Exchange filing", 130)
                    detail = compact(item.get("attchmntText") or title)
                    category, base = classify(title, detail)
                    filings.append({
                        "id": str(item.get("seq_id") or item.get("dt")),
                        "symbol": symbol,
                        "company": item.get("sm_name") or symbol,
                        "published_at": str(item.get("sort_date") or "").replace(" ", "T") + "+05:30",
                        "category": category,
                        "score": base,
                        "headline": title,
                        "summary": detail,
                        "source_url": item.get("attchmntFile") or "",
                        "source": "NSE filing",
                    })
            except Exception as exc:
                errors[symbol] = str(exc)
                print(f"filings {symbol}: {exc}", file=sys.stderr)
    return filings, errors


def build(days: int, symbols: list[str], skip_prices: bool = False) -> dict:
    today = datetime.now(IST)
    since = (today - timedelta(days=days)).date()
    filings, errors = fetch_filings(symbols, since, today.date())
    prices = {} if skip_prices else fetch_prices(symbols)
    for item in filings:
        price = prices.get(item["symbol"])
        filing_time = datetime.fromisoformat(item["published_at"])
        price_day = date.fromisoformat(price["as_of"]) if price else None
        # Only the same session (if published before close) or the next
        # weekday can confirm a filing. Holidays are omitted conservatively.
        next_session = filing_time.date() + timedelta(days=1)
        while next_session.weekday() >= 5:
            next_session += timedelta(days=1)
        before_close = filing_time.hour < 15 or (filing_time.hour == 15 and filing_time.minute <= 30)
        confirms_filing = bool(price and (price_day == filing_time.date() and before_close or price_day == next_session))
        if confirms_filing:
            item["price"] = price
            if abs(price["move_pct"]) >= 3:
                item["score"] += 1
            if price["volume_ratio"] and price["volume_ratio"] >= 2:
                item["score"] += 1
        item["tier"] = "act" if item["score"] >= 5 else "note" if item["score"] >= 2 else "routine"
        item["reason"] = item["category"].replace("_", " ").title()
        if confirms_filing:
            item["reason"] += f" · {price['move_pct']:+g}% price move"
            if price["volume_ratio"]:
                item["reason"] += f" · {price['volume_ratio']:g}× volume"
    filings.sort(key=lambda x: (x["score"], x["published_at"]), reverse=True)
    return {
        "generated_at": today.isoformat(timespec="seconds"),
        "window_days": days,
        "portfolio": [{"symbol": s, "name": n, "sector": sector} for s, n, sector in PORTFOLIO if s in symbols],
        "prices": prices,
        "filings": filings,
        "errors": errors,
        "method": "NSE filings classified with explicit keyword rules; end-of-day Yahoo Finance prices when available.",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=7)
    parser.add_argument("--symbols", nargs="*", default=[x[0] for x in PORTFOLIO])
    parser.add_argument("--skip-prices", action="store_true")
    args = parser.parse_args()
    payload = build(args.days, [s.upper() for s in args.symbols], args.skip_prices)
    output = ROOT / "data" / "digest.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    if not payload["filings"] and payload["errors"] and output.exists():
        raise RuntimeError("All filing fetches failed; keeping the previous snapshot.")
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {len(payload['filings'])} filings to {output}")


if __name__ == "__main__":
    main()

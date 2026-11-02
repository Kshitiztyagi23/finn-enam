"""Precompute a few demo research views; arbitrary NSE tickers still fetch live."""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app import research  # noqa: E402

digest_path = ROOT / "data" / "digest.json"
portfolio = [item["symbol"] for item in json.loads(digest_path.read_text(encoding="utf-8")).get("portfolio", [])] if digest_path.exists() else ["RELIANCE", "DIXON"]
symbols = [x.upper() for x in sys.argv[1:]] or list(dict.fromkeys(portfolio + ["ASTRAL", "PIDILITIND"]))
output_dir = ROOT / "data" / "research"
output_dir.mkdir(parents=True, exist_ok=True)
for symbol in symbols:
    try:
        payload = research(symbol)
        (output_dir / f"{symbol}.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"{symbol}: {len(payload['annual_reports'])} reports, {len(payload['transcripts'])} transcripts")
    except Exception as exc:
        print(f"{symbol}: {exc}", file=sys.stderr)

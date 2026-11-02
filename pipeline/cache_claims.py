"""Cache source-linked transcript candidates for demo tickers."""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from pipeline.claims import claims_for  # noqa: E402

output_dir = ROOT / "data" / "claims"
output_dir.mkdir(parents=True, exist_ok=True)
for symbol in sys.argv[1:] or ["RELIANCE", "DIXON"]:
    symbol = symbol.upper()
    company = json.loads((ROOT / "data" / "research" / f"{symbol}.json").read_text(encoding="utf-8"))
    docs = tuple((item["label"], item["url"]) for item in company["transcripts"][:4])
    payload = {"symbol": symbol, "claims": claims_for(symbol, docs), "method": "Quantitative forward-looking sentences extracted from source transcripts; check speaker and outcome against later filings."}
    (output_dir / f"{symbol}.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"{symbol}: {len(payload['claims'])} source-linked candidates")

# Submission draft

**To:** assessment@enam.com
**Subject:** ENAM - IIT screening - 2027

Hello ENAM team,

I built **FINN**, a mobile-first portfolio filing desk for an 18-stock NSE watchlist. I'm aware this is two days past the stated deadline — if that disqualifies me, I understand. I wanted to send what I actually built rather than skip the exercise.

The **Brief** opens on the latest 24 hours of the cached snapshot, groups related earnings documents into one company event, and offers a seven-day view. Each event opens to the full source trail. The archive keeps every original announcement searchable; **Signals** lets the investor tune filing, price, and volume matches.

**Research** accepts any NSE ticker and, for five companies this submission ships with as verified evidence — DIXON (hand-curated), RELIANCE, INFY, HDFCBANK and LT — renders a four-metric results grid (Revenue, EBITDA, PBT, PAT) with QoQ and YoY deltas, each cell linked to a specific page of the Outcome PDF. Appointments extracted from change-in-management filings include each appointee's filing-disclosed bio. A **Promise Tracker** (DIXON, RELIANCE, INFY) reconciles management's prior earnings-call statements against the later Outcome PDF — delivered / partial / missed / pending, with the verdict rule stated and both source pages one tap away.

The push pipeline is deterministic — rules only, no model cost, scoring is inspectable. The LLM is Gemini 3.5 Flash with a model-chain fallback, used only for extracting structured facts from PDFs under a strict JSON schema plus deterministic sanity checks (unit, PBT ≥ PAT, no >10× magnitude swings). Every call is cached by (model, prompt, pdf-hash) so a demo view costs ₹0. A pipeline self-test reproduces the hand-verified Dixon grid to 0.1% on all 12 cells before any new ticker is trusted. The HDFCBANK Promise Tracker call hit a corrupted-PDF upstream and L&T's hit a Gemini quota during build — both tickers still ship with their verified results grid and the document trail.

The engine generalises: on-demand research works on any NSE ticker from Screener's document index. Primary-source discipline is enforced in prompts and in UI copy — no broker notes, no outside knowledge, every claim either has a page link or is marked "not disclosed".

- Prototype: [add deployed link]
- GitHub repository: [add repository link]
- AI build history: [add Claude Code + Codex export/share links]

Regards,
Kshitij

## Before sending

1. Deploy the Dockerfile to Fly.io / Render / Railway and paste the URL.
2. Push the repo and paste its link.
3. Export the Claude Code session and the Codex session, paste share links.
4. Open the deployed link on a phone and verify Brief, Research → DIXON / RELIANCE / INFY, and Signals.
5. Replace all bracketed placeholders.

# FINN product direction

Research and design notes, 3 November 2026. These are product hypotheses based on the assignment, the current prototype, and published feature descriptions. They are not usability-study findings.

## The product promise

**FINN helps an investor answer three questions:**

1. **What changed in my companies?** A short, time-bounded portfolio brief.
2. **Why should I care?** A concrete change, the rule that surfaced it, and useful context without implying a market move was caused by a filing.
3. **Can I verify it?** The exact primary document and page behind each material fact.

The most distinctive demonstration should be a **management memory**: what was said in an earlier call, what period and metric it concerned, and what a later company filing actually reported. `Met`, `missed`, or `pending` must follow explicit comparison rules; uncertain matches stay pending.

## Three directions considered

| Direction | Investor job | Strength | Cost or risk |
| --- | --- | --- | --- |
| **Event brief** | Catch up on the portfolio each morning. | Fast, calm, works across all 18 companies. | Needs reliable event grouping and specific headlines. |
| **Management memory** | Check whether a company delivered what it previously said. | Distinctive research capability that fits the assignment. | Source matching is hard; careless verdicts can mislead. |
| **Research workspace** | Investigate any ticker and search all documents. | Broad utility after the demo. | Breadth can consume time before the core evidence path works. |

**Recommendation:** make the event brief the entry point, then let a relevant event open a management-memory comparison. Add wider research tools after that loop is credible. This creates a clear story for the demo: *notice → understand → verify → remember*.

## Reading and visual rules

- The first screen should show one lead event and a few compact follow-ups. The archive carries the complete filing trail.
- Use a single clear headline per card, then one line of quantified context when verified. Put document counts, timestamps, and source status in a consistent location.
- Reserve tables for comparison tasks. Four aligned result metrics are easier to inspect than four separate scorecards.
- Give source, period, units, and reporting basis a visible place beside each comparison. If extraction is uncertain, label the figure unverified and open the original document.
- Keep controls near the task: time window on the Brief, document filters in the archive, source and comparison controls in Research, delivery controls in Signals.

## What other products teach us

| Published feature | Useful lesson for FINN | Our specific adaptation |
| --- | --- | --- |
| [Quartr event summaries](https://quartr.com/features/summaries) assemble reports, slides, and transcripts and link each line to its source. | A company event is a better reading unit than several separate document rows. | One earnings card expands to every related filing; facts link to the relevant PDF page. |
| [Quartr slide history](https://quartr.com/features/slide-history-comparison) compares messages and KPIs across periods. | The investor needs memory across quarters. | A compact promise timeline with statement, target, subsequent outcome, and two sources. |
| [Koyfin Watchlist News](https://www.koyfin.com/help/watchlist-news-feature/) lets users filter watchlist news by sources and topics. | Noise control is personal. | Keep all filings searchable; let investors tune which categories reach the brief and alerts. |
| [Trendlyne Alpha Alerts](https://trendlyne.com/alerts/portfolio-real-time-alerts/) offers live, hourly, and daily digests for distinct filing and market categories. | Cadence matters as much as thresholds. | Urgent categories can alert immediately; less urgent items join a daily digest. Show actual delivery history. |
| [TradingView News Alerts](https://www.tradingview.com/support/solutions/43000762838-news-alerts/) are attached to saved flows and show whether they are active. | An alert needs an understandable scope and visible state. | Each FINN rule states companies, categories, threshold, channel, and last match; allow pause and edit. |
| [Fiscal.ai sourcing](https://docs.fiscal.ai/docs/introduction) links financial data points back to filing tables. | A source link beside a table is weaker than a source attached to each figure. | Each revenue, EBITDA, PBT, and PAT number has filing, page, basis, period, and unit metadata. |
| [Tickertape Scorecard](https://www.tickertape.in/blog/introducing-scorecard-stock-analysis-got-quicker-and-better-with-quantitative-insights/) makes a dense stock view scannable and expands scores to reveal their inputs. | A short summary can lead into more detail. | Use plain-language observations and expandable evidence, without an opaque investment score. |

These are descriptions published by the companies. We have not measured whether their users complete the tasks faster. [Progressive disclosure](https://www.nngroup.com/articles/progressive-disclosure/) supports putting essential information first and offering deeper detail on demand; FINN should test that principle against its own tasks.

## Proposed mobile experience

**Home / Brief**

```text
Your portfolio · Last 24 hours                         [Change window]

2 developments need attention · 4 other filings

DIXON · Earnings · 10:09
Revenue grew 24% YoY; margin fell 1.2 points.
Reported in Q2 consolidated results.                [Review event →]

RELIANCE · Leadership · 14:32
New independent director appointed.                 [Review event →]

Other filings                                      [Expand 4]
```

- Default to the assignment's latest 24 hours. Offer 7 days and a custom range. Explain when the snapshot was last refreshed and when no filing was found.
- One card per **event**, with clear counts of related documents. Preserve the complete filing archive with routine items and direct links.
- The top card says the **specific change** and its measurement basis. Avoid generic wording such as “quarterly results published.”
- Use color for scan support, never as the only carrier of importance. Keep reason and source visible in text.

**Event detail**

```text
DIXON · Q2 FY27 results
What changed       Revenue ↑ 24% YoY · EBITDA margin ↓ 1.2 pp
Why surfaced       Results rule + above-threshold filing priority
What to check      Margin basis and management's prior volume target

Evidence           Results PDF p. 4 · Presentation p. 12 · Call transcript p. 8
All documents      4 filings [expand]
```

The exact numbers in this sketch are illustrative only; they must not appear in the live app unless verified from the company's filing.

**Research / Management memory**

```text
What management said                 Later company result
“...target...” · Q1 call p. 7         Actual metric · Q2 filing p. 5
Target: segment X / FY27             Comparison: same segment and period?
Status: pending until comparable disclosure exists
```

The user can open either source, see the comparison rule, and mark an extraction error for correction. No status is inferred when the segment, metric, time period, or basis differs.

**Signals**

Start with three readable presets: `Results and guidance`, `Leadership or governance`, and `Large EOD move`. A rule preview shows how many existing items would match. The saved rule view shows `Active`, `Paused`, or `Delivery unavailable`, the last match, and where delivery occurred. A local preview must never be labeled a sent notification.

## Build order

### 1. Event brief and complete trail — highest UX return

Group related results, presentation, call, and recording filings by company and reporting period. Change the brief default to 24 hours. Each group has a precise headline and an expandable document list. Keep all 88 current filings reachable from the archive, with no lost or duplicated source links. Test empty, stale-data, and same-day multiple-event states.

### 2. Filing-grounded results — highest trust return

Extend the curated Dixon evidence to two or three varied companies, then create a general extraction path with a visible `unverified` fallback. Every result row records the source page, standalone/consolidated basis, quarter, unit, and calculation. The current Screener standardized table is useful orientation but does not satisfy the brief's primary-source standard for final research answers. Do not present an operating-profit proxy as filed EBITDA.

### 3. Four-quarter management memory — strongest differentiator

Build one complete, defensible example. Choose a statement with a quantitative target and a later company report that measures the same item. Show the original statement, exact period/segment/basis, later actual, and comparison method. If no exact comparable disclosure exists, show `pending` and explain the missing evidence. Then extend to four quarters and more companies.

### 4. Real alert loop — assignment completeness

Persist rules outside a single browser, evaluate each new filing or EOD datapoint once, and record match and delivery states. For a local demo, in-app notifications plus a delivery log can prove the loop. External push can follow once its channel is configured. Include threshold, cadence, pause, duplicate suppression, and an explicit explanation for each match.

### 5. Personalization and polish

Let the investor edit the watchlist, choose categories and cadence, and save a research question for follow-up. Then run short task-based usability checks: find the most consequential event in 30 seconds; verify one number in 2 minutes; assess one promise in 5 minutes. Treat those timings as targets until observed with real participants.

## Tools and skills

| Need | Current or proposed tool | Decision |
| --- | --- | --- |
| Interface direction and interaction behavior | Installed `frontend-design`, `product-design-and-ux`, `web-accessibility`, `playwright` | Use these for the next build and browser review. More UI skills will not fix weak evidence or event structure. |
| PDF tables, OCR, page-aware structure | Installed [Docling skill](https://github.com/docling-project/docling/blob/main/docling/.agents/skills/docling/SKILL.md); [PyMuPDF table extraction](https://pymupdf.readthedocs.io/en/latest/page.html#Page.find_tables) is another candidate | Trial each on three representative NSE filings before adding a heavy runtime. Compare accuracy, source-page retention, time, and setup cost. The skill is installed; the Docling runtime is not. |
| Search across transcripts | [SQLite FTS5](https://www.sqlite.org/fts5.html) | A lightweight local full-text index with snippets can support 18 companies before adding a vector database. |
| Extra charting/visualization skill | Explored GitHub options | Defer. The core tasks benefit more from clear comparisons and source evidence than more charts. |

## Decision boundary

The current feature research is enough to choose a prototype direction. It is not evidence that investors prefer this flow. Before adding more surface area, the best next build is **event grouping + 24-hour brief + one complete promise comparison**. The first two improve the daily read; the last makes the submission memorable and directly demonstrates the assignment's research challenge.

## Build progress

- Event grouping, the 24-hour Brief default, and the seven-day switch are implemented. The cached 88 filings remain in the archive and in the event source trails.
- The interface now uses a shared Almanac design system: cool slate, a pale sheet, ruled event rows, and a practical data-provenance footer. Dixon's management statement and later-disclosure check are shown side by side, with both source links. Unsupported tickers show primary document trails without secondary-source result figures.
- The four-quarter outcome ledger, general primary-source result extractor, and actual notification delivery remain to be built. The current statement remains explicitly pending until comparable source evidence exists.

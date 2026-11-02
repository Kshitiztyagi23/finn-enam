# Submission draft

**To:** assessment@enam.com  
**Subject:** ENAM - IIT screening - 2027

Hello ENAM team,

I built **FINN**, a mobile-first portfolio brief that turns exchange filings into a ranked inbox for an 18-stock NSE portfolio. It shows the few filings worth attention first, keeps routine filings accessible in a collapsed group, and lets the investor tune filing, price, and volume signals. Every item links back to its exchange filing.

The research view accepts an NSE ticker and opens a document trail of annual reports and earnings-call transcripts. Its guidance ledger extracts page-linked candidate statements from the original transcript PDFs. I chose to leave outcome labels open until a statement can be matched to the correct later filing; the prototype does not guess whether management delivered.

The pipeline uses explicit rules and cached public data, so the brief has no model API cost. This keeps the demo fast and the priority judgment inspectable. The tradeoff is that ambiguous filings need human review, and PDF extraction can introduce text spacing errors. The next step would be source-verified matching of guidance to outcomes, followed by result-table extraction directly from exchange filings and management-change bios.

- Prototype: [add deployed link]
- GitHub repository: [add repository link]
- AI build history: [add Claude and Codex export/share links]

Regards,  
[Your name]

## Before sending

1. Confirm ENAM accepts a submission after the November 1, 2026 deadline.
2. Publish the repository and deploy the app from the Dockerfile.
3. Open the deployed link on a phone and verify Today, Research, and Signals.
4. Export or share the Claude conversation and this Codex build session.
5. Replace all bracketed placeholders above.

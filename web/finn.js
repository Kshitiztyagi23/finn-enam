const byId = id => document.getElementById(id);
const categories = {
  results: "Results", "m&a": "Transaction", management_change: "Leadership",
  litigation: "Legal", fund_raise: "Fund raise", capex: "Expansion",
  credit_rating: "Credit rating", pledging: "Pledging", earnings_call: "Earnings call",
  press_release: "Company update", dividend: "Dividend", other: "Filing", routine: "Routine"
};
const defaults = { price: 3, volume: 2, categories: ["results", "m&a", "management_change"] };
function stored(key, fallback) {
  try { return JSON.parse(localStorage.getItem(key)) ?? fallback; } catch { return fallback; }
}
const state = {
  digest: null, view: "brief", days: 7, briefDays: 1, archivePage: 1, showRoutine: false,
  search: "", company: "all", allMatches: false, allBriefEvents: false,
  seen: new Set(stored("finn-seen", [])),
  rules: { ...defaults, ...stored("finn-rules", {}) }
};
function esc(value) {
  return String(value ?? "").replace(/[&<>"']/g, c => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
  }[c]));
}
function safeUrl(value) {
  try { const u = new URL(value); return ["https:", "http:"].includes(u.protocol) ? u.href : "#"; }
  catch { return "#"; }
}
function date(value, time = false) {
  const d = new Date(value);
  return Number.isNaN(d.getTime()) ? "Date unavailable" : d.toLocaleString("en-IN", {
    day: "numeric", month: "short", ...(time ? { hour: "numeric", minute: "2-digit" } : {}), timeZone: "Asia/Kolkata"
  });
}
function snapshotTime() { return Date.parse(state.digest?.generated_at || "") || Date.now(); }
function withinDays(value, days) {
  return days === "all" || Date.parse(value) >= snapshotTime() - days * 86400000;
}
function switchView(name, focus = true, updateUrl = true) {
  state.view = name;
  document.querySelectorAll(".view").forEach(el => el.classList.toggle("visible", el.id === `view-${name}`));
  document.querySelectorAll("[data-view]").forEach(el => {
    if (el.dataset.view === name) el.setAttribute("aria-current", "page");
    else el.removeAttribute("aria-current");
  });
  if (updateUrl && location.hash !== `#${name}`) history.pushState(null, "", `#${name}`);
  window.scrollTo({ top: 0, behavior: "smooth" });
  if (focus) byId(`${name}-title`)?.focus({ preventScroll: true });
}
function distinct(items) {
  const seen = new Set();
  return items.filter(x => {
    const key = [x.symbol, x.category, x.summary, x.published_at?.slice(0, 10)].join("|");
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}
function companyName(item) {
  const portfolioName = state.digest?.portfolio?.find(x => x.symbol === item.symbol)?.name;
  return String(portfolioName || item.company || item.symbol).replace(/\s+(Limited|Ltd\.?|Company Limited)$/i, "").trim();
}
function filingTitle(item) {
  const company = companyName(item);
  const summary = item.summary || "";
  if (item.symbol === "DIXON" && /DIXON_30102026160939_/i.test(item.source_url || "")) return "Prithvi Vachani joins Dixon’s board";
  if (item.category === "management_change") {
    const retirement = summary.match(/Retirement of (?:Mr\.?|Shri|Prof\.?)?\s*([^,]+?) as (?:the )?([^,.]+?)(?:\.|$)/i);
    if (retirement) return `${retirement[1].trim()} retires as ${company} ${retirement[2].trim().toLowerCase()}`;
    return `${company} reports a leadership change`;
  }
  if (item.category === "results") {
    const month = ["March", "June", "September", "December"].find(x => new RegExp(x, "i").test(summary));
    return `${company} files ${month ? `${month}-quarter` : "quarterly"} results`;
  }
  if (item.category === "press_release" && /clarification/i.test(summary)) {
    if (/assam facility/i.test(summary)) return `${company} files an Assam facility clarification`;
    return `${company} files a clarification`;
  }
  if (item.category === "press_release" && /orders?\/contracts?|receiving of orders/i.test(summary)) return `${company} reports a new order`;
  if (item.category === "litigation") return `${company} files a legal update`;
  if (item.category === "credit_rating") return `${company} receives a credit-rating update`;
  if (item.category === "m&a") return `${company} files a transaction update`;
  if (item.category === "earnings_call") {
    if (/investor presentation/i.test(summary)) return `${company} shares its investor presentation`;
    if (/transcript/i.test(summary)) return `${company} posts an earnings-call transcript`;
    if (/recording|audio/i.test(summary)) return `${company} posts an earnings-call recording`;
    return `${company} shares an earnings-call update`;
  }
  if (item.category === "routine") return `${company} files routine paperwork`;
  const headline = item.headline || "Company filing";
  return headline.length > 65 ? `${headline.slice(0, 62).trim()}…` : `${company}: ${headline}`;
}
function storyReason(item) {
  const raw = String(item.summary || item.headline || "").replace(/\s+/g, " ").trim();
  if (!raw) return "Open the filing for the full exchange announcement.";
  if (/clarification regarding news report.*assam facility/i.test(raw)) return "The company filed a clarification about a news report concerning its Assam facility.";
  const brief = raw.replace(/^.{0,120}?(?:has informed the Exchange|has submitted to the Exchange)[, ]*(?:about|regarding)?\s*/i, "");
  const sentence = brief.length > 190 ? `${brief.slice(0, 187).trimEnd()}…` : brief;
  return sentence.charAt(0).toUpperCase() + sentence.slice(1);
}
function source(item, label = "Open filing") {
  const link = safeUrl(item.source_url);
  return link !== "#" ? `<a class="text-link" href="${esc(link)}" target="_blank" rel="noopener noreferrer" aria-label="${esc(label)} for ${esc(item.symbol)} in a new tab">${esc(label)}</a>` : `<span class="missing-source">Source PDF unavailable</span>`;
}
function reviewButton(item) {
  return `<button class="text-button secondary" type="button" data-review="${esc(item.id)}">${state.seen.has(item.id) ? "Mark unread" : "Mark reviewed"}</button>`;
}
function isEarningsCompanion(item) {
  const value = `${item.headline || ""} ${item.summary || ""}`;
  return item.category === "earnings_call" || /financial results|investor presentation|analyst presentation|earnings.call transcript|conference call|link of recording|media release relating to financial results/i.test(value);
}
function relatedEventType(item) {
  const value = `${item.headline || ""} ${item.summary || ""}`;
  if (item.category === "press_release" && /clarification|news report/i.test(value)) return "clarification";
  if ((item.category === "management_change" || item.category === "other") && /director|appointment|retirement|management/i.test(value)) return "leadership";
  return null;
}
function allEvents() {
  const filings = state.digest?.filings || [];
  const anchors = [];
  const events = [];
  const assigned = new Set();
  for (const item of filings.filter(x => x.category === "results")) {
    let group = anchors.find(e => e.symbol === item.symbol && Math.abs(Date.parse(e.anchor.published_at) - Date.parse(item.published_at)) < 36 * 3600000);
    if (!group) {
      group = { symbol: item.symbol, anchor: item, items: [], type: "earnings" };
      anchors.push(group); events.push(group);
    }
    group.items.push(item); assigned.add(item.id);
  }
  for (const item of filings) {
    if (assigned.has(item.id)) continue;
    if (isEarningsCompanion(item) && item.tier !== "routine") {
      const candidates = anchors.filter(e => e.symbol === item.symbol && Date.parse(item.published_at) - Date.parse(e.anchor.published_at) >= -3 * 86400000 && Date.parse(item.published_at) - Date.parse(e.anchor.published_at) <= 10 * 86400000);
      candidates.sort((a, b) => Math.abs(Date.parse(a.anchor.published_at) - Date.parse(item.published_at)) - Math.abs(Date.parse(b.anchor.published_at) - Date.parse(item.published_at)));
      if (candidates[0]) { candidates[0].items.push(item); assigned.add(item.id); continue; }
    }
    const relatedType = relatedEventType(item);
    const group = relatedType && events.find(e => e.symbol === item.symbol && e.type === relatedType && Math.abs(Date.parse(e.anchor.published_at) - Date.parse(item.published_at)) <= (relatedType === "clarification" ? 2 : 1) * 86400000);
    if (group) group.items.push(item);
    else events.push({ symbol: item.symbol, anchor: item, items: [item], type: relatedType || "filing" });
    assigned.add(item.id);
  }
  return events;
}
function briefEvents() {
  return allEvents().map(event => {
    const recent = event.items.filter(x => withinDays(x.published_at, state.briefDays) && x.tier !== "routine");
    if (!recent.length) return null;
    recent.sort((a, b) => b.score - a.score || Date.parse(b.published_at) - Date.parse(a.published_at));
    return { ...event, current: recent[0], recentCount: recent.length, lastAt: Math.max(...recent.map(x => Date.parse(x.published_at))), score: recent[0].score };
  }).filter(Boolean).sort((a, b) => b.score - a.score || b.lastAt - a.lastAt);
}
function eventLabel(event) {
  if (event.type === "earnings") return "Earnings record";
  if (event.type === "clarification") return "Clarification";
  if (event.type === "leadership") return "Leadership";
  return categories[event.current.category] || "Filing";
}
function eventDocuments(event) {
  const items = [...event.items].sort((a, b) => Date.parse(b.published_at) - Date.parse(a.published_at));
  return `<details class="event-docs"><summary>View ${items.length} source ${items.length === 1 ? "filing" : "filings"}</summary><div class="event-doc-list">${items.map(x => `<div class="event-doc"><span>${esc(date(x.published_at, true))}<br>${esc(categories[x.category] || "Filing")}</span><div><strong>${esc(filingTitle(x))}</strong>${source(x, "Open PDF")}</div></div>`).join("")}</div></details>`;
}
function eventBody(event) {
  const item = event.current;
  if (event.type === "earnings" && item.category === "earnings_call") return "This document joins the results record.";
  return storyReason(item);
}
function renderBrief() {
  if (!state.digest) return;
  const events = briefEvents();
  const lead = events[0];
  byId("brief-title").textContent = "What changed in your portfolio";
  byId("brief-context").textContent = `${state.digest.portfolio.length} companies followed`;
  byId("brief-copy").textContent = `${events.length} ${events.length === 1 ? "development" : "developments"} in the ${state.briefDays === 1 ? "last 24 hours" : "last 7 days"}, as of this snapshot.`;
  byId("brief-date").textContent = date(state.digest.generated_at, true);
  byId("brief-date").dateTime = state.digest.generated_at || "";
  document.querySelectorAll("[data-brief-days]").forEach(button => {
    const active = Number(button.dataset.briefDays) === state.briefDays;
    button.classList.toggle("active", active);
    button.setAttribute("aria-pressed", String(active));
  });
  byId("archive-cta-count").textContent = `${state.digest.filings.length} filings`;
  if (!lead) {
    byId("lead-story").innerHTML = `<div class="empty-state"><strong>No developments in this window.</strong><p>Try 7 days or open the complete filing archive.</p><button class="text-button" type="button" data-brief-days="7">Show 7 days</button></div>`;
    byId("next-stories").innerHTML = "";
    byId("next-count").textContent = "";
    byId("brief-show-all").hidden = true;
    return;
  }
  byId("lead-story").innerHTML = `<article class="lead-story">
    <div class="lead-top"><span class="lead-tag">${esc(lead.symbol)} <span>${esc(eventLabel(lead))}</span></span><time class="lead-date" datetime="${esc(lead.current.published_at)}">${esc(date(lead.current.published_at, true))}</time></div>
    <h2>${esc(filingTitle(lead.current))}</h2><p>${esc(eventBody(lead))}</p>
    <div class="lead-actions">${source(lead.current, "Read latest filing")}<button class="text-button" type="button" data-research="${esc(lead.symbol)}">Research ${esc(lead.symbol)}</button>${reviewButton(lead.current)}</div>
    ${eventDocuments(lead)}
  </article>`;
  const next = state.allBriefEvents ? events.slice(1) : events.slice(1, 5);
  byId("next-count").textContent = events.length > 5 ? `${next.length} of ${events.length - 1} shown` : `${next.length} more`;
  byId("brief-show-all").hidden = events.length <= 5;
  byId("brief-show-all").textContent = state.allBriefEvents ? "Show fewer developments" : `Show all ${events.length - 1} developments`;
  byId("next-stories").innerHTML = next.map(event => `<article class="story-row">
    <div class="story-main"><div class="row-meta"><strong>${esc(event.symbol)}</strong><span>${esc(eventLabel(event))}</span><time datetime="${esc(event.current.published_at)}">${esc(date(event.current.published_at, true))}</time></div><h3>${esc(filingTitle(event.current))}</h3><p class="row-note">${esc(eventBody(event))}</p>${eventDocuments(event)}</div>
  </article>`).join("");
}
function archiveItems() {
  const cutoff = state.days === "all" ? -Infinity : snapshotTime() - state.days * 86400000;
  const query = state.search.trim().toLowerCase();
  return (state.digest?.filings || []).filter(x => {
    if (Date.parse(x.published_at) < cutoff) return false;
    if (!state.showRoutine && x.tier === "routine") return false;
    if (state.company !== "all" && x.symbol !== state.company) return false;
    return !query || [x.symbol, x.company, x.summary, x.headline, categories[x.category]].some(v => String(v || "").toLowerCase().includes(query));
  }).sort((a, b) => Date.parse(b.published_at) - Date.parse(a.published_at));
}
function renderArchive() {
  if (!state.digest) return;
  document.querySelectorAll("[data-days]").forEach(button => {
    const active = String(state.days) === button.dataset.days;
    button.classList.toggle("active", active);
    button.setAttribute("aria-pressed", String(active));
  });
  const items = archiveItems();
  const shown = items.slice(0, state.archivePage * 12);
  byId("archive-count").textContent = `${items.length} ${items.length === 1 ? "filing" : "filings"}`;
  byId("archive-list").innerHTML = shown.length ? shown.map(x => `<article class="filing-item">
    <div><div class="row-meta">${esc(x.symbol)}, ${esc(categories[x.category] || "Filing")}, ${esc(date(x.published_at, true))}</div><h3>${esc(filingTitle(x))}</h3><p>${esc(storyReason(x).slice(0, 135))}${storyReason(x).length > 135 ? "…" : ""}</p></div>${source(x, "Open PDF")}
  </article>`).join("") : `<div class="empty-state"><strong>No filings match.</strong><p>Try a different search, company or date range.</p></div>`;
  byId("load-more").hidden = shown.length >= items.length;
  byId("load-more").textContent = `Show more filings (${items.length - shown.length} left)`;
}
function n(value) { if (value == null || String(value).trim() === "") return null; const x = Number(String(value).replaceAll(",", "")); return Number.isFinite(x) ? x : null; }
function fmtNum(value) {
  if (value == null) return "—";
  const abs = Math.abs(value);
  const digits = abs >= 100 ? 0 : abs >= 10 ? 1 : 2;
  return value.toLocaleString("en-IN", { minimumFractionDigits: digits, maximumFractionDigits: digits });
}
function delta(current, previous) {
  if (current === null || previous === null || !previous) return "—";
  const value = (current / previous - 1) * 100;
  return `<span class="${value >= 0 ? "positive" : "negative"}">${value > 0 ? "+" : ""}${value.toFixed(1)}%</span>`;
}
const VERDICT_GLYPH = { delivered: "▲", partial: "◆", missed: "■", pending: "●" };
function verdictChip(verdict, label) {
  const key = (verdict || "pending").toLowerCase();
  const glyph = VERDICT_GLYPH[key] || VERDICT_GLYPH.pending;
  return `<span class="verdict-chip verdict-${esc(key)}"><span class="glyph" aria-hidden="true">${glyph}</span>${esc(label)}</span>`;
}
function documentGroup(title, items) {
  return `<details class="document-group"><summary>${esc(title)} <span>${items?.length || 0} documents</span></summary><div class="document-links">${items?.length ? items.map(x => `<a href="${esc(safeUrl(x.url))}" target="_blank" rel="noopener noreferrer">${esc(x.label)}</a>`).join("") : "<p>No documents found.</p>"}</div></details>`;
}
const VERDICT_LABEL = { delivered: "Delivered", partial: "Partial", missed: "Missed", pending: "Awaiting outcome" };
function normalizeEvidence(ev) {
  // Dixon is hand-crafted and already matches the display shape; new tickers come
  // from pipeline/build_evidence.py + build_promises.py in a slightly richer shape.
  // One shim here keeps renderResearch simple.
  if (ev?.results && !ev.results.calculation_note && ev.results.notes) ev.results.calculation_note = ev.results.notes;
  if (Array.isArray(ev?.promise)) {
    ev.promise = ev.promise.map(p => {
      if (p.status && p.source) return p; // Dixon's hand shape
      const label = VERDICT_LABEL[p.verdict] || "Awaiting outcome";
      const target = p.target ? ` Target: ${p.target}.` : "";
      const actual = p.actual ? ` Actual: ${p.actual}.` : " Actual not yet reported comparably.";
      return {
        ...p,
        status: label,
        source: p.statement_source || p.source || null,
        check: `${p.reasoning || ""}${target}${actual}`.trim(),
        actual_source: p.actual_source || null,
      };
    });
  }
  if (Array.isArray(ev?.people)) {
    ev.people = ev.people.map(p => {
      if (!p.role && p.change) return p;
      const change = [p.role, p.change && p.change !== p.role ? `(${p.change}${p.effective ? ` ${p.effective}` : ""})` : null].filter(Boolean).join(" ");
      return { ...p, change: change || p.change || "" };
    });
  }
  return ev;
}
function renderResearch(data, evidence) {
  evidence = normalizeEvidence(evidence || {});
  byId("research-form").classList.add("has-result");
  document.querySelector(".try-line").hidden = true;
  const rows = evidence.results?.rows || [];
  const verified = !!evidence.results;
  const results = rows.length ? `<table class="results-table"><thead><tr><th>${esc(evidence.results.unit || "₹ crore")}</th><th>Latest</th><th>QoQ</th><th>YoY</th></tr></thead><tbody>${rows.map(r => `<tr><td>${esc(r.label)}</td><td class="num">${fmtNum(n(r.current))}</td><td class="num">${delta(n(r.current), n(r.previous))}</td><td class="num">${delta(n(r.current), n(r.year_ago))}</td></tr>`).join("")}</tbody></table>` : `<p>A filing-verified result comparison is not ready for this company. Open its exchange filings below to inspect the reported figures.</p>`;
  const resultContext = verified ? `<p class="insight">${esc(evidence.results.insight || "")}</p><p class="source-note">${esc(evidence.results.basis || "")}${evidence.results.calculation_note ? ". " + esc(evidence.results.calculation_note) : ""}</p><div class="sources-inline">${(evidence.results.sources || []).map(x => `<a href="${esc(safeUrl(x.url))}" target="_blank" rel="noopener noreferrer">${esc(x.label)}</a>`).join("")}</div>` : "";
  const promise = evidence.promise?.length ? evidence.promise.map(x => {
    const laterLink = x.actual_source ? `<div class="sources-inline"><a href="${esc(safeUrl(x.actual_source.url))}" target="_blank" rel="noopener noreferrer">${esc(x.actual_source.label)}</a></div>` : (evidence.results?.sources?.[0] ? `<div class="sources-inline"><a href="${esc(safeUrl(evidence.results.sources[0].url))}" target="_blank" rel="noopener noreferrer">${esc(evidence.results.sources[0].label)}</a></div>` : "");
    const statementLink = x.source ? `<div class="sources-inline"><a href="${esc(safeUrl(x.source.url))}" target="_blank" rel="noopener noreferrer">${esc(x.source.label)}</a></div>` : "";
    const verdictKey = (x.verdict || "pending").toLowerCase();
    const meta = [x.period, x.metric].filter(Boolean).map(esc).join(" · ");
    return `<div class="promise-ledger">${verdictChip(verdictKey, x.status)}<blockquote class="promise-quote">${esc(x.statement)}</blockquote>${meta ? `<p class="promise-quote-meta">${meta}</p>` : ""}${statementLink}<div class="promise-outcome"><h4>Later disclosure check</h4><p>${esc(x.check)}</p>${laterLink}</div></div>`;
  }).join("") : `<p>No statement has a verified outcome comparison yet. You can inspect candidate transcript statements.</p><button id="extract-claims" type="button" class="text-button" data-symbol="${esc(data.symbol)}">Find transcript statements</button><div id="claim-results"></div>`;
  const people = evidence.people?.length ? `<section class="research-section"><h3>People</h3>${evidence.people.map(x => `<div class="story-detail"><strong>${esc(x.name)}</strong><p>${esc(x.change)}</p>${x.bio ? `<p>${esc(x.bio)}</p>` : ""}${x.source ? `<div class="sources-inline"><a href="${esc(safeUrl(x.source.url))}" target="_blank" rel="noopener noreferrer">${esc(x.source.label)}</a></div>` : ""}</div>`).join("")}</section>` : "";
  const exchangeDocs = (state.digest?.filings || []).filter(x => x.symbol === data.symbol && safeUrl(x.source_url) !== "#")
    .sort((a, b) => Date.parse(b.published_at) - Date.parse(a.published_at)).slice(0, 12)
    .map(x => ({ label: `${date(x.published_at)}: ${filingTitle(x)}`, url: x.source_url }));
  byId("research-result").innerHTML = `<div class="company-heading"><div><h2>${esc(data.company)}</h2><p>${esc(data.symbol)}: documents indexed ${esc(date(data.fetched_at))}</p></div><a class="text-link" href="${esc(safeUrl(data.source_page))}" target="_blank" rel="noopener noreferrer">Document index</a></div>
    <section class="research-section"><div class="section-eyeline"><h3>Quarterly results</h3><span>${esc(evidence.results?.period || "Not yet verified")}</span></div>${results}${resultContext}</section>
    <section class="research-section"><h3>What management said</h3>${promise}</section>${people}
    <section class="research-section"><h3>Source library</h3><p>Open the original documents when you need detail.</p>${documentGroup("Recent exchange filings", exchangeDocs.length ? exchangeDocs : data.recent_filings)}${documentGroup("Annual reports", data.annual_reports)}${documentGroup("Earnings-call transcripts", data.transcripts)}</section>`;
  byId("extract-claims")?.addEventListener("click", () => loadClaims(data.symbol));
}
async function loadClaims(symbol) {
  const target = byId("claim-results");
  target.innerHTML = "<p>Reading transcript PDFs…</p>";
  try {
    const r = await fetch(`/api/claims/${encodeURIComponent(symbol)}`);
    const data = await r.json();
    if (!r.ok) throw Error(data.detail || "Transcript extraction failed");
    target.innerHTML = data.claims?.length ? data.claims.map(x => `<div class="story-detail"><span class="status">Outcome unverified</span><p>“${esc(x.quote)}”</p><div class="sources-inline"><a href="${esc(safeUrl(`${x.source_url}#page=${x.page}`))}" target="_blank" rel="noopener noreferrer">${esc(x.document)}, page ${esc(x.page)}</a></div></div>`).join("") : "<p>No quantitative statements could be extracted. Open the transcripts below.</p>";
    byId("extract-claims").remove();
  } catch (error) { target.innerHTML = `<p>${esc(error.message)}. Try the document links below.</p>`; }
}
async function loadResearch(raw) {
  const symbol = raw.trim().toUpperCase();
  if (!/^[A-Z0-9&-]{1,20}$/.test(symbol)) {
    byId("research-result").innerHTML = `<div class="empty-state"><strong>Enter a valid NSE ticker.</strong></div>`;
    return;
  }
  byId("ticker-input").value = symbol;
  byId("research-result").innerHTML = `<div class="skeleton-lead" aria-busy="true" aria-label="Loading ${esc(symbol)}"><span class="sk-tag"></span><span class="sk-headline"></span><span class="sk-line"></span><span class="sk-line sk-line-2"></span><span class="sk-line sk-line-3"></span></div>`;
  try {
    const [r, e] = await Promise.all([fetch(`/api/research/${encodeURIComponent(symbol)}`), fetch(`/api/evidence/${encodeURIComponent(symbol)}`)]);
    const data = await r.json(), evidence = await e.json();
    if (!r.ok) throw Error(data.detail || "Research unavailable");
    if (!e.ok) throw Error(evidence.detail || "Evidence unavailable");
    renderResearch(data, evidence);
  } catch (error) {
    byId("research-result").innerHTML = `<div class="empty-state"><strong>Could not load ${esc(symbol)}.</strong><p>${esc(error.message)} Try again or choose another ticker.</p></div>`;
  }
}
function signalMatches() {
  if (!state.digest) return [];
  const matches = [];
  const cutoff = Date.parse(state.digest.generated_at) - 7 * 86400000;
  for (const [symbol, p] of Object.entries(state.digest.prices || {})) {
    if (Date.parse(`${p.as_of}T23:59:59+05:30`) < cutoff) continue;
    if (Math.abs(p.move_pct) >= state.rules.price) matches.push({ text: `${symbol} moved ${p.move_pct > 0 ? "+" : ""}${p.move_pct}%`, detail: `${p.as_of} close; threshold ±${state.rules.price}%` });
    if (p.volume_ratio >= state.rules.volume) matches.push({ text: `${symbol} volume reached ${p.volume_ratio}× its 20-day average`, detail: `${p.as_of} close; threshold ${state.rules.volume}×` });
  }
  for (const item of distinct(state.digest.filings.filter(x => Date.parse(x.published_at) >= cutoff && state.rules.categories.includes(x.category)))) {
    matches.push({ text: `${item.symbol} filed ${categories[item.category] || "an update"}`, detail: `${date(item.published_at)}: ${filingTitle(item)}` });
  }
  return matches;
}
function renderSignals() {
  if (!state.digest) return;
  const matches = signalMatches();
  byId("match-count").textContent = `${matches.length} matches`;
  const visible = state.allMatches ? matches : matches.slice(0, 5);
  byId("matches-list").innerHTML = visible.length ? visible.map(x => `<div class="match-item"><strong>${esc(x.text)}</strong><span>${esc(x.detail)}</span></div>`).join("") : `<div class="empty-state"><strong>No current matches.</strong><p>Try a lower threshold or another filing type.</p></div>`;
  byId("all-matches").hidden = matches.length <= 5;
  byId("all-matches").textContent = state.allMatches ? "Show fewer matches" : `Show all ${matches.length} matches`;
}
function setupSignals() {
  const price = byId("price-threshold"), volume = byId("volume-threshold");
  price.value = state.rules.price; volume.value = state.rules.volume;
  function update() {
    state.rules.price = Number(price.value); state.rules.volume = Number(volume.value);
    byId("price-value").textContent = `±${state.rules.price}%`;
    byId("volume-value").textContent = `${state.rules.volume}×`;
    localStorage.setItem("finn-rules", JSON.stringify(state.rules));
    renderSignals();
  }
  price.addEventListener("input", update); volume.addEventListener("input", update);
  byId("category-options").innerHTML = ["results", "m&a", "management_change", "litigation", "fund_raise", "credit_rating", "capex", "dividend"].map(key => `<label><input type="checkbox" value="${esc(key)}" ${state.rules.categories.includes(key) ? "checked" : ""}>${esc(categories[key])}</label>`).join("");
  byId("category-options").addEventListener("change", () => {
    state.rules.categories = [...byId("category-options").querySelectorAll("input:checked")].map(x => x.value);
    localStorage.setItem("finn-rules", JSON.stringify(state.rules)); renderSignals();
  });
  update();
}
function currentTheme() {
  const saved = localStorage.getItem("finn-theme");
  return saved === "dark" ? "dark" : "light";
}
function applyTheme(theme) {
  document.documentElement.setAttribute("data-theme", theme);
  const toggle = byId("theme-toggle");
  if (!toggle) return;
  const next = theme === "dark" ? "light" : "dark";
  toggle.setAttribute("aria-label", `Switch to ${next} theme`);
  toggle.title = `Switch to ${next} theme`;
  toggle.querySelector('[data-theme-icon="light"]').hidden = theme === "dark";
  toggle.querySelector('[data-theme-icon="dark"]').hidden = theme !== "dark";
}
function setupTheme() {
  applyTheme(currentTheme());
  byId("theme-toggle")?.addEventListener("click", () => {
    const next = currentTheme() === "dark" ? "light" : "dark";
    localStorage.setItem("finn-theme", next);
    applyTheme(next);
  });
}
async function init() {
  setupTheme();
  document.addEventListener("click", e => {
    const nav = e.target.closest("[data-view]");
    if (nav) { e.preventDefault(); switchView(nav.dataset.view); return; }
    const research = e.target.closest("[data-research]");
    if (research) { switchView("research"); loadResearch(research.dataset.research); return; }
    const ticker = e.target.closest("[data-ticker]");
    if (ticker) { loadResearch(ticker.dataset.ticker); return; }
    const review = e.target.closest("[data-review]");
    if (review) {
      state.seen.has(review.dataset.review) ? state.seen.delete(review.dataset.review) : state.seen.add(review.dataset.review);
      localStorage.setItem("finn-seen", JSON.stringify([...state.seen])); renderBrief(); return;
    }
  });
  window.addEventListener("popstate", () => {
    const name = location.hash.slice(1);
    switchView(["brief", "archive", "research", "signals"].includes(name) ? name : "brief", true, false);
  });
  byId("archive-search").addEventListener("input", e => { state.search = e.target.value; state.archivePage = 1; renderArchive(); });
  byId("archive-company").addEventListener("change", e => { state.company = e.target.value; state.archivePage = 1; renderArchive(); });
  byId("show-routine").addEventListener("change", e => { state.showRoutine = e.target.checked; state.archivePage = 1; renderArchive(); });
  document.querySelectorAll("[data-days]").forEach(button => button.addEventListener("click", () => {
    state.days = button.dataset.days === "all" ? "all" : Number(button.dataset.days); state.archivePage = 1;
    renderArchive();
  }));
  document.addEventListener("click", e => {
    const button = e.target.closest("[data-brief-days]");
    if (button) { state.briefDays = Number(button.dataset.briefDays); state.allBriefEvents = false; renderBrief(); }
  });
  byId("brief-show-all").addEventListener("click", () => { state.allBriefEvents = !state.allBriefEvents; renderBrief(); });
  byId("load-more").addEventListener("click", () => { state.archivePage++; renderArchive(); });
  byId("all-matches").addEventListener("click", () => { state.allMatches = !state.allMatches; renderSignals(); });
  byId("research-form").addEventListener("submit", e => { e.preventDefault(); loadResearch(byId("ticker-input").value); });
  setupSignals();
  try {
    const r = await fetch("/api/digest");
    if (!r.ok) throw Error("Snapshot unavailable");
    state.digest = await r.json();
    byId("header-status").textContent = `Snapshot ${date(state.digest.generated_at, true)}`;
    byId("footer-updated").textContent = date(state.digest.generated_at, true);
    byId("footer-updated").dateTime = state.digest.generated_at || "";
    byId("archive-company").innerHTML = `<option value="all">All companies</option>` + (state.digest.portfolio || []).map(x => `<option value="${esc(x.symbol)}">${esc(x.symbol)}</option>`).join("");
    renderBrief(); renderArchive(); renderSignals();
  } catch (error) {
    byId("header-status").textContent = "Snapshot unavailable";
    byId("brief-copy").textContent = "The saved filing snapshot could not be loaded.";
    byId("lead-story").innerHTML = `<div class="empty-state"><strong>Could not load the brief.</strong><p>${esc(error.message)} Refresh the page or rebuild the snapshot.</p></div>`;
    byId("archive-list").innerHTML = `<div class="empty-state"><strong>Filings are unavailable.</strong><p>Refresh the page or rebuild the snapshot.</p></div>`;
    byId("matches-list").innerHTML = `<div class="empty-state"><strong>Match preview is unavailable.</strong><p>Load a filing snapshot to check your rules.</p></div>`;
  }
  const initial = location.hash.slice(1);
  if (["brief", "archive", "research", "signals"].includes(initial)) switchView(initial, false, false);
}
init();

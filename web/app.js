const state = { digest: null, hours: 168, company: "all", research: null, rules: loadRules() };
const categoryLabels = { results: "Results", "m&a": "M&A", management_change: "Management", litigation: "Litigation", fund_raise: "Fund raise", capex: "Capex", credit_rating: "Credit rating", pledging: "Pledging", earnings_call: "Earnings call", press_release: "Press release", dividend: "Dividend", other: "Other", routine: "Routine" };

function loadRules() {
  try { return { price: 3, volume: 2, categories: ["results", "m&a", "management_change"], ...JSON.parse(localStorage.getItem("finn-rules") || "{}") }; }
  catch { return { price: 3, volume: 2, categories: ["results", "m&a", "management_change"] }; }
}
function saveRules() { localStorage.setItem("finn-rules", JSON.stringify(state.rules)); renderAlerts(); }
function esc(value) { return String(value ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c])); }
function safeUrl(value) { try { const url = new URL(value); return ["https:", "http:"].includes(url.protocol) ? url.href : "#"; } catch { return "#"; } }
function dateLabel(value) { const d = new Date(value); return Number.isNaN(d.getTime()) ? "Date unavailable" : d.toLocaleString("en-IN", { day: "numeric", month: "short", hour: "numeric", minute: "2-digit", timeZone: "Asia/Kolkata" }); }
function sinceCutoff() { return Date.now() - state.hours * 3600000; }
function visibleFilings() { return (state.digest?.filings || []).filter(x => Date.parse(x.published_at) >= sinceCutoff() && (state.company === "all" || x.symbol === state.company)); }
function setView(view) {
  document.querySelectorAll(".view").forEach(el => el.classList.toggle("active", el.id === `view-${view}`));
  document.querySelectorAll("[data-view]").forEach(el => el.classList.toggle("active", el.dataset.view === view));
  document.getElementById("top-section").textContent = ({ today: "TODAY", research: "RESEARCH", rules: "MY SIGNALS" })[view];
  window.scrollTo({ top: 0, behavior: "smooth" });
}
function filingCard(item) {
  const category = categoryLabels[item.category] || "Filing";
  return `<article class="filing ${esc(item.tier)}"><div class="filing-main"><div class="filing-top"><span class="ticker">${esc(item.symbol)} <span style="color:#a0aea7;font-weight:500">/ ${esc(item.company)}</span></span><span class="filing-time">${esc(dateLabel(item.published_at))}</span></div><h3>${esc(item.headline)}</h3><p class="filing-summary">${esc(item.summary)}</p><div class="filing-meta"><span class="tag ${esc(item.tier)}">${esc(item.tier === "act" ? "Priority" : item.tier === "note" ? "Worth a look" : "Routine")}</span><span class="score">${esc(item.reason || category)} · priority ${esc(item.score)}</span><button class="explore-button" data-explore="${esc(item.symbol)}">EXPLORE ↗</button>${item.source_url ? `<a class="source-link" href="${esc(safeUrl(item.source_url))}" target="_blank" rel="noopener noreferrer" aria-label="Open source filing for ${esc(item.symbol)}">VIEW FILING ↗</a>` : ""}</div></div></article>`;
}
function renderFeed() {
  if (!state.digest) return;
  const items = visibleFilings(), material = items.filter(x => x.tier !== "routine"), routine = items.filter(x => x.tier === "routine");
  document.getElementById("filing-count").textContent = `${items.length} filings`;
  document.getElementById("brief-heading").textContent = items.length ? `${material.length} items to review. ${routine.length} routine.` : "No filings in this window.";
  document.getElementById("brief-subtitle").textContent = `${state.company === "all" ? `${state.digest.portfolio.length} companies` : state.company} · ${state.hours === 24 ? "last 24 hours" : state.hours === 72 ? "last 3 days" : "last 7 days"} · updated ${dateLabel(state.digest.generated_at)}`;
  const markup = material.map(filingCard).join("") + (routine.length ? `<details class="routine-group"><summary>+ ${routine.length} routine filing${routine.length === 1 ? "" : "s"} · tap to review</summary>${routine.map(filingCard).join("")}</details>` : "");
  document.getElementById("feed").innerHTML = markup || `<div class="empty">No filings in this time window. Try a wider period or another company.</div>`;
  renderAlerts();
}
function renderAlerts() {
  if (!state.digest) return;
  const alerts = [];
  const freshSymbols = new Set();
  const prices = state.digest.prices || {};
  Object.entries(prices).forEach(([symbol, price]) => {
    if (state.company !== "all" && symbol !== state.company) return;
    if (Date.parse(`${price.as_of}T23:59:59+05:30`) < sinceCutoff()) return;
    if (Math.abs(price.move_pct) >= state.rules.price) { alerts.push(`${symbol} moved ${price.move_pct > 0 ? "+" : ""}${price.move_pct}% on ${price.as_of}`); freshSymbols.add(symbol); }
    if (price.volume_ratio >= state.rules.volume) alerts.push(`${symbol} volume was ${price.volume_ratio}× its 20-day average on ${price.as_of}`);
  });
  visibleFilings().filter(x => state.rules.categories.includes(x.category)).slice(0, 3).forEach(x => alerts.push(`${x.symbol}: ${categoryLabels[x.category] || "Filing"} filed ${dateLabel(x.published_at)}`));
  document.getElementById("alerts").innerHTML = alerts.length ? alerts.slice(0, 3).map((x, i) => `<div class="alert-line"><b>${i === 0 ? "SIGNAL" : "·"}</b><span>${esc(x)}</span></div>`).join("") : "";
}
function populatePortfolio() {
  const select = document.getElementById("company-filter");
  select.innerHTML = `<option value="all">All companies</option>` + (state.digest.portfolio || []).map(x => `<option value="${esc(x.symbol)}">${esc(x.symbol)}</option>`).join("");
}
function parseNumber(raw) { const n = Number(String(raw || "").replace(/[,₹%]/g, "")); return Number.isFinite(n) ? n : null; }
function delta(current, past) { const a = parseNumber(current), b = parseNumber(past); if (a === null || b === null || b === 0) return "—"; const n = (a / b - 1) * 100; return `<span class="${n >= 0 ? "positive" : "negative"}">${n >= 0 ? "+" : ""}${n.toFixed(1)}%</span>`; }
function docList(items, empty) { return items?.length ? `<div class="doc-list">${items.map(x => `<a class="doc-link" target="_blank" rel="noopener noreferrer" href="${esc(safeUrl(x.url))}"><span>${esc(x.label)}</span><b>↗</b></a>`).join("")}</div>` : `<p class="doc-empty">${esc(empty)}</p>`; }
function renderResearch(data) {
  const labels = { revenue: "Revenue", ebitda_proxy: "Operating profit*", pbt: "PBT", pat: "PAT" };
  const values = data.quarters?.values || {};
  const rows = Object.entries(labels).filter(([key]) => values[key]).map(([key, label]) => { const v = values[key]; return `<tr><td>${label}</td><td>${esc(v.current)}</td><td>${delta(v.current, v.previous)}</td><td>${delta(v.current, v.year_ago)}</td></tr>`; }).join("");
  document.getElementById("research-result").innerHTML = `<div class="research-header"><div><p class="eyebrow">COMPANY FILE / ${esc(data.symbol)}</p><h2>${esc(data.company)}</h2><p>Document trail and quarterly context · fetched ${esc(dateLabel(data.fetched_at))}</p></div><a href="${esc(safeUrl(data.source_page))}" target="_blank" rel="noopener noreferrer">OPEN COMPANY PAGE ↗</a></div><div class="research-block"><div class="block-heading"><h3>Quarterly numbers</h3><span>${esc(data.quarters?.quarter || "Latest")}</span></div>${rows ? `<div style="overflow:auto"><table class="result-table"><thead><tr><th>₹ crore</th><th>Latest</th><th>QoQ</th><th>YoY</th></tr></thead><tbody>${rows}</tbody></table></div>` : `<p class="doc-empty">No quarterly table available for this company.</p>`}<p class="research-note">${esc(data.quarters?.source_note || "Figures require checking against the linked company filing.")} *Operating profit is a proxy, not a reported EBITDA figure.</p></div><div class="research-block"><div class="block-heading"><h3>Annual reports</h3><span>PRIMARY SOURCE</span></div>${docList(data.annual_reports, "No annual report links found.")}</div><div class="research-block"><div class="block-heading"><h3>Management in their words</h3><span>EARNINGS CALLS</span></div><p class="research-note" style="margin:0 0 15px">Open the transcripts to test what management said against subsequent results. FINN does not assign a delivered or missed label without matching the statement to a cited outcome.</p>${docList(data.transcripts, "No transcript links found on this page.")}</div><div class="research-block"><div class="block-heading"><h3>Latest source trail</h3><span>COMPANY FILINGS</span></div>${docList(data.recent_filings, "No recent document links found.")}</div>`;
  document.getElementById("research-result").insertAdjacentHTML("beforeend", `<div class="research-block"><div class="block-heading"><h3>Guidance ledger</h3><span>TRANSCRIPT EVIDENCE</span></div><p class="research-note" style="margin:0 0 15px">Pull quantitative, forward-looking sentences from the original call PDFs. Each links to its source page. Verify the speaker and compare the outcome with a later filing.</p><button class="claim-button" id="load-claims" data-symbol="${esc(data.symbol)}">EXTRACT STATEMENTS ↗</button><div id="claims-list"></div></div>`);
  document.getElementById("load-claims").addEventListener("click", () => loadClaims(data.symbol));
}
async function loadClaims(symbol) {
  const target = document.getElementById("claims-list");
  target.innerHTML = `<p class="research-note">Reading up to four transcript PDFs…</p>`;
  try {
    const response = await fetch(`/api/claims/${encodeURIComponent(symbol)}`);
    const result = await response.json();
    if (!response.ok) throw Error(result.detail || "Transcript extraction failed");
    target.innerHTML = result.claims.length ? result.claims.map(x => `<div class="claim"><p>“${esc(x.quote)}”</p><a href="${esc(safeUrl(x.source_url))}#page=${esc(x.page)}" target="_blank" rel="noopener noreferrer">${esc(x.document)} · page ${esc(x.page)} ↗</a><span>OUTCOME TO VERIFY</span></div>`).join("") : `<p class="doc-empty">No quantitative guidance statements could be extracted from the linked PDFs.</p>`;
    document.getElementById("load-claims").remove();
  } catch (error) { target.innerHTML = `<p class="doc-empty">${esc(error.message)}. Open the transcripts above to inspect them directly.</p>`; }
}
async function loadResearch(symbol) {
  const target = symbol.trim().toUpperCase();
  if (!/^[A-Z0-9&-]{1,20}$/.test(target)) { document.getElementById("research-result").innerHTML = `<div class="empty">Enter an NSE ticker using letters and numbers.</div>`; return; }
  document.getElementById("ticker-input").value = target;
  document.getElementById("research-result").innerHTML = `<div class="loading">Reading ${esc(target)} documents…</div>`;
  try { const response = await fetch(`/api/research/${encodeURIComponent(target)}`); const data = await response.json(); if (!response.ok) throw Error(data.detail || "Research unavailable"); renderResearch(data); }
  catch (error) { document.getElementById("research-result").innerHTML = `<div class="empty">${esc(error.message)} Try another ticker or refresh the page.</div>`; }
}
function initRules() {
  const price = document.getElementById("price-threshold"), volume = document.getElementById("volume-threshold");
  price.value = state.rules.price; volume.value = state.rules.volume;
  function update() { state.rules.price = Number(price.value); state.rules.volume = Number(volume.value); document.getElementById("price-value").textContent = `±${state.rules.price}%`; document.getElementById("volume-value").textContent = `${state.rules.volume}×`; saveRules(); }
  price.addEventListener("input", update); volume.addEventListener("input", update); update();
  const categories = ["results", "m&a", "management_change", "litigation", "fund_raise", "credit_rating", "capex"];
  document.getElementById("category-options").innerHTML = categories.map(x => `<label><input type="checkbox" value="${x}" ${state.rules.categories.includes(x) ? "checked" : ""}>${esc(categoryLabels[x])}</label>`).join("");
  document.getElementById("category-options").addEventListener("change", () => { state.rules.categories = [...document.querySelectorAll("#category-options input:checked")].map(x => x.value); saveRules(); });
}
async function init() {
  document.querySelectorAll("[data-view]").forEach(x => x.addEventListener("click", () => setView(x.dataset.view)));
  document.querySelectorAll("[data-hours]").forEach(x => x.addEventListener("click", () => { state.hours = Number(x.dataset.hours); document.querySelectorAll("[data-hours]").forEach(y => y.classList.toggle("selected", y === x)); renderFeed(); }));
  document.getElementById("company-filter").addEventListener("change", e => { state.company = e.target.value; renderFeed(); });
  document.getElementById("feed").addEventListener("click", e => { const button = e.target.closest("[data-explore]"); if (button) { setView("research"); loadResearch(button.dataset.explore); } });
  document.getElementById("research-form").addEventListener("submit", e => { e.preventDefault(); loadResearch(document.getElementById("ticker-input").value); });
  document.querySelectorAll("[data-ticker]").forEach(x => x.addEventListener("click", () => loadResearch(x.dataset.ticker)));
  initRules();
  try { const response = await fetch("/api/digest"); if (!response.ok) throw Error("Digest unavailable"); state.digest = await response.json(); populatePortfolio(); document.getElementById("cache-date").textContent = state.digest.generated_at ? `Snapshot ${dateLabel(state.digest.generated_at)}` : "No snapshot yet"; renderFeed(); }
  catch (error) { document.getElementById("feed").innerHTML = `<div class="empty">${esc(error.message)}. Refresh the page.</div>`; }
}
init();

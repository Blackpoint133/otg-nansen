"use strict";

const LAGS = [0, 1, 6, 24];
const OUTCOMES = [
  ["market_trade_tx_count", "Trades"],
  ["market_native_gun_amount_truncated", "Native GUN volume"],
  ["market_unique_buyers", "Unique buyers"],
];
let historyData = null;
let liveRequestRunning = false;

function node(tag, className, text) {
  const element = document.createElement(tag);
  if (className) element.className = className;
  if (text !== undefined) element.textContent = text;
  return element;
}

function finiteText(value, digits = 4) {
  if (value === null || value === undefined || !Number.isFinite(Number(value))) return "n/a";
  return Number(value).toFixed(digits);
}

function formatPercent(value) {
  if (value === null || value === undefined || !Number.isFinite(Number(value))) return "n/a";
  const n = Number(value) * 100;
  return `${n > 0 ? "+" : ""}${n.toFixed(2)}%`;
}

function formatTime(value) {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.valueOf())) return "—";
  return `${date.toISOString().slice(0, 16).replace("T", " ")} UTC`;
}

function renderRelationships(rows) {
  const host = document.getElementById("relationship-table");
  host.replaceChildren();
  const table = node("table", "relationship-table");
  const head = node("thead");
  const header = node("tr");
  header.append(node("th", "row-label", "Outcome"));
  for (const lag of LAGS) header.append(node("th", "", `${lag}h`));
  head.append(header);
  const body = node("tbody");
  for (const [key, label] of OUTCOMES) {
    const tr = node("tr");
    tr.append(node("th", "row-label", label));
    for (const lag of LAGS) {
      const row = rows.find((item) => item.outcome === key && item.lag_hours === lag);
      const value = row ? row.spearman_rho : null;
      const td = node("td", value === null ? "null-value" : (value >= 0 ? "positive" : "negative"), value === null ? "NULL" : finiteText(value, 3));
      td.title = "Full-sample Spearman rho from the preregistered Task 034 analysis";
      tr.append(td);
    }
    body.append(tr);
  }
  table.append(head, body);
  host.append(table);
  host.append(node("p", "micro-note", "Fixed lags: Nansen observation at t−k, OTG outcome at t. All four lags are retained."));
}

function renderEvents(rows, direction = null) {
  const host = document.getElementById("event-summary");
  host.replaceChildren();
  const visibleDirections = direction ? [direction] : ["positive", "negative"];
  document.getElementById("event-selection").textContent = direction ? `Selected: ${direction} shocks` : "Both directions · neutral";
  const grid = node("div", "event-grid");
  const selectedRows = rows.filter((row) => visibleDirections.includes(row.direction));
  for (const [outcome, label] of OUTCOMES) {
    const group = node("section", "event-outcome");
    group.append(node("h3", "", label));
    for (const dir of visibleDirections) {
      const dirRows = selectedRows.filter((row) => row.outcome === outcome && row.direction === dir);
      if (!dirRows.length) continue;
      const strip = node("div", `event-strip ${dir}`);
      strip.append(node("span", "event-direction", dir === "positive" ? "UP" : "DOWN"));
      for (const horizon of LAGS) {
        const item = dirRows.find((row) => row.horizon_hours === horizon);
        const cell = node("div", "event-cell");
        cell.append(node("small", "", `${horizon}h`));
        cell.append(node("strong", "", item ? finiteText(item.median_response, 3) : "n/a"));
        if (item) cell.title = `Median ${item.median_response}; ${item.event_count} events; descriptive bootstrap interval in committed artifact`;
        strip.append(cell);
      }
      group.append(strip);
    }
    grid.append(group);
  }
  host.append(grid);
}

async function loadHistory() {
  const error = document.getElementById("history-error");
  try {
    const response = await fetch("/api/history", { headers: { Accept: "application/json" } });
    const body = await response.json();
    if (!response.ok || body.status !== "success" || body.relationship_rows.length !== 12 || body.event_rows.length !== 24) throw new Error("history contract");
    historyData = body;
    renderRelationships(body.relationship_rows);
    renderEvents(body.event_rows);
    document.getElementById("q05").textContent = formatPercent(body.q05_historical_threshold);
    document.getElementById("q95").textContent = formatPercent(body.q95_historical_threshold);
    error.hidden = true;
  } catch (_) {
    error.hidden = false;
    document.getElementById("relationship-table").replaceChildren(node("p", "error-text", "Historical relationship data is unavailable."));
    document.getElementById("event-summary").replaceChildren(node("p", "error-text", "Historical event data is unavailable."));
  }
}

function renderLive(data) {
  const success = data.status === "success";
  const badge = document.getElementById("fetch-badge");
  badge.textContent = success ? data.fetch_mode : "UNAVAILABLE";
  badge.className = `state-badge ${success ? (data.fetch_mode === "CACHED" ? "state-cached" : "state-live") : "state-error"}`;
  document.getElementById("live-error").hidden = success;
  if (!success) {
    document.getElementById("live-error").textContent = `Live Nansen data unavailable (${data.error_code || "LIVE_DATA_UNAVAILABLE"}). Historical analysis remains visible.`;
    document.getElementById("bucket-time").textContent = "—";
    document.getElementById("live-price").textContent = "—";
    document.getElementById("live-return").textContent = "—";
    document.getElementById("live-imbalance").textContent = "—";
    document.getElementById("fetch-time").textContent = "No current live observation is available.";
    document.getElementById("decision-card").dataset.regime = "LIVE_RETURN_UNAVAILABLE";
    document.getElementById("decision-text").textContent = "Live observation unavailable";
    document.getElementById("decision-caption").textContent = "No historical event group is selected when live data is unavailable.";
    if (historyData) renderEvents(historyData.event_rows);
    return;
  }
  document.getElementById("bucket-time").textContent = formatTime(data.latest_bucket_start_utc);
  document.getElementById("live-price").textContent = data.latest_price_usd === null ? "n/a" : `$${Number(data.latest_price_usd).toPrecision(6)}`;
  document.getElementById("live-return").textContent = formatPercent(data.price_return_1h);
  document.getElementById("live-imbalance").textContent = formatPercent(data.flow_imbalance_share);
  document.getElementById("fetch-time").textContent = `${data.fetch_mode} · fetched ${formatTime(data.fetched_at_utc)} · ${data.complete_hourly_bucket_count} complete hourly buckets`;
  const decision = document.getElementById("decision-card");
  decision.dataset.regime = data.current_regime;
  document.getElementById("decision-text").textContent = data.decision_message;
  document.getElementById("decision-caption").textContent = data.current_regime === "LIVE_RETURN_UNAVAILABLE"
    ? "No event group is selected when the live return cannot be calculated."
    : `Live 1h return ${formatPercent(data.price_return_1h)} is compared with the committed Task 034 historical thresholds.`;
  if (historyData && data.current_regime === "POSITIVE_SHOCK_RANGE") renderEvents(historyData.event_rows, "positive");
  else if (historyData && data.current_regime === "NEGATIVE_SHOCK_RANGE") renderEvents(historyData.event_rows, "negative");
  else if (historyData) renderEvents(historyData.event_rows);
}

async function refreshLive() {
  if (liveRequestRunning) return;
  liveRequestRunning = true;
  const button = document.getElementById("refresh-button");
  button.disabled = true;
  button.textContent = "Requesting…";
  try {
    const response = await fetch("/api/live-gun", { headers: { Accept: "application/json" }, cache: "no-store" });
    const body = await response.json();
    renderLive(body);
  } catch (_) {
    renderLive({ status: "error", error_code: "LOCAL_DEMO_REQUEST_FAILED" });
  } finally {
    button.disabled = false;
    button.innerHTML = 'Refresh Live Data <span aria-hidden="true">↗</span>';
    liveRequestRunning = false;
  }
}

document.getElementById("refresh-button").addEventListener("click", refreshLive);
loadHistory();

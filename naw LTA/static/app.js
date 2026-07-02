const page = document.body.dataset.page;
const symbols = ["BTCUSD", "ETHUSD", "XAUUSD", "XAGUSD", "US30", "US100"];
let workerEnabled = false;
let selectedSymbol = null;
let latestScans = [];
let activeRunId = null;

const $ = (selector, root = document) => root.querySelector(selector);
const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];
const esc = (value) => String(value ?? "").replace(/[&<>'"]/g, (char) => ({"&":"&amp;","<":"&lt;",">":"&gt;","'":"&#39;",'"':"&quot;"}[char]));
const money = (value) => `${Number(value || 0) < 0 ? "-" : ""}$${Math.abs(Number(value || 0)).toFixed(2)}`;
const number = (value, digits = 2) => value == null ? "--" : Number(value).toLocaleString(undefined, {maximumFractionDigits: digits});
const dateTime = (value) => value ? new Date(value).toLocaleString() : "--";

async function api(path, options = {}) {
  const response = await fetch(path, {headers: {"Content-Type": "application/json", ...(options.headers || {})}, ...options});
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.detail || data.error || `Request failed (${response.status})`);
  return data;
}

function toast(message, tone = "normal") {
  const node = $("#toast");
  node.textContent = message;
  node.className = `pointer-events-none fixed bottom-5 right-5 z-50 max-w-sm border px-4 py-3 text-sm shadow-2xl ${tone === "error" ? "border-loss bg-[#2b0d15] text-rose-200" : "border-line bg-ink-800 text-slate-100"}`;
  setTimeout(() => node.classList.add("hidden"), 4000);
}

async function refreshWorker() {
  try {
    const state = await api("/api/worker");
    workerEnabled = state.enabled;
    const status = $("#worker-status");
    const button = $("#worker-toggle");
    const workerTone = state.status === "error" ? "!bg-loss" : state.enabled ? "!bg-signal" : "";
    status.innerHTML = `<span class="dot ${workerTone}"></span><span>${esc(state.enabled ? `Worker ${state.status}` : "Worker stopped")}</span>`;
    button.textContent = window.innerWidth < 500
      ? (state.enabled ? "Stop" : "Start")
      : (state.enabled ? "Stop worker" : "Start worker");
    button.className = state.enabled ? "btn btn-danger" : "btn btn-primary";
    if (state.error && page !== "config") toast(state.error, "error");
  } catch (error) {
    $("#worker-status").innerHTML = `<span class="dot !bg-loss"></span><span>API unavailable</span>`;
  }
}

$("#worker-toggle")?.addEventListener("click", async () => {
  const button = $("#worker-toggle");
  button.disabled = true;
  try {
    await api(`/api/worker/${workerEnabled ? "stop" : "start"}`, {method: "POST"});
    toast(workerEnabled ? "Worker stopped." : "Worker started. First scan queued.");
    await refreshWorker();
  } catch (error) { toast(error.message, "error"); }
  finally { button.disabled = false; }
});

function tone(value) {
  if (value === "BUY" || value === "A_PLUS" || value === "OPEN" || value === "complete") return "text-signal border-signal/40 bg-[#0b211b]";
  if (value === "SELL" || value === "error" || value === "CLOSED") return "text-loss border-loss/40 bg-[#250d14]";
  return "text-muted border-line bg-ink-800";
}

async function loadDashboard() {
  const data = await api("/api/dashboard");
  Object.entries(data.summary).forEach(([key, value]) => {
    const node = $(`[data-metric="${key}"]`);
    if (!node) return;
    node.textContent = key.includes("pnl") ? money(value) : value;
    if (key.includes("pnl")) node.className = `value ${Number(value) >= 0 ? "text-signal" : "text-loss"}`;
  });
  latestScans = data.scans;
  if (!selectedSymbol && latestScans.length) selectedSymbol = latestScans[0].symbol;
  renderSymbolTabs();
  renderDashboardScan();
  renderOrders(data.orders);
}

function renderSymbolTabs() {
  const host = $("#symbol-tabs");
  if (!host) return;
  host.innerHTML = latestScans.map((scan) => `<button type="button" data-symbol="${esc(scan.symbol)}" class="btn !min-h-8 !px-2 ${scan.symbol === selectedSymbol ? "!border-signal !text-signal" : ""}">${esc(scan.symbol)}</button>`).join("");
  $$('[data-symbol]', host).forEach((button) => button.addEventListener("click", () => {
    selectedSymbol = button.dataset.symbol;
    renderSymbolTabs();
    renderDashboardScan();
  }));
}

function renderDashboardScan() {
  const scan = latestScans.find((item) => item.symbol === selectedSymbol);
  if (!scan) return;
  const payload = scan.payload || {};
  $("#chart-title").textContent = `${scan.symbol} · ${number(scan.price, 5)}`;
  $("#detail-score").textContent = `${number(scan.score, 0)} / 100`;
  $("#detail-score").className = `badge ${tone(scan.status)}`;
  $("#scan-detail").innerHTML = `
    <div class="flex items-center justify-between"><span>Decision</span><span class="badge ${tone(scan.direction)}">${esc(scan.direction)}</span></div>
    <div class="grid grid-cols-2 gap-px overflow-hidden border border-line bg-line" style="border-radius:4px">
      ${detailCell("Regime", scan.regime)}${detailCell("Order", payload.order_type || "--")}${detailCell("Entry", number(payload.entry, 5))}${detailCell("Stop", number(payload.stop_loss, 5))}${detailCell("Target", number(payload.take_profit, 5))}${detailCell("Reward / risk", payload.reward_risk ? `1 : ${payload.reward_risk}` : "--")}
    </div>
    <div><p class="label mb-2">Why it scored</p><ul class="space-y-2">${(payload.reasons || []).map((reason) => `<li class="border-l-2 border-line pl-3 text-xs leading-5">${esc(reason)}</li>`).join("") || '<li class="text-xs">No confirmation notes.</li>'}</ul></div>
    <div><p class="label mb-2">Order flow</p><div class="space-y-2 text-xs"><div class="flex justify-between"><span>Depth imbalance</span><strong class="text-white">${payload.order_book?.imbalance == null ? "Unavailable" : `${number(payload.order_book.imbalance * 100, 1)}%`}</strong></div><div class="flex justify-between"><span>Aggressor delta</span><strong class="text-white">${payload.trade_flow?.delta_ratio == null ? "Unavailable" : `${number(payload.trade_flow.delta_ratio * 100, 1)}%`}</strong></div></div></div>`;
  const profile = payload.profile || {};
  $("#chart-levels").innerHTML = [["POC", profile.poc], ["VAH", profile.vah], ["VAL", profile.val], ["Entry", payload.entry], ["Stop", payload.stop_loss], ["Target", payload.take_profit]].map(([label, value]) => `<div class="border-r border-line px-2 py-3 last:border-r-0"><span class="label block">${label}</span><strong class="mt-1 block text-slate-200">${number(value, 5)}</strong></div>`).join("");
  drawCandles(payload.candles || [], payload);
}

function detailCell(label, value) { return `<div class="bg-ink-950 p-3"><span class="label block">${label}</span><strong class="mt-1 block text-sm text-white">${esc(value)}</strong></div>`; }

function renderOrders(orders) {
  const body = $("#orders-body");
  if (!body) return;
  body.innerHTML = orders.length ? orders.map((order) => `<tr><td>${esc(dateTime(order.opened_at))}</td><td class="font-semibold text-white">${esc(order.symbol)}</td><td><span class="badge ${tone(order.side)}">${esc(order.side)}</span></td><td>${esc(order.order_type)}</td><td>${number(order.entry, 5)}</td><td>${number(order.stop_loss, 5)}</td><td>${number(order.take_profit, 5)}</td><td>${number(order.score, 0)}</td><td><span class="badge ${tone(order.status)}">${esc(order.status)}</span></td><td class="${Number(order.pnl || 0) >= 0 ? "text-signal" : "text-loss"}">${order.pnl == null ? "--" : money(order.pnl)}</td></tr>`).join("") : '<tr><td colspan="10" class="text-center text-muted">No orders yet.</td></tr>';
}

function drawCandles(candles, payload) {
  const canvas = $("#candle-chart");
  const empty = $("#chart-empty");
  if (!canvas || !candles.length) { if (empty) empty.classList.remove("hidden"); return; }
  empty.classList.add("hidden");
  const rect = canvas.getBoundingClientRect();
  const ratio = window.devicePixelRatio || 1;
  canvas.width = rect.width * ratio; canvas.height = rect.height * ratio;
  const ctx = canvas.getContext("2d"); ctx.scale(ratio, ratio);
  const width = rect.width, height = rect.height, pad = {left: 12, right: 64, top: 18, bottom: 26};
  const visible = candles.slice(-120);
  const levelValues = [payload.entry, payload.stop_loss, payload.take_profit].filter(Number.isFinite);
  const min = Math.min(...visible.map((c) => c.low), ...levelValues), max = Math.max(...visible.map((c) => c.high), ...levelValues);
  const range = Math.max(max - min, 1e-8), plotW = width - pad.left - pad.right, plotH = height - pad.top - pad.bottom;
  const y = (price) => pad.top + (max - price) / range * plotH;
  ctx.fillStyle = "#0d1118"; ctx.fillRect(0, 0, width, height);
  ctx.strokeStyle = "#1d2733"; ctx.lineWidth = 1;
  ctx.font = "10px Segoe UI"; ctx.fillStyle = "#8290a3";
  for (let i = 0; i <= 5; i++) { const py = pad.top + plotH * i / 5; ctx.beginPath(); ctx.moveTo(pad.left, py); ctx.lineTo(width - pad.right, py); ctx.stroke(); const price = max - range * i / 5; ctx.fillText(number(price, price > 1000 ? 1 : 4), width - pad.right + 8, py + 3); }
  const slot = plotW / visible.length, bodyW = Math.max(1, Math.min(7, slot * .68));
  visible.forEach((candle, index) => { const x = pad.left + slot * index + slot / 2; const up = candle.close >= candle.open; ctx.strokeStyle = up ? "#22d3a7" : "#fb7185"; ctx.fillStyle = ctx.strokeStyle; ctx.beginPath(); ctx.moveTo(x, y(candle.high)); ctx.lineTo(x, y(candle.low)); ctx.stroke(); const top = y(Math.max(candle.open, candle.close)); const bottom = y(Math.min(candle.open, candle.close)); ctx.fillRect(x - bodyW / 2, top, bodyW, Math.max(1, bottom - top)); });
  [[payload.entry, "ENTRY", "#38bdf8"], [payload.stop_loss, "SL", "#fb7185"], [payload.take_profit, "TP", "#22d3a7"]].forEach(([price, label, color]) => { if (!Number.isFinite(price)) return; const py = y(price); ctx.strokeStyle = color; ctx.setLineDash([5,4]); ctx.beginPath(); ctx.moveTo(pad.left, py); ctx.lineTo(width - pad.right, py); ctx.stroke(); ctx.setLineDash([]); ctx.fillStyle = color; ctx.fillText(label, pad.left + 4, py - 4); });
}

$("#scan-now")?.addEventListener("click", async () => { try { await api("/api/worker/scan", {method: "POST"}); toast("Scan queued."); } catch (error) { toast(error.message, "error"); } });

async function loadScanner() {
  latestScans = await api("/api/scans");
  const grid = $("#scanner-grid");
  grid.innerHTML = latestScans.length ? latestScans.map((scan) => `<button type="button" data-scan="${esc(scan.symbol)}" class="panel p-4 text-left transition hover:border-slate-500"><div class="flex items-start justify-between"><div><p class="label">${esc(scan.regime)}</p><h2 class="mt-1 text-lg font-semibold text-white">${esc(scan.symbol)}</h2></div><span class="badge ${tone(scan.status)}">${esc(scan.status.replace('_', ' '))}</span></div><div class="mt-5 flex items-end justify-between"><div><p class="text-2xl font-semibold text-white">${number(scan.price, 5)}</p><p class="mt-1 text-xs text-muted">${esc(dateTime(scan.timestamp))}</p></div><div class="text-right"><p class="text-2xl font-semibold ${scan.score >= 78 ? "text-signal" : "text-slate-300"}">${number(scan.score, 0)}</p><p class="text-xs text-muted">score</p></div></div></button>`).join("") : '<p class="text-sm text-muted">No scans yet. Start the worker after configuring Databento.</p>';
  $$('[data-scan]', grid).forEach((button) => button.addEventListener("click", () => renderScannerDetail(button.dataset.scan)));
  if (latestScans.length) renderScannerDetail(latestScans[0].symbol);
}

function renderScannerDetail(symbol) {
  const scan = latestScans.find((item) => item.symbol === symbol); if (!scan) return;
  const p = scan.payload || {}; $("#scanner-detail-title").textContent = `${symbol} · ${scan.direction} · score ${scan.score}`;
  $("#scanner-detail").innerHTML = `<div>${detailSection("Trade plan", [["Order", p.order_type], ["Entry", number(p.entry, 5)], ["Stop", number(p.stop_loss, 5)], ["Target", number(p.take_profit, 5)], ["RR", p.reward_risk ? `1:${p.reward_risk}` : "--"]])}</div><div>${detailSection("Volume profile", [["Source", p.profile?.source], ["POC", number(p.profile?.poc, 5)], ["VAH", number(p.profile?.vah, 5)], ["VAL", number(p.profile?.val, 5)], ["Volume", number(p.profile?.total_volume, 0)]])}</div><div><p class="label mb-3">Confirmations</p><ul class="space-y-2 text-xs text-muted">${(p.reasons || []).map((reason) => `<li>${esc(reason)}</li>`).join("")}</ul></div>`;
}

function detailSection(title, rows) { return `<p class="label mb-3">${title}</p><dl class="space-y-2 text-sm">${rows.map(([key,value]) => `<div class="flex justify-between gap-4"><dt class="text-muted">${esc(key)}</dt><dd class="font-medium text-white">${esc(value || "--")}</dd></div>`).join("")}</dl>`; }

async function initBacktests() {
  let enabled = new Set(["XAUUSD"]);
  try {
    const envelope = await api("/api/config");
    enabled = new Set(symbols.filter((symbol) => envelope.config.symbols[symbol]?.enabled));
  } catch (_) {}
  $("#backtest-symbols").innerHTML = symbols.map((symbol) => `<label class="badge cursor-pointer gap-2 bg-ink-950"><input type="checkbox" name="symbols" value="${symbol}" ${enabled.has(symbol) ? "checked" : ""} class="accent-[#22d3a7]">${symbol}</label>`).join("");
  $("#backtest-form").addEventListener("submit", async (event) => {
    event.preventDefault(); const form = new FormData(event.currentTarget); const selected = $$('#backtest-symbols input:checked').map((input) => input.value);
    if (!selected.length) return toast("Select at least one symbol.", "error");
    const button = $("button[type=submit]", event.currentTarget); button.disabled = true;
    try { const run = await api("/api/backtests", {method:"POST", body: JSON.stringify({period: form.get("period"), starting_balance: Number(form.get("starting_balance")), optimize: form.get("optimize") === "on", symbols: selected})}); toast(`Backtest #${run.id} queued.`); activeRunId = run.id; await loadRuns(); await loadRun(run.id); }
    catch (error) { toast(error.message, "error"); } finally { button.disabled = false; }
  });
  $("#refresh-runs").addEventListener("click", loadRuns); loadRuns();
}

async function loadRuns() {
  const runs = await api("/api/backtests"); const host = $("#runs-list");
  host.innerHTML = runs.length ? runs.map((run) => `<button type="button" data-run="${run.id}" class="block w-full p-4 text-left hover:bg-ink-850 ${run.id === activeRunId ? "bg-ink-850" : ""}"><div class="flex justify-between gap-3"><strong class="text-sm text-white">#${run.id} · ${esc(run.period.toUpperCase())}</strong><span class="badge ${tone(run.status)}">${esc(run.status)}</span></div><p class="mt-2 text-xs text-muted">${esc(run.start_date)} to ${esc(run.end_date)} · ${run.symbols.length} symbols</p></button>`).join("") : '<p class="p-4 text-sm text-muted">No backtests yet.</p>';
  $$('[data-run]', host).forEach((button) => button.addEventListener("click", () => { activeRunId = Number(button.dataset.run); loadRuns(); loadRun(activeRunId); }));
}

async function loadRun(id) {
  const run = await api(`/api/backtests/${id}`); $("#result-title").textContent = `Backtest #${id} · ${run.status}`;
  if (run.status === "error") { $("#result-content").innerHTML = `<p class="text-loss">${esc(run.error)}</p>`; return; }
  if (run.status !== "complete") { $("#result-content").innerHTML = '<div class="skeleton h-24 w-full"></div><p class="mt-3 text-muted">Worker is processing market data and simulations.</p>'; setTimeout(() => loadRun(id), 5000); return; }
  const aggregate = run.aggregate || {};
  $("#result-content").innerHTML = `<div class="mb-5 grid grid-cols-2 overflow-hidden border border-line lg:grid-cols-4" style="border-radius:5px">${metricBox("Avg return", `${number(aggregate.average_return_percent)}%`)}${metricBox("Net profit", money(aggregate.total_net_profit_independent_accounts))}${metricBox("Total trades", aggregate.total_trades)}${metricBox("Symbols", aggregate.symbols)}</div><div class="table-wrap"><table class="data-table"><thead><tr><th>Symbol</th><th>End balance</th><th>Return</th><th>Trades</th><th>Win rate</th><th>Profit factor</th><th>Max DD</th></tr></thead><tbody>${run.results.map((result) => `<tr><td class="font-semibold text-white">${esc(result.symbol)}</td><td>${money(result.metrics.ending_balance)}</td><td class="${result.metrics.return_percent >= 0 ? "text-signal" : "text-loss"}">${number(result.metrics.return_percent)}%</td><td>${result.metrics.trades}</td><td>${number(result.metrics.win_rate)}%</td><td>${number(result.metrics.profit_factor, 3)}</td><td>${number(result.metrics.max_drawdown_percent)}%</td></tr><tr><td colspan="7" class="!p-0"><details><summary class="cursor-pointer px-4 py-2 text-xs text-muted">Monthly breakdown</summary><div class="overflow-x-auto p-3"><table class="data-table !min-w-[560px]"><thead><tr><th>Month</th><th>Open</th><th>Close</th><th>P&amp;L</th><th>Return</th><th>Trades</th><th>Win rate</th></tr></thead><tbody>${result.monthly.map((month) => `<tr><td>${month.month}</td><td>${money(month.opening_balance)}</td><td>${money(month.closing_balance)}</td><td>${money(month.pnl)}</td><td>${number(month.return_percent)}%</td><td>${month.trades}</td><td>${number(month.win_rate)}%</td></tr>`).join("")}</tbody></table></div></details></td></tr>`).join("")}</tbody></table></div><p class="mt-4 text-xs text-muted">${esc(aggregate.note || "")}</p>`;
}

function metricBox(label, value) { return `<div class="metric"><p class="label">${label}</p><p class="mt-1 text-xl font-semibold text-white">${value}</p></div>`; }

async function initConfig() {
  const envelope = await api("/api/config"); window.runtimeConfig = envelope.config;
  if (!envelope.databento_key_configured) { const notice = $("#provider-notice"); notice.classList.remove("hidden"); notice.innerHTML = '<strong>Market data key needed.</strong> Add <code>DATABENTO_API_KEY=db-...</code> to <code>.env</code>, then restart run.bat. The UI and configuration work without it; scans and honest backtests do not.'; }
  renderConfig(envelope.config);
  $("#save-config").addEventListener("click", saveConfig);
}

const globalFields = [
  ["account_balance", "Account balance", "number", 1], ["risk_percent", "Risk per trade (%)", "number", .1], ["max_trades_per_day", "Max trades / day", "number", 1], ["execution_mode", "Execution", "select", ["paper","signals_only","mt5"]],
  ["scan_interval_seconds", "Scan interval (sec)", "number", 1], ["trail_enabled", "Trail stops", "checkbox"], ["trail_step_r", "Trail step (R)", "number", .25], ["partial_take_profit_percent", "Partial close (%)", "number", 1]
  , ["max_data_cost_usd", "Max download cost ($)", "number", .01], ["mt5_live_orders_enabled", "Allow MT5 orders", "checkbox"], ["max_basis_bps", "Maximum CME basis (bps)", "number", 1]
];
const signalFields = [
  ["signal_timeframe_minutes", "Signal timeframe (min)", "number", 1], ["profile_lookback_days", "Profile lookback (days)", "number", 1], ["profile_bins", "Profile price bins", "number", 1], ["value_area_percent", "Value area fraction", "number", .01],
  ["minimum_score", "Default A+ score", "number", 1], ["orderbook_imbalance_threshold", "Depth imbalance", "number", .01], ["volume_expansion_ratio", "Volume expansion", "number", .05], ["pending_expiry_bars", "Pending expiry (bars)", "number", 1],
  ["use_trade_tape_profile", "Use trade tape live", "checkbox"], ["use_order_book", "Use MBP-10 depth", "checkbox"], ["optimize_objective", "Optimization objective", "select", ["balanced","growth","drawdown"]]
];

function renderConfig(config) {
  $("#global-config").innerHTML = globalFields.map((field) => configField(field, config[field[0]])).join("");
  $("#signal-config").innerHTML = signalFields.map((field) => configField(field, config[field[0]])).join("");
  $("#symbol-config").innerHTML = symbols.map((symbol) => { const item = config.symbols[symbol]; return `<tr data-symbol-row="${symbol}"><td><input data-key="enabled" type="checkbox" ${item.enabled ? "checked" : ""} class="accent-[#22d3a7]"></td><td class="font-semibold text-white">${symbol}<input data-key="mt5_symbol" class="field mt-2 min-w-24" value="${esc(item.mt5_symbol)}" title="MT5 symbol"></td><td><input data-key="provider_symbol" class="field min-w-24" value="${esc(item.provider_symbol)}"></td><td><input data-key="reward_risk" type="number" step=".1" class="field w-20" value="${item.reward_risk}"></td><td><input data-key="atr_stop_multiplier" type="number" step=".1" class="field w-20" value="${item.atr_stop_multiplier}"></td><td><input data-key="minimum_score" type="number" step="1" placeholder="Default" class="field w-24" value="${item.minimum_score ?? ""}"></td><td><input data-key="spread_bps" type="number" step=".1" class="field w-20" value="${item.spread_bps}"></td><td><input data-key="slippage_bps" type="number" step=".1" class="field w-20" value="${item.slippage_bps}"></td><td><input data-key="sessions" class="field min-w-48" value="${esc((item.sessions || config.sessions).join(','))}"></td></tr>`; }).join("");
}

function configField([key, label, type, options], value) {
  let control;
  if (type === "checkbox") control = `<input data-config="${key}" type="checkbox" ${value ? "checked" : ""} class="h-5 w-5 accent-[#22d3a7]">`;
  else if (type === "select") control = `<select data-config="${key}" class="field">${options.map((option) => `<option value="${option}" ${value === option ? "selected" : ""}>${option.replace('_',' ')}</option>`).join("")}</select>`;
  else control = `<input data-config="${key}" type="${type}" step="${options || 'any'}" class="field" value="${esc(value)}">`;
  return `<label class="${type === 'checkbox' ? 'flex items-center justify-between border border-line bg-ink-950 px-3 py-2' : ''}" style="border-radius:4px"><span class="label mb-2 ${type === 'checkbox' ? '!mb-0' : 'block'}">${label}</span>${control}</label>`;
}

async function saveConfig() {
  const config = structuredClone(window.runtimeConfig);
  $$('[data-config]').forEach((input) => { const old = config[input.dataset.config]; config[input.dataset.config] = input.type === "checkbox" ? input.checked : typeof old === "number" ? Number(input.value) : input.value; });
  $$('[data-symbol-row]').forEach((row) => { const symbol = row.dataset.symbolRow; $$('[data-key]', row).forEach((input) => { const key = input.dataset.key; const old = config.symbols[symbol][key]; if (key === "sessions") config.symbols[symbol][key] = input.value.split(',').map((v) => v.trim()).filter(Boolean); else if (key === "minimum_score") config.symbols[symbol][key] = input.value ? Number(input.value) : null; else config.symbols[symbol][key] = input.type === "checkbox" ? input.checked : typeof old === "number" ? Number(input.value) : input.value; }); });
  const button = $("#save-config"); button.disabled = true;
  try { const saved = await api("/api/config", {method:"PUT", body: JSON.stringify(config)}); window.runtimeConfig = saved.config; renderConfig(saved.config); toast("Configuration saved. The worker will use it on the next scan."); }
  catch (error) { toast(error.message, "error"); } finally { button.disabled = false; }
}

window.addEventListener("resize", () => { if (page === "dashboard") renderDashboardScan(); });
refreshWorker(); setInterval(refreshWorker, 10000);
if (page === "dashboard") { loadDashboard().catch((e) => toast(e.message,"error")); setInterval(() => loadDashboard().catch(() => {}), 15000); }
if (page === "scanner") { loadScanner().catch((e) => toast(e.message,"error")); setInterval(() => loadScanner().catch(() => {}), 15000); }
if (page === "backtests") initBacktests().catch((e) => toast(e.message,"error"));
if (page === "config") initConfig().catch((e) => toast(e.message,"error"));

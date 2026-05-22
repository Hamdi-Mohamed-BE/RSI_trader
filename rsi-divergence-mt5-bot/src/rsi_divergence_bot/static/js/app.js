const STRATEGY_LABELS = {
  signal_no_tp_protection: "No TP protection",
  signal_with_tp_protection: "With TP protection",
};

const els = {
  loopBadge: document.getElementById("loop-badge"),
  modeBadge: document.getElementById("mode-badge"),
  strategyBadge: document.getElementById("strategy-badge"),
  statSymbols: document.getElementById("stat-symbols"),
  statPoll: document.getElementById("stat-poll"),
  statSetups: document.getElementById("stat-setups"),
  statMagic: document.getElementById("stat-magic"),
  symbolsBody: document.getElementById("symbols-body"),
  saveLotsBtn: document.getElementById("save-lots-btn"),
  backtestForm: document.getElementById("backtest-form"),
  start: document.getElementById("start"),
  end: document.getElementById("end"),
  startingBalance: document.getElementById("starting-balance"),
  strategy: document.getElementById("strategy"),
  backtestBtn: document.getElementById("backtest-btn"),
  backtestSummary: document.getElementById("backtest-summary"),
  backtestDailyWrap: document.getElementById("backtest-daily-wrap"),
  backtestDailyBody: document.getElementById("backtest-daily-body"),
  backtestTableWrap: document.getElementById("backtest-table-wrap"),
  backtestBody: document.getElementById("backtest-body"),
  backtestTradesWrap: document.getElementById("backtest-trades-wrap"),
  backtestTradesList: document.getElementById("backtest-trades-list"),
  backtestRaw: document.getElementById("backtest-raw"),
  runOnceBtn: document.getElementById("run-once-btn"),
  manualTradeForm: document.getElementById("manual-trade-form"),
  manualTradeText: document.getElementById("manual-trade-text"),
  manualTradeBtn: document.getElementById("manual-trade-btn"),
  manualTradeResult: document.getElementById("manual-trade-result"),
  manualTradeStatus: document.getElementById("manual-trade-status"),
  autoRunStartBtn: document.getElementById("auto-run-start-btn"),
  autoRunStopBtn: document.getElementById("auto-run-stop-btn"),
  autoRunDot: document.getElementById("auto-run-dot"),
  autoRunLabel: document.getElementById("auto-run-label"),
  autoRunScans: document.getElementById("auto-run-scans"),
  autoRunLast: document.getElementById("auto-run-last"),
  autoRunStrategyLabel: document.getElementById("auto-run-strategy-label"),
  autoRunStrategy: document.getElementById("auto-run-strategy"),
  autoRunSaveStrategy: document.getElementById("auto-run-save-strategy"),
  autoRunSaveBtn: document.getElementById("auto-run-save-btn"),
  autoRunHint: document.getElementById("auto-run-hint"),
  liveUpdated: document.getElementById("live-updated"),
  liveError: document.getElementById("live-error"),
  acctBalance: document.getElementById("acct-balance"),
  acctEquity: document.getElementById("acct-equity"),
  acctFloating: document.getElementById("acct-floating"),
  acctFreeMargin: document.getElementById("acct-free-margin"),
  acctMeta: document.getElementById("acct-meta"),
  positionsBody: document.getElementById("positions-body"),
  positionsCount: document.getElementById("positions-count"),
  dealsBody: document.getElementById("deals-body"),
  dealsCount: document.getElementById("deals-count"),
  scanResult: document.getElementById("scan-result"),
  status: document.getElementById("status"),
  logs: document.getElementById("logs"),
  logViewport: document.getElementById("log-viewport"),
  logFilter: document.getElementById("log-filter"),
  logCount: document.getElementById("log-count"),
  autoScroll: document.getElementById("auto-scroll"),
  refreshLogsBtn: document.getElementById("refresh-logs-btn"),
  telegramUpdated: document.getElementById("telegram-updated"),
  telegramDot: document.getElementById("telegram-dot"),
  telegramLabel: document.getElementById("telegram-label"),
  telegramCounts: document.getElementById("telegram-counts"),
  telegramLast: document.getElementById("telegram-last"),
  telegramProtectTp: document.getElementById("telegram-protect-tp"),
  telegramStartBtn: document.getElementById("telegram-start-btn"),
  telegramStopBtn: document.getElementById("telegram-stop-btn"),
  telegramClearBtn: document.getElementById("telegram-clear-btn"),
  telegramHint: document.getElementById("telegram-hint"),
  telegramError: document.getElementById("telegram-error"),
  telegramGemini: document.getElementById("telegram-gemini"),
  telegramOpenGuard: document.getElementById("telegram-open-guard"),
  telegramChannels: document.getElementById("telegram-channels"),
  telegramPoll: document.getElementById("telegram-poll"),
  telegramLastParsed: document.getElementById("telegram-last-parsed"),
  telegramLastResult: document.getElementById("telegram-last-result"),
  telegramLastResultJson: document.getElementById("telegram-last-result-json"),
  telegramMessagesBody: document.getElementById("telegram-messages-body"),
  toastStack: document.getElementById("toast-stack"),
};

let allLogs = [];
let logTimer = null;
let loopTimer = null;
let liveTimer = null;
let telegramTimer = null;
let botConfig = null;
let symbolSettingsReady = false;

function currentPage() {
  const path = window.location.pathname.replace(/\/+$/, "") || "/";
  if (path === "/backtest") return "backtest";
  if (path === "/settings") return "settings";
  if (path === "/manual-trade") return "manual-trade";
  if (path === "/telegram-signals") return "telegram-signals";
  if (path === "/logs") return "logs";
  return "home";
}

function applyPageVisibility() {
  const page = currentPage();
  document.body.dataset.page = page;

  for (const section of document.querySelectorAll("[data-pages]")) {
    const pages = (section.dataset.pages || "").split(/\s+/).filter(Boolean);
    section.classList.toggle("page-hidden", !pages.includes(page));
  }

  for (const link of document.querySelectorAll("[data-page-link]")) {
    link.classList.toggle("active", link.dataset.pageLink === page);
  }
}

function toast(message, type = "info") {
  const node = document.createElement("div");
  node.className = `toast toast-${type}`;
  node.textContent = message;
  els.toastStack.appendChild(node);
  setTimeout(() => node.remove(), 4200);
}

function setLoading(button, loading, loadingText = null) {
  const label = button.querySelector(".btn-label");
  const spinner = button.querySelector(".spinner");
  button.disabled = loading;
  if (label) {
    if (loading && loadingText) {
      if (!label.dataset.defaultText) label.dataset.defaultText = label.textContent;
      label.textContent = loadingText;
      label.hidden = false;
    } else {
      if (label.dataset.defaultText) label.textContent = label.dataset.defaultText;
      label.hidden = loading;
    }
  }
  if (spinner) spinner.hidden = !loading;
}

function isoToLocalInput(iso) {
  const date = new Date(iso);
  const pad = (n) => String(n).padStart(2, "0");
  return `${date.getUTCFullYear()}-${pad(date.getUTCMonth() + 1)}-${pad(date.getUTCDate())}T${pad(date.getUTCHours())}:${pad(date.getUTCMinutes())}`;
}

function localInputToIso(value) {
  if (!value) return "";
  return `${value}:00+00:00`;
}

function formatStrategy(value) {
  return STRATEGY_LABELS[value] || value.replaceAll("_", " ");
}

function pnlClass(value) {
  if (value > 0) return "value-positive";
  if (value < 0) return "value-negative";
  return "value-neutral";
}

function formatMoney(value) {
  const prefix = value > 0 ? "+" : "";
  return `${prefix}$${Number(value).toFixed(2)}`;
}

function escapeHtml(text) {
  if (text == null) return "";
  return String(text)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;");
}

function colorizeLogLine(line) {
  const safe = escapeHtml(line);
  const upper = line.toUpperCase();
  if (upper.includes("ERROR") || upper.includes("FAILED")) {
    return `<span class="log-line-error">${safe}</span>`;
  }
  if (upper.includes("WARN") || upper.includes("STARTUP") || upper.includes("DRY_RUN")) {
    return `<span class="log-line-warn">${safe}</span>`;
  }
  if (upper.includes("BACKTEST") || upper.includes("WEB START") || upper.includes("AUTO LOOP") || upper.includes("BOT LOOP")) {
    return `<span class="log-line-info">${safe}</span>`;
  }
  if (upper.includes("SIGNAL") || upper.includes("COMPLETE") || upper.includes("FILLED")) {
    return `<span class="log-line-success">${safe}</span>`;
  }
  if (upper.includes("DEBUG")) {
    return `<span class="log-line-dim">${safe}</span>`;
  }
  return safe;
}

function renderLogs() {
  const query = els.logFilter.value.trim().toLowerCase();
  const filtered = query
    ? allLogs.filter((line) => line.toLowerCase().includes(query))
    : allLogs;

  els.logCount.textContent = `${filtered.length} line${filtered.length === 1 ? "" : "s"}`;

  if (!filtered.length) {
    els.logs.innerHTML = '<div class="log-empty">No log lines to display yet.</div>';
    return;
  }

  els.logs.innerHTML = filtered
    .map((line) => `<div class="log-line">${colorizeLogLine(line)}</div>`)
    .join("");

  if (els.autoScroll.checked) {
    els.logViewport.scrollTop = els.logViewport.scrollHeight;
  }
}

async function refreshLogs() {
  try {
    const response = await fetch("/api/logs", { cache: "no-store" });
    if (!response.ok) throw new Error("Failed to load logs");
    const data = await response.json();
    allLogs = Array.isArray(data) ? data : [];
    renderLogs();
  } catch (error) {
    els.logs.innerHTML = `<div class="log-empty">${escapeHtml(error.message)}</div>`;
    toast(error.message, "error");
  }
}

function renderSymbols(symbols) {
  if (!els.symbolsBody) return;

  const rows = Array.isArray(symbols) ? symbols : [];
  if (!rows.length) {
    els.symbolsBody.innerHTML = '<tr><td colspan="8" class="empty-row">No symbols in config.</td></tr>';
    return;
  }

  els.symbolsBody.innerHTML = rows
    .map(
      (item) => `
        <tr class="${item.enabled ? "" : "row-disabled"}">
          <td>
            <label class="switch" title="${item.enabled ? "Enabled" : "Disabled"}">
              <input
                class="symbol-enabled"
                type="checkbox"
                data-symbol="${escapeHtml(item.symbol)}"
                ${item.enabled ? "checked" : ""}
              >
              <span class="switch-slider"></span>
            </label>
          </td>
          <td><strong>${escapeHtml(item.symbol)}</strong></td>
          <td><span class="tag">${escapeHtml(item.market_key || item.symbol)}</span></td>
          <td>${escapeHtml(item.name)}</td>
          <td><span class="tag tag-accent">${escapeHtml(item.timeframe)}</span></td>
          <td>
            <input
              class="lot-input"
              type="number"
              min="0.01"
              step="0.01"
              data-symbol="${escapeHtml(item.symbol)}"
              value="${item.lot_per_leg}"
            >
          </td>
          <td>${escapeHtml(item.confirmation)}</td>
          <td>${(item.sessions || []).map((s) => `<span class="tag">${escapeHtml(s)}</span>`).join("") || "—"}</td>
        </tr>
      `,
    )
    .join("");
}

function updateSymbolStats(stats) {
  if (!stats) return;
  els.statSymbols.textContent = `${stats.enabled} / ${stats.total}`;
}

function symbolSettingsFromConfig() {
  const lots = {};
  const enabled = {};
  for (const item of botConfig?.symbols || []) {
    lots[item.symbol] = item.lot_per_leg;
    enabled[item.symbol] = Boolean(item.enabled);
  }
  return { lots, enabled };
}

function collectSymbolSettings() {
  const lots = {};
  const enabled = {};
  const lotInputs = els.symbolsBody.querySelectorAll(".lot-input");
  const enabledInputs = els.symbolsBody.querySelectorAll(".symbol-enabled");

  if (!lotInputs.length && !enabledInputs.length) {
    return symbolSettingsFromConfig();
  }

  for (const input of lotInputs) {
    const symbol = input.dataset.symbol;
    const lot = Number(input.value);
    if (!symbol || !Number.isFinite(lot) || lot <= 0) {
      throw new Error(`Invalid lot size for ${symbol || "symbol"}`);
    }
    lots[symbol] = lot;
  }

  for (const input of enabledInputs) {
    const symbol = input.dataset.symbol;
    if (!symbol) continue;
    enabled[symbol] = input.checked;
  }

  if (!Object.keys(lots).length || !Object.keys(enabled).length) {
    const fallback = symbolSettingsFromConfig();
    if (!Object.keys(lots).length) Object.assign(lots, fallback.lots);
    if (!Object.keys(enabled).length) Object.assign(enabled, fallback.enabled);
  }

  return { lots, enabled };
}

function formatApiError(detail) {
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail.map((item) => item.msg || JSON.stringify(item)).join("; ");
  }
  return "Request failed";
}

async function syncSymbolSettings({ persist = true, silent = false, rerender = false } = {}) {
  const { lots, enabled } = collectSymbolSettings();
  if (!Object.keys(lots).length && !Object.keys(enabled).length) {
    return { status: "noop", symbols: botConfig?.symbols || [], symbol_stats: botConfig?.symbol_stats || null };
  }

  const response = await fetch("/api/symbols/settings", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ lots, enabled, persist }),
  });
  const data = await response.json();
  if (!response.ok) throw new Error(formatApiError(data.detail) || "Failed to sync symbol settings");

  if (botConfig) {
    botConfig.symbols = data.symbols;
    botConfig.symbol_stats = data.symbol_stats;
  }
  updateSymbolStats(data.symbol_stats);
  if (rerender || !silent) renderSymbols(data.symbols);

  if (!silent) {
    toast(persist ? "Symbol settings saved to config" : "Symbol settings applied", "success");
    await refreshLogs();
  }

  return data;
}

let settingsTimer = null;

function scheduleSettingsSync({ persist = false, silent = true } = {}) {
  if (!symbolSettingsReady) return;
  if (settingsTimer) clearTimeout(settingsTimer);
  settingsTimer = setTimeout(async () => {
    try {
      await syncSymbolSettings({ persist, silent, rerender: false });
      if (!silent) toast("Symbol settings updated", "info");
    } catch (error) {
      toast(error.message, "error");
    }
  }, 400);
}

async function saveLots() {
  setLoading(els.saveLotsBtn, true);
  try {
    await syncSymbolSettings({ persist: true, silent: false, rerender: true });
  } catch (error) {
    toast(error.message, "error");
  } finally {
    setLoading(els.saveLotsBtn, false);
  }
}

function formatCurrency(value) {
  return `$${Number(value).toFixed(2)}`;
}

function formatPrice(value) {
  if (value === 0) return "—";
  return Number(value).toFixed(5);
}

function renderLiveData(data) {
  data = data || {};
  const hasAccount = Boolean(data.account);
  const failed = Boolean(data.error) && !hasAccount;

  if (failed) {
    els.liveError.textContent = data.error;
    els.liveError.classList.remove("hidden");
    els.liveUpdated.textContent = "Live: disconnected";
    els.liveUpdated.classList.remove("ok");
    els.positionsBody.innerHTML = `<tr><td colspan="10" class="empty-row">${escapeHtml(data.error)}</td></tr>`;
    els.dealsBody.innerHTML = '<tr><td colspan="8" class="empty-row">Live data unavailable.</td></tr>';
    els.positionsCount.textContent = "0 open";
    els.dealsCount.textContent = "0 deals";
    return;
  }

  if (data.error) {
    els.liveError.textContent = data.error;
    els.liveError.classList.remove("hidden");
  } else {
    els.liveError.classList.add("hidden");
  }

  els.liveUpdated.textContent = `Live: ${formatTimestamp(data.updated_at)}`;
  els.liveUpdated.classList.toggle("ok", Boolean(data.connected || hasAccount));

  const account = data.account;
  if (account) {
    els.acctBalance.textContent = formatCurrency(account.balance);
    els.acctEquity.textContent = formatCurrency(account.equity);
    els.acctFloating.textContent = formatMoney(account.floating_pnl);
    els.acctFloating.className = `stat-value ${pnlClass(account.floating_pnl)}`;
    els.acctFreeMargin.textContent = formatCurrency(account.free_margin);
    els.acctMeta.textContent = `#${account.login} · ${account.server}`;
  }

  const positions = data.positions || [];
  els.positionsCount.textContent = `${positions.length} open`;
  if (!positions.length) {
    els.positionsBody.innerHTML = '<tr><td colspan="10" class="empty-row">No open positions.</td></tr>';
  } else {
    els.positionsBody.innerHTML = positions
      .map(
        (row) => `
          <tr>
            <td>${row.ticket}${row.is_bot ? ' <span class="tag tag-bot">bot</span>' : ""}</td>
            <td><strong>${escapeHtml(row.symbol)}</strong></td>
            <td class="side-${row.side}">${String(row.side || "").toUpperCase()}</td>
            <td>${row.volume}</td>
            <td>${formatPrice(row.price_open)}</td>
            <td>${formatPrice(row.price_current)}</td>
            <td>${formatPrice(row.sl)}</td>
            <td>${formatPrice(row.tp)}</td>
            <td class="${pnlClass(row.profit)}">${formatMoney(row.profit)}</td>
            <td>${escapeHtml(row.comment || "—")}</td>
          </tr>
        `,
      )
      .join("");
  }

  const deals = data.deals || [];
  els.dealsCount.textContent = `${deals.length} deals`;
  if (!deals.length) {
    els.dealsBody.innerHTML = '<tr><td colspan="8" class="empty-row">No deals in the last 24 hours.</td></tr>';
  } else {
    els.dealsBody.innerHTML = deals
      .map(
        (row) => `
          <tr>
            <td>${formatTimestamp(row.time)}</td>
            <td>${row.ticket}</td>
            <td><strong>${escapeHtml(row.symbol)}</strong></td>
            <td class="side-${row.side}">${String(row.side).toUpperCase()}</td>
            <td>${row.volume}</td>
            <td>${formatPrice(row.price)}</td>
            <td class="${pnlClass(row.profit)}">${formatMoney(row.profit)}</td>
            <td>${escapeHtml(row.comment || "—")}</td>
          </tr>
        `,
      )
      .join("");
  }
}

async function refreshLiveData() {
  try {
    const response = await fetch("/api/live", { cache: "no-store" });
    let data;
    try {
      data = await response.json();
    } catch {
      throw new Error(`Live data failed (HTTP ${response.status})`);
    }
    if (!response.ok && !data.error) {
      data.error = typeof data.detail === "string" ? data.detail : `HTTP ${response.status}`;
    }
    renderLiveData(data);
  } catch (error) {
    renderLiveData({ error: error.message, connected: false });
  }
}

function startLivePolling() {
  if (liveTimer) clearInterval(liveTimer);
  liveTimer = setInterval(refreshLiveData, 5000);
}

function formatTimestamp(value) {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString();
}

function describeDecisionFilters(filters) {
  if (!filters) return "profile defaults";
  const names = [];
  if (filters.spread) names.push("spread");
  if (filters.tp1_spread) names.push("TP distance");
  if (filters.risk) names.push("risk cap");
  if (filters.existing_position) names.push("existing position");
  if (filters.max_setups) names.push("max setups");
  return names.length ? `filters: ${names.join(", ")}` : "raw signal gate only";
}

function syncStrategyUi(strategy) {
  if (!strategy) return;
  if (els.autoRunStrategy) els.autoRunStrategy.value = strategy;
  if (els.strategy) els.strategy.value = strategy;
  if (els.strategyBadge) els.strategyBadge.textContent = formatStrategy(strategy);
  if (botConfig?.bot) botConfig.bot.strategy = strategy;
}

function renderAutoRunStatus(status) {
  if (!els.autoRunLabel || !els.autoRunDot) return;

  const running = Boolean(status.running);
  const strategy = status.strategy || botConfig?.bot?.strategy;
  els.autoRunDot.classList.toggle("running", running);
  els.autoRunLabel.textContent = running ? "Running" : "Stopped";
  els.autoRunScans.textContent = `${status.scans_completed || 0} scans · ${status.last_signals || 0} signals · ${status.last_placed || 0} placed`;
  els.autoRunLast.textContent = `Last scan: ${formatTimestamp(status.last_scan_at)}`;
  if (els.autoRunStrategyLabel) {
    els.autoRunStrategyLabel.textContent = `Strategy: ${formatStrategy(strategy)}`;
  }
  syncStrategyUi(strategy);
  els.autoRunStartBtn.disabled = running;
  els.autoRunStopBtn.disabled = !running;
  if (els.autoRunStrategy) els.autoRunStrategy.disabled = false;

  if (running) {
    els.loopBadge.textContent = "Loop running";
    els.loopBadge.className = "badge badge-running";
    els.loopBadge.classList.remove("hidden");
  } else {
    els.loopBadge.classList.add("hidden");
  }

  if (status.last_error) {
    els.autoRunHint.textContent = `Last error: ${status.last_error}`;
    els.autoRunHint.className = "panel-hint live-warning";
  } else if (status.daily_risk?.halted) {
    els.autoRunHint.textContent = `Daily loss guard active: loss ${formatMoney(status.daily_risk.loss)} reached limit ${formatMoney(status.daily_risk.loss_limit)}. New trades are blocked until the next UTC day.`;
    els.autoRunHint.className = "panel-hint live-warning";
  } else if (!running) {
    const strategyText = formatStrategy(strategy);
    els.autoRunHint.textContent = status.dry_run
      ? `Auto run is stopped. Choose a TP protection rule, then start to scan symbols in paper mode (${strategyText}).`
      : `Auto run is stopped. Choose a TP protection rule, then start to scan enabled symbols and place live MT5 orders (${strategyText}).`;
    els.autoRunHint.className = "panel-hint";
  } else if (status.dry_run) {
    els.autoRunHint.textContent = `Paper mode: ${formatStrategy(strategy)}. Listening every ${status.poll_seconds}s. Signals are logged but no live orders are sent.`;
    els.autoRunHint.className = "panel-hint";
  } else {
    const profile = status.trade_decision_profile || botConfig?.bot?.trade_decision_profile || "safe";
    const filters = status.decision_filters || botConfig?.decision_filters;
    const profileText = `${profile} profile, ${describeDecisionFilters(filters)}`;
    els.autoRunHint.textContent = `Live mode: ${formatStrategy(strategy)}. Listening every ${status.poll_seconds}s. New signals auto-place split TP orders in MT5, ${profileText}.`;
    els.autoRunHint.className = "panel-hint live-warning";
  }
}

async function refreshAutoRunStatus() {
  try {
    const response = await fetch("/api/auto-run/status", { cache: "no-store" });
    if (!response.ok) throw new Error("Failed to load auto-run status");
    renderAutoRunStatus(await response.json());
  } catch (error) {
    toast(error.message, "error");
  }
}

async function saveBotStrategy({ persist, silent = false } = {}) {
  if (!els.autoRunStrategy) return null;
  const strategy = els.autoRunStrategy.value;
  const saveToConfig = persist ?? Boolean(els.autoRunSaveStrategy?.checked);
  setLoading(els.autoRunSaveBtn, true);
  try {
    const response = await fetch("/api/bot/settings", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ strategy, persist: saveToConfig }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || "Failed to save bot strategy");
    syncStrategyUi(data.strategy);
    if (data.auto_run) renderAutoRunStatus(data.auto_run);
    if (!silent) {
      toast(saveToConfig ? "Bot strategy saved to config" : "Bot strategy applied", "success");
    }
    return data;
  } finally {
    setLoading(els.autoRunSaveBtn, false);
  }
}

async function startAutoRun() {
  if (botConfig && !botConfig.bot.dry_run) {
    const strategyText = formatStrategy(els.autoRunStrategy?.value || botConfig.bot.strategy);
    const confirmed = window.confirm(
      `Live trading is enabled with ${strategyText}. The bot will place real MT5 orders all day until you stop it. Continue?`,
    );
    if (!confirmed) return;
  }

  setLoading(els.autoRunStartBtn, true);
  try {
    await syncSymbolSettings({ persist: false, silent: true });
    const response = await fetch("/api/auto-run/start", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        strategy: els.autoRunStrategy?.value,
        strategy_persist: Boolean(els.autoRunSaveStrategy?.checked),
        persist: false,
      }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || "Failed to start auto run");
    syncStrategyUi(data.strategy || els.autoRunStrategy?.value);
    renderAutoRunStatus(data);
    const strategyText = formatStrategy(data.strategy || els.autoRunStrategy?.value);
    toast(
      data.dry_run ? `Auto run started (paper, ${strategyText})` : `Auto run started (LIVE, ${strategyText})`,
      data.dry_run ? "info" : "success",
    );
    await refreshLogs();
  } catch (error) {
    toast(error.message, "error");
  } finally {
    setLoading(els.autoRunStartBtn, false);
  }
}

async function stopAutoRun() {
  setLoading(els.autoRunStopBtn, true);
  try {
    const response = await fetch("/api/auto-run/stop", { method: "POST" });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || "Failed to stop auto run");
    renderAutoRunStatus(data);
    toast("Auto run stopped", "info");
    await refreshLogs();
  } catch (error) {
    toast(error.message, "error");
  } finally {
    setLoading(els.autoRunStopBtn, false);
  }
}

function startLoopPolling() {
  if (loopTimer) clearInterval(loopTimer);
  loopTimer = setInterval(refreshAutoRunStatus, 2000);
}

function renderTelegramStatus(status) {
  if (!els.telegramLabel) return;
  const running = Boolean(status.running);

  els.telegramDot?.classList.toggle("running", running);
  if (els.telegramLabel) els.telegramLabel.textContent = running ? "Running" : "Stopped";
  if (els.telegramStartBtn) els.telegramStartBtn.disabled = running;
  if (els.telegramStopBtn) els.telegramStopBtn.disabled = !running;
  if (els.telegramUpdated) {
    els.telegramUpdated.textContent = `Telegram: ${running ? "watching" : "stopped"}`;
    els.telegramUpdated.classList.toggle("ok", running);
  }
  if (els.telegramCounts) {
    els.telegramCounts.textContent =
      `${status.messages_seen || 0} messages · ${status.parsed_signals || 0} parsed · ${status.placed || 0} placed`;
  }
  if (els.telegramLast) {
    els.telegramLast.textContent = `Last signal: ${formatTimestamp(status.last_action_at || status.last_message_at)}`;
  }

  if (els.telegramError) {
    if (status.last_error) {
      els.telegramError.textContent = status.last_error;
      els.telegramError.classList.remove("hidden");
    } else {
      els.telegramError.classList.add("hidden");
    }
  }

  if (els.telegramHint) {
    if (status.running && status.browser_open) {
      els.telegramHint.textContent = "Telegram browser is open. Login there if Telegram asks, then keep the signal chats visible.";
      els.telegramHint.className = "panel-hint live-warning";
    } else if (!status.gemini_api_key_configured) {
      els.telegramHint.textContent = "Gemini API key is missing. Add telegram_signals.gemini_api_key in config.yaml or set GEMINI_API_KEY.";
      els.telegramHint.className = "panel-hint live-warning";
    } else if (botConfig && !botConfig.bot.dry_run) {
      els.telegramHint.textContent = "Live mode: copied Telegram signals will place real MT5 orders after validation.";
      els.telegramHint.className = "panel-hint live-warning";
    } else {
      els.telegramHint.textContent = "Dry run mode: copied Telegram signals are parsed and logged without live orders.";
      els.telegramHint.className = "panel-hint";
    }
  }

  const signal = status.last_signal;
  if (els.telegramLastParsed) {
    els.telegramLastParsed.textContent = signal?.action && signal.action !== "none"
      ? `${String(signal.action).toUpperCase()} ${signal.symbol || ""}`
      : "—";
  }
  if (els.telegramLastResult && els.telegramLastResultJson) {
    if (status.last_result) {
      els.telegramLastResultJson.textContent = JSON.stringify(status.last_result, null, 2);
      els.telegramLastResult.classList.remove("hidden");
    } else {
      els.telegramLastResult.classList.add("hidden");
      els.telegramLastResultJson.textContent = "";
    }
  }
  renderTelegramMessages(status.recent_messages || []);
}

function renderTelegramMessages(messages) {
  if (!els.telegramMessagesBody) return;
  if (!messages.length) {
    els.telegramMessagesBody.innerHTML = '<tr><td colspan="5" class="empty-row">No Telegram messages tracked yet.</td></tr>';
    return;
  }
  els.telegramMessagesBody.innerHTML = messages
    .slice()
    .reverse()
    .map((item) => {
      const status = String(item.status || "unknown");
      const statusClass = status === "placed" || status === "paper"
        ? "value-positive"
        : status === "watching" || status === "latest"
          ? "value-positive"
        : status.includes("failed")
          ? "value-negative"
          : status === "stale" || status === "empty"
            ? "value-negative"
          : "value-neutral";
      return `
        <tr>
          <td class="${statusClass}">${escapeHtml(status)}</td>
          <td>${escapeHtml(String(item.channel_name || "—"))}</td>
          <td>${formatTimestamp(item.updated_at)}</td>
          <td>${escapeHtml(String(item.text_preview || "—")).slice(0, 220)}</td>
          <td>${escapeHtml(String(item.reason || item.result?.reason || "—"))}</td>
        </tr>
      `;
    })
    .join("");
}

function renderTelegramConfig(config) {
  if (!config.telegram_signals) return;
  const telegram = config.telegram_signals;
  if (els.telegramGemini) {
    els.telegramGemini.textContent = telegram.gemini_api_key_configured
      ? telegram.gemini_model
      : "Missing key";
  }
  if (els.telegramOpenGuard) {
    els.telegramOpenGuard.textContent = telegram.ignore_open_symbol_trades ? "On" : "Off";
  }
  if (els.telegramChannels) {
    els.telegramChannels.textContent = `${(telegram.channels || []).filter((channel) => channel.enabled).length} active`;
  }
  if (els.telegramPoll) {
    els.telegramPoll.textContent = `${telegram.poll_seconds}s`;
  }
}

async function refreshTelegramStatus() {
  if (!els.telegramLabel) return;
  try {
    const response = await fetch("/api/telegram-signals/status", { cache: "no-store" });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || "Failed to load Telegram copier status");
    renderTelegramStatus(data);
  } catch (error) {
    if (els.telegramError) {
      els.telegramError.textContent = error.message;
      els.telegramError.classList.remove("hidden");
    } else {
      toast(error.message, "error");
    }
  }
}

async function startTelegramSignals() {
  if (botConfig && !botConfig.bot.dry_run) {
    const confirmed = window.confirm(
      "Live trading is enabled. Telegram copied signals will place real MT5 orders after validation. Continue?",
    );
    if (!confirmed) return;
  }

  setLoading(els.telegramStartBtn, true);
  try {
    const response = await fetch("/api/telegram-signals/start", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ protect_tp: Boolean(els.telegramProtectTp?.checked) }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || "Failed to start Telegram copier");
    renderTelegramStatus(data);
    toast("Telegram copier started", "success");
    await refreshLogs();
  } catch (error) {
    toast(error.message, "error");
    await refreshTelegramStatus();
  } finally {
    setLoading(els.telegramStartBtn, false);
  }
}

async function stopTelegramSignals() {
  setLoading(els.telegramStopBtn, true);
  try {
    const response = await fetch("/api/telegram-signals/stop", { method: "POST" });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || "Failed to stop Telegram copier");
    renderTelegramStatus(data);
    toast("Telegram copier stopped", "info");
    await refreshLogs();
  } catch (error) {
    toast(error.message, "error");
  } finally {
    setLoading(els.telegramStopBtn, false);
  }
}

async function clearTelegramMessages() {
  const confirmed = window.confirm(
    "Clear all tracked Telegram messages and reset the dedup cache? New messages can be processed again.",
  );
  if (!confirmed) return;

  setLoading(els.telegramClearBtn, true);
  try {
    const response = await fetch("/api/telegram-signals/clear-messages", { method: "POST" });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || "Failed to clear Telegram messages");
    renderTelegramStatus(data);
    toast(
      `Cleared ${data.messages_removed || 0} message${data.messages_removed === 1 ? "" : "s"}`,
      "success",
    );
    await refreshLogs();
  } catch (error) {
    toast(error.message, "error");
  } finally {
    setLoading(els.telegramClearBtn, false);
  }
}

function startTelegramPolling() {
  if (telegramTimer) clearInterval(telegramTimer);
  telegramTimer = setInterval(refreshTelegramStatus, 2000);
}

function renderConfig(config) {
  symbolSettingsReady = false;
  botConfig = config;

  try {
    renderSymbols(config.symbols || []);
  } catch (error) {
    if (els.symbolsBody) {
      els.symbolsBody.innerHTML = `<tr><td colspan="8" class="empty-row">${escapeHtml(error.message)}</td></tr>`;
    }
    toast(error.message, "error");
  }
  symbolSettingsReady = true;

  try {
    const dryRun = config.bot?.dry_run;
    if (els.modeBadge) {
      els.modeBadge.textContent = dryRun ? "Dry run" : "Live trading";
      els.modeBadge.className = `badge ${dryRun ? "badge-warn" : "badge-live"}`;
    }

    if (els.strategyBadge) {
      els.strategyBadge.textContent = formatStrategy(config.bot?.strategy);
    }
    syncStrategyUi(config.bot?.strategy);
    if (els.statSymbols) {
      els.statSymbols.textContent = config.symbol_stats
        ? `${config.symbol_stats.enabled} / ${config.symbol_stats.total}`
        : `${(config.symbols || []).filter((item) => item.enabled).length} / ${(config.symbols || []).length}`;
    }
    if (els.statPoll) els.statPoll.textContent = `${config.bot?.poll_seconds ?? "—"}s`;
    const filters = config.decision_filters || {};
    if (els.statSetups) {
      els.statSetups.textContent = filters.max_setups ? config.bot?.max_concurrent_setups : "Ignored";
    }
    if (els.statMagic) els.statMagic.textContent = config.bot?.magic ?? "—";

    renderTelegramConfig(config);

    if (els.start && config.defaults?.backtest_start) {
      els.start.value = isoToLocalInput(config.defaults.backtest_start);
    }
    if (els.end && config.defaults?.backtest_end) {
      els.end.value = isoToLocalInput(config.defaults.backtest_end);
    }
    if (els.startingBalance) {
      els.startingBalance.value = config.defaults?.starting_balance ?? 1000;
    }

    if (config.auto_run) renderAutoRunStatus(config.auto_run);
  } catch (error) {
    toast(error.message, "error");
  }
}

function renderBacktestTrades(symbols) {
  const rows = (symbols || []).filter((item) => !item.error && item.trade_logs && item.trade_logs.length);
  if (!rows.length) {
    els.backtestTradesWrap.classList.add("hidden");
    els.backtestTradesList.innerHTML = "";
    return;
  }

  els.backtestTradesList.innerHTML = rows
    .map(
      (symbolRow) => `
        <details class="backtest-symbol-trades" open>
          <summary>
            <strong>${escapeHtml(symbolRow.symbol)}</strong>
            <span class="tag">${escapeHtml(symbolRow.name)} · ${escapeHtml(symbolRow.timeframe || "")}</span>
            <span class="backtest-trade-meta">${symbolRow.trade_logs.length} trade${symbolRow.trade_logs.length === 1 ? "" : "s"} · ${formatMoney(symbolRow.pnl)}</span>
          </summary>
          <div class="table-wrap">
            <table class="data-table data-table-compact">
              <thead>
                <tr>
                  <th>Time</th>
                  <th>Side</th>
                  <th>Entry</th>
                  <th>SL</th>
                  <th>TPs</th>
                  <th>Lot/leg</th>
                  <th>Risk $</th>
                  <th>PnL</th>
                  <th>Session</th>
                </tr>
              </thead>
              <tbody>
                ${symbolRow.trade_logs
                  .map(
                    (trade) => `
                      <tr>
                        <td>${formatTimestamp(trade.time)}</td>
                        <td class="side-${trade.side}">${String(trade.side).toUpperCase()}</td>
                        <td>${formatPrice(trade.entry)}</td>
                        <td>${formatPrice(trade.sl)}</td>
                        <td class="trade-tps">${(trade.tps || []).map((tp) => formatPrice(tp)).join(" · ")}</td>
                        <td>${trade.lot_per_leg}</td>
                        <td>${formatMoney(trade.risk_usd)}</td>
                        <td class="${pnlClass(trade.pnl)}">${formatMoney(trade.pnl)}</td>
                        <td>${escapeHtml(trade.session || "—")}</td>
                      </tr>
                    `,
                  )
                  .join("")}
              </tbody>
            </table>
          </div>
        </details>
      `,
    )
    .join("");

  els.backtestTradesWrap.classList.remove("hidden");
}

function renderBacktestDaily(dailyRows) {
  if (!dailyRows || !dailyRows.length) {
    els.backtestDailyWrap.classList.add("hidden");
    els.backtestDailyBody.innerHTML = "";
    return;
  }

  els.backtestDailyBody.innerHTML = dailyRows
    .map(
      (row) => `
        <tr>
          <td><strong>${escapeHtml(row.date)}</strong></td>
          <td>${row.trades}</td>
          <td>${row.wins} / ${row.losses}</td>
          <td class="${pnlClass(row.pnl)}">${formatMoney(row.pnl)}</td>
          <td>${formatMoney(row.balance)}</td>
        </tr>
      `,
    )
    .join("");
  els.backtestDailyWrap.classList.remove("hidden");
}

function renderBacktestResult(data) {
  els.backtestRaw.textContent = JSON.stringify(data, null, 2);

  const totalClass = pnlClass(data.total_pnl);
  const rawSignals = (data.symbols || []).reduce((sum, row) => sum + (row.raw_signals || 0), 0);
  const skippedSignals = (data.symbols || []).reduce((sum, row) => sum + (row.skipped_signals || 0), 0);
  els.backtestSummary.innerHTML = `
    <div class="summary-card">
      <span class="label">Start balance</span>
      <span class="value">${formatMoney(data.starting_balance)}</span>
    </div>
    <div class="summary-card">
      <span class="label">Total PnL</span>
      <span class="value ${totalClass}">${formatMoney(data.total_pnl)}</span>
    </div>
    <div class="summary-card">
      <span class="label">End balance</span>
      <span class="value">${formatMoney(data.end_balance_if_sequential)}</span>
    </div>
    <div class="summary-card">
      <span class="label">Strategy</span>
      <span class="value" style="font-size:0.95rem">${escapeHtml(formatStrategy(data.strategy))}</span>
    </div>
    <div class="summary-card">
      <span class="label">Signal gate</span>
      <span class="value" style="font-size:0.95rem">${rawSignals} raw / ${skippedSignals} skipped</span>
    </div>
  `;
  els.backtestSummary.classList.remove("hidden");
  renderBacktestDaily(data.daily_performance);

  els.backtestBody.innerHTML = (data.symbols || [])
    .map(
      (row) => row.error
        ? `
        <tr>
          <td><strong>${escapeHtml(row.symbol)}</strong><div class="tag">${escapeHtml(row.name)} · ${escapeHtml(row.timeframe || "")}</div></td>
          <td colspan="6" class="value-negative">${escapeHtml(row.error)}</td>
        </tr>
      `
      : `
        <tr>
          <td><strong>${escapeHtml(row.symbol)}</strong><div class="tag">${escapeHtml(row.name)} · ${escapeHtml(row.timeframe || "")}</div></td>
          <td>${row.raw_signals ?? row.trades} raw / ${row.skipped_signals ?? 0} skipped</td>
          <td>${row.trades}</td>
          <td>${row.wins} / ${row.losses}</td>
          <td>${row.win_rate}%</td>
          <td class="${pnlClass(row.pnl)}">${formatMoney(row.pnl)}</td>
          <td>${formatMoney(-row.max_drawdown)}</td>
        </tr>
      `,
    )
    .join("");

  els.backtestTableWrap.classList.remove("hidden");
  renderBacktestTrades(data.symbols);
}

async function loadConfig() {
  const response = await fetch("/api/config", { cache: "no-store" });
  if (!response.ok) throw new Error("Failed to load config");
  const config = await response.json();
  renderConfig(config);
}

async function runBacktest(event) {
  event.preventDefault();

  const start = localInputToIso(els.start.value);
  const end = localInputToIso(els.end.value);
  const strategy = els.strategy.value;
  const startingBalance = Number(els.startingBalance.value);

  if (!Number.isFinite(startingBalance) || startingBalance <= 0) {
    toast("Starting balance must be greater than 0", "error");
    return;
  }

  setLoading(els.backtestBtn, true, "Running backtest…");

  try {
    await syncSymbolSettings({ persist: false, silent: true });
    toast("Backtest running — watch Live logs for progress", "info");
    const response = await fetch(
      `/api/backtest?start=${encodeURIComponent(start)}&end=${encodeURIComponent(end)}&strategy=${encodeURIComponent(strategy)}&starting_balance=${encodeURIComponent(startingBalance)}`,
    );
    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.detail || "Backtest failed");
    }
    renderBacktestResult(data);
    toast("Backtest completed", "success");
    await refreshLogs();
  } catch (error) {
    toast(error.message, "error");
  } finally {
    setLoading(els.backtestBtn, false);
  }
}

async function runOnce() {
  setLoading(els.runOnceBtn, true);
  try {
    await syncSymbolSettings({ persist: false, silent: true });
    const response = await fetch("/api/run-once", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        strategy: els.autoRunStrategy?.value,
        strategy_persist: Boolean(els.autoRunSaveStrategy?.checked),
        persist: false,
      }),
    });
    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.detail || "Scan failed");
    }
    els.status.textContent = JSON.stringify(data, null, 2);
    els.scanResult.classList.remove("hidden");
    toast("Scan complete", "success");
    await refreshLogs();
  } catch (error) {
    toast(error.message, "error");
  } finally {
    setLoading(els.runOnceBtn, false);
  }
}

async function placeManualTrade(event) {
  event.preventDefault();
  const text = els.manualTradeText.value.trim();
  if (!text) {
    toast("Paste a trade signal first", "error");
    return;
  }

  const confirmed = window.confirm(
    "This will place real MT5 market orders with the pasted SL and TPs. Continue?",
  );
  if (!confirmed) return;

  setLoading(els.manualTradeBtn, true, "Sending live trade...");
  try {
    const response = await fetch("/api/manual-trade", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text, confirm_live: true }),
    });
    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.detail || "Manual trade failed");
    }
    els.manualTradeStatus.textContent = JSON.stringify(data, null, 2);
    els.manualTradeResult.classList.remove("hidden");
    const placed = data.tickets?.length || 0;
    const failed = data.failed?.length || 0;
    toast(`Manual trade sent: ${placed} placed, ${failed} failed`, failed ? "error" : "success");
    await refreshLiveData();
    await refreshLogs();
  } catch (error) {
    toast(error.message, "error");
  } finally {
    setLoading(els.manualTradeBtn, false);
  }
}

function startLogPolling() {
  if (logTimer) clearInterval(logTimer);
  logTimer = setInterval(refreshLogs, 1500);
}

async function init() {
  applyPageVisibility();

  window.addEventListener("app:toast", (event) => {
    toast(event.detail.message, event.detail.type || "info");
  });

  els.backtestForm?.addEventListener("submit", runBacktest);
  els.runOnceBtn?.addEventListener("click", runOnce);
  els.manualTradeForm?.addEventListener("submit", placeManualTrade);
  els.saveLotsBtn?.addEventListener("click", saveLots);
  els.symbolsBody?.addEventListener("change", (event) => {
    if (!event.target.matches(".lot-input, .symbol-enabled")) return;
    const row = event.target.closest("tr");
    if (row && event.target.matches(".symbol-enabled")) {
      row.classList.toggle("row-disabled", !event.target.checked);
    }
    scheduleSettingsSync({ persist: false, silent: true });
  });
  els.autoRunStartBtn?.addEventListener("click", startAutoRun);
  els.autoRunStopBtn?.addEventListener("click", stopAutoRun);
  els.autoRunSaveBtn?.addEventListener("click", () => saveBotStrategy());
  els.autoRunStrategy?.addEventListener("change", async () => {
    if (!els.autoRunStartBtn?.disabled) return;
    try {
      await saveBotStrategy({
        persist: Boolean(els.autoRunSaveStrategy?.checked),
        silent: true,
      });
      toast(`Strategy switched to ${formatStrategy(els.autoRunStrategy.value)}`, "info");
      await refreshAutoRunStatus();
    } catch (error) {
      toast(error.message, "error");
    }
  });
  els.telegramStartBtn?.addEventListener("click", startTelegramSignals);
  els.telegramStopBtn?.addEventListener("click", stopTelegramSignals);
  els.telegramClearBtn?.addEventListener("click", clearTelegramMessages);
  els.refreshLogsBtn?.addEventListener("click", refreshLogs);
  els.logFilter?.addEventListener("input", renderLogs);

  startLogPolling();
  startLoopPolling();
  startTelegramPolling();
  startLivePolling();

  window.addEventListener("pageshow", (event) => {
    if (event.persisted) {
      refreshAutoRunStatus();
      refreshLiveData();
    }
  });

  const [configResult] = await Promise.allSettled([
    loadConfig(),
    refreshAutoRunStatus(),
    refreshLiveData(),
    refreshTelegramStatus(),
    refreshLogs(),
  ]);

  if (botConfig && window.ChartPreview) {
    try {
      ChartPreview.initChartPreview(botConfig);
    } catch (error) {
      toast(error.message, "error");
    }
  }

  if (configResult.status === "rejected") {
    toast(configResult.reason?.message || "Failed to load config", "error");
  }
}

init();

const SIGNAL_ALGORITHM_LABELS = {
  rsi_divergence: "RSI divergence",
  silver_optimized: "Silver optimized (XAU/XAG/BTC trend pullback)",
  forex_trade: "Forex trade (RSI mean-reversion)",
};

const STRATEGY_LABELS = {
  signal_no_tp_protection: "Split legs - no TP protection",
  signal_with_tp_protection: "Split legs - with TP protection",
  signal_full_no_tp_protection: "Full position - no TP protection",
  signal_full_with_tp_protection: "Full position - with TP protection",
};

const PAGE_LABELS = {
  home: "Live",
  backtest: "Backtest",
  settings: "Settings",
  "manual-trade": "Manual trade",
  "live-summary": "Live summary",
  "telegram-signals": "Telegram signals",
  "tradlia-signals": "Tradlia signals",
  logs: "Logs",
};

const MOBILE_TABLE_BP = 768;

const STRATEGY_ALIASES = {
  signal_partial_no_tp_protection: "signal_no_tp_protection",
  signal_partial_with_tp_protection: "signal_with_tp_protection",
  trend_pullback: "signal_with_tp_protection",
  supply_demand: "signal_with_tp_protection",
  box_theory: "signal_with_tp_protection",
};

const els = {
  loopBadge: document.getElementById("loop-badge"),
  modeBadge: document.getElementById("mode-badge"),
  accountTypeBadge: document.getElementById("account-type-badge"),
  mt5IsDemoInputs: () => Array.from(document.querySelectorAll("[data-mt5-is-demo-input]")),
  strategyBadge: document.getElementById("strategy-badge"),
  statSymbols: document.getElementById("stat-symbols"),
  statPoll: document.getElementById("stat-poll"),
  statSetups: document.getElementById("stat-setups"),
  statMagic: document.getElementById("stat-magic"),
  symbolsBody: document.getElementById("symbols-body"),
  resetLotsBtn: document.getElementById("reset-lots-btn"),
  defaultForexLot: document.getElementById("default-forex-lot"),
  appendBrokerSymbolSuffix: document.getElementById("append-broker-symbol-suffix"),
  brokerSymbolSuffixHint: document.getElementById("broker-symbol-suffix-hint"),
  resetTimeframesBtn: document.getElementById("reset-timeframes-btn"),
  optimizeTimeframesBtn: document.getElementById("optimize-timeframes-btn"),
  saveLotsBtn: document.getElementById("save-lots-btn"),
  addCustomSymbolForm: document.getElementById("add-custom-symbol-form"),
  addCustomSymbolBtn: document.getElementById("add-custom-symbol-btn"),
  customSymbolKey: document.getElementById("custom-symbol-key"),
  customSymbolName: document.getElementById("custom-symbol-name"),
  customSymbolDemo: document.getElementById("custom-symbol-demo"),
  customSymbolLive: document.getElementById("custom-symbol-live"),
  customSymbolLot: document.getElementById("custom-symbol-lot"),
  customSymbolTimeframe: document.getElementById("custom-symbol-timeframe"),
  customSymbolEnabled: document.getElementById("custom-symbol-enabled"),
  forexTradeForm: document.getElementById("forex-trade-form"),
  forexTradeSaveBtn: document.getElementById("forex-trade-save-btn"),
  forexTradeTimeframe: document.getElementById("forex-trade-timeframe"),
  forexTradeBars: document.getElementById("forex-trade-bars"),
  forexTradeRiskPerTrade: document.getElementById("forex-trade-risk-per-trade"),
  forexTradeMaxSpread: document.getElementById("forex-trade-max-spread"),
  forexTradeRsiPeriod: document.getElementById("forex-trade-rsi-period"),
  forexTradeRsiLongEntry: document.getElementById("forex-trade-rsi-long-entry"),
  forexTradeRsiShortEntry: document.getElementById("forex-trade-rsi-short-entry"),
  forexTradeRsiLongExit: document.getElementById("forex-trade-rsi-long-exit"),
  forexTradeRsiShortExit: document.getElementById("forex-trade-rsi-short-exit"),
  forexTradeStopLossPct: document.getElementById("forex-trade-stop-loss-pct"),
  forexTradeTakeProfitPct: document.getElementById("forex-trade-take-profit-pct"),
  forexTradeTrendEma: document.getElementById("forex-trade-trend-ema"),
  forexTradeSymbolKeys: document.getElementById("forex-trade-symbol-keys"),
  forexTradeUseTrendFilter: document.getElementById("forex-trade-use-trend-filter"),
  forexTradeUseRiskLot: document.getElementById("forex-trade-use-risk-lot"),
  forexTradeUseSpreadFilter: document.getElementById("forex-trade-use-spread-filter"),
  snapshotForm: document.getElementById("snapshot-form"),
  snapshotName: document.getElementById("snapshot-name"),
  snapshotNote: document.getElementById("snapshot-note"),
  snapshotSaveBtn: document.getElementById("snapshot-save-btn"),
  snapshotRefreshBtn: document.getElementById("snapshot-refresh-btn"),
  snapshotApplyPersist: document.getElementById("snapshot-apply-persist"),
  snapshotsBody: document.getElementById("snapshots-body"),
  mt5TestTradeBtn: document.getElementById("mt5-test-trade-btn"),
  mt5TestTradeResult: document.getElementById("mt5-test-trade-result"),
  mt5TestTradeJson: document.getElementById("mt5-test-trade-json"),
  backtestForm: document.getElementById("backtest-form"),
  start: document.getElementById("start"),
  end: document.getElementById("end"),
  startingBalance: document.getElementById("starting-balance"),
  strategy: document.getElementById("strategy"),
  backtestBtn: document.getElementById("backtest-btn"),
  backtestSummary: document.getElementById("backtest-summary"),
  backtestResults: document.getElementById("backtest-results"),
  backtestDailyWrap: document.getElementById("backtest-daily-wrap"),
  backtestDailyBody: document.getElementById("backtest-daily-body"),
  backtestTableWrap: document.getElementById("backtest-table-wrap"),
  backtestBody: document.getElementById("backtest-body"),
  backtestTradesWrap: document.getElementById("backtest-trades-wrap"),
  backtestTradesList: document.getElementById("backtest-trades-list"),
  backtestRaw: document.getElementById("backtest-raw"),
  runOnceBtn: document.getElementById("run-once-btn"),
  manualTradeForm: document.getElementById("manual-trade-form"),
  manualTradeImageDrop: document.getElementById("manual-trade-image-drop"),
  manualTradeImageInput: document.getElementById("manual-trade-image-input"),
  manualTradeImageBtn: document.getElementById("manual-trade-image-btn"),
  manualTradeParseBtn: document.getElementById("manual-trade-parse-btn"),
  manualTradeImagePreview: document.getElementById("manual-trade-image-preview"),
  manualTradeImageName: document.getElementById("manual-trade-image-name"),
  manualTradeParseHint: document.getElementById("manual-trade-parse-hint"),
  manualTradeText: document.getElementById("manual-trade-text"),
  manualTradeBtn: document.getElementById("manual-trade-btn"),
  manualTradeQuickTestEurusdBtn: document.getElementById("manual-trade-quick-test-eurusd-btn"),
  manualTradeQuickTestBtcusdBtn: document.getElementById("manual-trade-quick-test-btcusd-btn"),
  manualTradeResult: document.getElementById("manual-trade-result"),
  manualTradeResultSummary: document.getElementById("manual-trade-result-summary"),
  manualTradeDismissBtn: document.getElementById("manual-trade-dismiss-btn"),
  manualTradeStatus: document.getElementById("manual-trade-status"),
  autoRunStartBtn: document.getElementById("auto-run-start-btn"),
  autoRunStopBtn: document.getElementById("auto-run-stop-btn"),
  autoRunDot: document.getElementById("auto-run-dot"),
  autoRunLabel: document.getElementById("auto-run-label"),
  autoRunScans: document.getElementById("auto-run-scans"),
  autoRunLast: document.getElementById("auto-run-last"),
  autoRunStrategyLabel: document.getElementById("auto-run-strategy-label"),
  autoRunStrategy: document.getElementById("auto-run-strategy"),
  autoRunSignalAlgorithm: document.getElementById("auto-run-signal-algorithm"),
  backtestSignalAlgorithm: document.getElementById("backtest-signal-algorithm"),
  autoRunSaveStrategy: document.getElementById("auto-run-save-strategy"),
  autoRunSaveBtn: document.getElementById("auto-run-save-btn"),
  autoRunHint: document.getElementById("auto-run-hint"),
  dailyLossGuardEnabled: document.getElementById("daily-loss-guard-enabled"),
  dailyLossGuardPct: document.getElementById("daily-loss-guard-pct"),
  dailyLossStatus: document.getElementById("daily-loss-status"),
  dailyWinGuardEnabled: document.getElementById("daily-win-guard-enabled"),
  dailyWinTargetMode: document.getElementById("daily-win-target-mode"),
  dailyWinTargetValue: document.getElementById("daily-win-target-value"),
  dailyWinTargetLabel: document.getElementById("daily-win-target-label"),
  dailyWinStatus: document.getElementById("daily-win-status"),
  dailyGuardResetClock: document.getElementById("daily-guard-reset-clock"),
  telegramDailyLossGuardEnabled: document.getElementById("telegram-daily-loss-guard-enabled"),
  telegramDailyLossGuardPct: document.getElementById("telegram-daily-loss-guard-pct"),
  telegramDailyLossStatus: document.getElementById("telegram-daily-loss-status"),
  telegramDailyWinGuardEnabled: document.getElementById("telegram-daily-win-guard-enabled"),
  telegramDailyWinTargetMode: document.getElementById("telegram-daily-win-target-mode"),
  telegramDailyWinTargetValue: document.getElementById("telegram-daily-win-target-value"),
  telegramDailyWinTargetLabel: document.getElementById("telegram-daily-win-target-label"),
  telegramDailyWinStatus: document.getElementById("telegram-daily-win-status"),
  telegramDailyGuardResetClock: document.getElementById("telegram-daily-guard-reset-clock"),
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
  liveSummaryForm: document.getElementById("live-summary-form"),
  liveSummaryStart: document.getElementById("live-summary-start"),
  liveSummaryEnd: document.getElementById("live-summary-end"),
  liveSummaryBtn: document.getElementById("live-summary-btn"),
  liveSummaryOverall: document.getElementById("live-summary-overall"),
  liveSummaryChart: document.getElementById("live-summary-chart"),
  liveSummarySymbolsWrap: document.getElementById("live-summary-symbols-wrap"),
  liveSummarySymbols: document.getElementById("live-summary-symbols"),
  liveSummaryCount: document.getElementById("live-summary-count"),
  liveSummaryBody: document.getElementById("live-summary-body"),
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
  telegramIgnoreOpen: document.getElementById("telegram-ignore-open"),
  telegramSaveBtn: document.getElementById("telegram-save-btn"),
  telegramStartBtn: document.getElementById("telegram-start-btn"),
  telegramStopBtn: document.getElementById("telegram-stop-btn"),
  telegramClearBtn: document.getElementById("telegram-clear-btn"),
  telegramHint: document.getElementById("telegram-hint"),
  telegramError: document.getElementById("telegram-error"),
  telegramLlm: document.getElementById("telegram-llm"),
  telegramOpenGuard: document.getElementById("telegram-open-guard"),
  telegramChannels: document.getElementById("telegram-channels"),
  telegramChannelsBody: document.getElementById("telegram-channels-body"),
  telegramChannelForm: document.getElementById("telegram-channel-form"),
  telegramChannelUrl: document.getElementById("telegram-channel-url"),
  telegramChannelName: document.getElementById("telegram-channel-name"),
  telegramChannelEnabled: document.getElementById("telegram-channel-enabled"),
  telegramChannelAddBtn: document.getElementById("telegram-channel-add-btn"),
  telegramPoll: document.getElementById("telegram-poll"),
  telegramLastParsed: document.getElementById("telegram-last-parsed"),
  telegramLastAction: document.getElementById("telegram-last-action"),
  telegramLastActionMeta: document.getElementById("telegram-last-action-meta"),
  telegramLastActionStatus: document.getElementById("telegram-last-action-status"),
  telegramLastActionJson: document.getElementById("telegram-last-action-json"),
  telegramActionLogBody: document.getElementById("telegram-action-log-body"),
  telegramLastResult: document.getElementById("telegram-last-result"),
  telegramLastResultJson: document.getElementById("telegram-last-result-json"),
  telegramBrowserHeadless: document.getElementById("telegram-browser-headless"),
  tradliaUpdated: document.getElementById("tradlia-updated"),
  tradliaDot: document.getElementById("tradlia-dot"),
  tradliaLabel: document.getElementById("tradlia-label"),
  tradliaCounts: document.getElementById("tradlia-counts"),
  tradliaLast: document.getElementById("tradlia-last"),
  tradliaStartBtn: document.getElementById("tradlia-start-btn"),
  tradliaStopBtn: document.getElementById("tradlia-stop-btn"),
  tradliaHint: document.getElementById("tradlia-hint"),
  tradliaError: document.getElementById("tradlia-error"),
  tradliaApi: document.getElementById("tradlia-api"),
  tradliaLlm: document.getElementById("tradlia-llm"),
  tradliaPoll: document.getElementById("tradlia-poll"),
  tradliaLastParsed: document.getElementById("tradlia-last-parsed"),
  tradliaLastAction: document.getElementById("tradlia-last-action"),
  tradliaLastActionMeta: document.getElementById("tradlia-last-action-meta"),
  tradliaLastActionStatus: document.getElementById("tradlia-last-action-status"),
  tradliaLastActionJson: document.getElementById("tradlia-last-action-json"),
  tradliaActionLogBody: document.getElementById("tradlia-action-log-body"),
  telegramMessagesByChannel: document.getElementById("telegram-messages-by-channel"),
  toastStack: document.getElementById("toast-stack"),
  navToggle: document.getElementById("nav-toggle"),
  mainNav: document.getElementById("main-nav"),
  mobileNavPage: document.getElementById("mobile-nav-page"),
};

let allLogs = [];
let logTimer = null;
let loopTimer = null;
let liveTimer = null;
let telegramTimer = null;
let tradliaTimer = null;
let telegramMessagesFingerprint = "";
let telegramActionsFingerprint = "";
let telegramExpandedFields = new Set();
let telegramUserInteracting = false;
let botConfig = null;
let manualTradeImageFile = null;
let symbolSettingsReady = false;

function currentPage() {
  const path = window.location.pathname.replace(/\/+$/, "") || "/";
  if (path === "/backtest") return "backtest";
  if (path === "/settings") return "settings";
  if (path === "/manual-trade") return "manual-trade";
  if (path === "/live-summary") return "live-summary";
  if (path === "/telegram-signals") return "telegram-signals";
  if (path === "/tradlia-signals") return "tradlia-signals";
  if (path === "/logs") return "logs";
  return "home";
}

function applyPageVisibility() {
  const page = currentPage();
  document.body.dataset.page = page;
  if (els.mobileNavPage) {
    els.mobileNavPage.textContent = PAGE_LABELS[page] || "Dashboard";
  }

  for (const section of document.querySelectorAll("[data-pages]")) {
    const pages = (section.dataset.pages || "").split(/\s+/).filter(Boolean);
    section.classList.toggle("page-hidden", !pages.includes(page));
  }

  for (const link of document.querySelectorAll("[data-page-link]")) {
    link.classList.toggle("active", link.dataset.pageLink === page);
  }

  closeMobileNav();
  updateResponsiveTables();
}

function closeMobileNav() {
  if (!els.mainNav || !els.navToggle) return;
  els.mainNav.classList.remove("is-open");
  els.navToggle.setAttribute("aria-expanded", "false");
}

function toggleMobileNav() {
  if (!els.mainNav || !els.navToggle) return;
  const open = !els.mainNav.classList.contains("is-open");
  els.mainNav.classList.toggle("is-open", open);
  els.navToggle.setAttribute("aria-expanded", open ? "true" : "false");
}

function stampTableLabels(table) {
  const headers = [...table.querySelectorAll("thead th")].map((th) => {
    const label = th.querySelector(".sort-button span:first-child");
    return (label?.textContent || th.textContent || "").trim();
  });
  table.querySelectorAll("tbody tr").forEach((row) => {
    [...row.children].forEach((cell, index) => {
      if (cell.tagName === "TD" && headers[index]) {
        cell.dataset.label = headers[index];
      }
    });
  });
}

function updateResponsiveTables() {
  const mobile = window.matchMedia(`(max-width: ${MOBILE_TABLE_BP}px)`).matches;
  document.querySelectorAll(".table-wrap").forEach((wrap) => {
    const scrollOnly = wrap.classList.contains("table-wrap-scroll") || wrap.classList.contains("table-wrap-wide");
    wrap.classList.toggle("is-mobile-cards", mobile && !scrollOnly);
    const table = wrap.querySelector("table.data-table");
    if (table && mobile && !scrollOnly) {
      stampTableLabels(table);
    }
    if (scrollOnly) {
      wrap.classList.toggle("can-scroll-x", wrap.scrollWidth > wrap.clientWidth + 4);
    } else {
      wrap.classList.remove("can-scroll-x");
    }
  });
}

let responsiveTablesTimer = null;
function scheduleResponsiveTables() {
  if (responsiveTablesTimer) clearTimeout(responsiveTablesTimer);
  responsiveTablesTimer = setTimeout(updateResponsiveTables, 0);
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

function formatSignalAlgorithm(value) {
  return SIGNAL_ALGORITHM_LABELS[value] || String(value || "rsi_divergence").replaceAll("_", " ");
}

function syncSignalAlgorithmUi(algorithm, { updateSelects = true } = {}) {
  const normalized = algorithm || "rsi_divergence";
  if (updateSelects) {
    if (els.autoRunSignalAlgorithm) els.autoRunSignalAlgorithm.value = normalized;
    if (els.backtestSignalAlgorithm) els.backtestSignalAlgorithm.value = normalized;
  }
  if (botConfig?.bot) botConfig.bot.signal_algorithm = normalized;
}

function formatStrategy(value) {
  const strategy = canonicalStrategy(value);
  return STRATEGY_LABELS[strategy] || strategy.replaceAll("_", " ");
}

function canonicalStrategy(value) {
  const strategy = value || "signal_with_tp_protection";
  return STRATEGY_ALIASES[strategy] || strategy;
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

function formatLossAmount(value) {
  const amount = Math.max(0, Number(value) || 0);
  return `$${amount.toFixed(2)}`;
}

function escapeHtml(text) {
  if (text == null) return "";
  return String(text)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function sortHeader(label, key, type = "text", defaultDir = "") {
  const safeLabel = escapeHtml(label);
  const safeKey = escapeHtml(key);
  const safeType = escapeHtml(type);
  const defaultAttr = defaultDir ? ` data-sort-default="${escapeHtml(defaultDir)}"` : "";
  return `
    <button type="button" class="sort-button" data-sort-key="${safeKey}" data-sort-type="${safeType}"${defaultAttr} title="Sort by ${safeLabel}">
      <span>${safeLabel}</span>
      <span class="sort-indicator" aria-hidden="true">-</span>
    </button>
  `;
}

function sortValue(row, key, type) {
  const raw = row.getAttribute(`data-sort-${key}`) ?? "";
  if (type === "number") {
    const value = Number(raw);
    return Number.isFinite(value) ? value : null;
  }
  if (type === "date") {
    const value = Date.parse(raw);
    return Number.isFinite(value) ? value : null;
  }
  return raw.toLowerCase();
}

function compareSortValues(left, right, type, direction) {
  const leftMissing = left === null || left === "";
  const rightMissing = right === null || right === "";
  if (leftMissing && rightMissing) return 0;
  if (leftMissing) return 1;
  if (rightMissing) return -1;
  const comparison = type === "text" ? String(left).localeCompare(String(right)) : Number(left) - Number(right);
  return direction === "asc" ? comparison : -comparison;
}

function applySortableTableSort(button) {
  const table = button.closest("table");
  const tbody = table?.tBodies?.[0];
  if (!table || !tbody) return;

  const key = button.dataset.sortKey;
  const type = button.dataset.sortType || "text";
  if (!key) return;

  const sameColumn = table.dataset.sortKey === key;
  const defaultDir = button.dataset.sortDefault || (type === "text" ? "asc" : "desc");
  const direction = sameColumn && table.dataset.sortDir === "asc" ? "desc" : sameColumn ? "asc" : defaultDir;
  const allRows = Array.from(tbody.rows);
  const pairMode = table.dataset.sortPairs === "true";
  const sortableRows = allRows.filter((row) => row.dataset.sortRow === "true");

  const compareRows = (leftRow, rightRow) => {
    const left = sortValue(leftRow, key, type);
    const right = sortValue(rightRow, key, type);
    const comparison = compareSortValues(left, right, type, direction);
    if (comparison !== 0) return comparison;
    return Number(leftRow.dataset.sortIndex || 0) - Number(rightRow.dataset.sortIndex || 0);
  };

  if (pairMode) {
    const groups = sortableRows.map((row) => {
      const detail = row.nextElementSibling?.classList.contains("backtest-daily-detail")
        ? row.nextElementSibling
        : null;
      return { row, detail };
    });
    groups.sort((left, right) => compareRows(left.row, right.row));
    tbody.replaceChildren(...groups.flatMap((group) => (group.detail ? [group.row, group.detail] : [group.row])));
  } else {
    const staticRows = allRows.filter((row) => row.dataset.sortRow !== "true");
    sortableRows.sort(compareRows);
    tbody.replaceChildren(...staticRows, ...sortableRows);
  }

  table.dataset.sortKey = key;
  table.dataset.sortDir = direction;

  for (const headerButton of table.querySelectorAll(".sort-button")) {
    const active = headerButton === button;
    headerButton.classList.toggle("is-sorted", active);
    headerButton.setAttribute("aria-pressed", active ? "true" : "false");
    const indicator = headerButton.querySelector(".sort-indicator");
    if (indicator) indicator.textContent = active ? (direction === "asc" ? "^" : "v") : "-";
  }

  Array.from(tbody.querySelectorAll(".row-number")).forEach((cell, index) => {
    cell.textContent = String(index + 1);
  });
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

const SYMBOL_GROUPS = [
  ["crypto", "Crypto"],
  ["forex", "Forex"],
  ["metals", "Gold / Silver"],
  ["commodities", "Oil / Other"],
  ["other", "Other"],
];

function timeframeOptions() {
  const options = botConfig?.timeframe_options || [];
  if (options.length) return options;
  return ["M1", "M5", "M15", "M30", "H1"].map((value) => ({ value, label: value }));
}

function renderTimeframeOptions(selected) {
  return timeframeOptions()
    .map((item) => {
      const value = item.value || item;
      const label = item.label || value;
      return `<option value="${escapeHtml(value)}" ${value === selected ? "selected" : ""}>${escapeHtml(label)}</option>`;
    })
    .join("");
}

function renderTimeframeOptions(selected) {
  return timeframeOptions()
    .map((item) => {
      const value = item.value || item;
      const label = item.label || value;
      return `<option value="${escapeHtml(value)}" ${value === selected ? "selected" : ""}>${escapeHtml(label)}</option>`;
    })
    .join("");
}

function populateForexTradeTimeframeSelect(selected = "H1") {
  if (!els.forexTradeTimeframe) return;
  els.forexTradeTimeframe.innerHTML = renderTimeframeOptions(selected);
}

function syncForexTradeSettingsFromConfig(cfg) {
  if (!cfg) return;
  populateForexTradeTimeframeSelect(cfg.timeframe || "H1");
  if (els.forexTradeTimeframe) els.forexTradeTimeframe.value = cfg.timeframe || "H1";
  if (els.forexTradeBars && cfg.bars != null) els.forexTradeBars.value = cfg.bars;
  if (els.forexTradeRiskPerTrade && cfg.risk_per_trade != null) {
    els.forexTradeRiskPerTrade.value = cfg.risk_per_trade;
  }
  if (els.forexTradeMaxSpread && cfg.max_spread_points != null) {
    els.forexTradeMaxSpread.value = cfg.max_spread_points;
  }
  if (els.forexTradeRsiPeriod && cfg.rsi_period != null) els.forexTradeRsiPeriod.value = cfg.rsi_period;
  if (els.forexTradeRsiLongEntry && cfg.rsi_long_entry != null) {
    els.forexTradeRsiLongEntry.value = cfg.rsi_long_entry;
  }
  if (els.forexTradeRsiShortEntry && cfg.rsi_short_entry != null) {
    els.forexTradeRsiShortEntry.value = cfg.rsi_short_entry;
  }
  if (els.forexTradeRsiLongExit && cfg.rsi_long_exit != null) {
    els.forexTradeRsiLongExit.value = cfg.rsi_long_exit;
  }
  if (els.forexTradeRsiShortExit && cfg.rsi_short_exit != null) {
    els.forexTradeRsiShortExit.value = cfg.rsi_short_exit;
  }
  if (els.forexTradeStopLossPct && cfg.stop_loss_pct != null) {
    els.forexTradeStopLossPct.value = Number((cfg.stop_loss_pct * 100).toFixed(2));
  }
  if (els.forexTradeTakeProfitPct && cfg.take_profit_pct != null) {
    els.forexTradeTakeProfitPct.value = Number((cfg.take_profit_pct * 100).toFixed(2));
  }
  if (els.forexTradeTrendEma && cfg.trend_ema_period != null) {
    els.forexTradeTrendEma.value = cfg.trend_ema_period;
  }
  if (els.forexTradeSymbolKeys && Array.isArray(cfg.symbol_keys)) {
    els.forexTradeSymbolKeys.value = cfg.symbol_keys.join(", ");
  }
  if (els.forexTradeUseTrendFilter) els.forexTradeUseTrendFilter.checked = Boolean(cfg.use_trend_filter);
  if (els.forexTradeUseRiskLot) els.forexTradeUseRiskLot.checked = cfg.use_risk_based_lot !== false;
  if (els.forexTradeUseSpreadFilter) els.forexTradeUseSpreadFilter.checked = cfg.use_spread_filter !== false;
}

function collectForexTradeSettings() {
  const symbolKeysRaw = els.forexTradeSymbolKeys?.value || "";
  const symbol_keys = symbolKeysRaw
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
  return {
    timeframe: els.forexTradeTimeframe?.value || "H1",
    bars: Number(els.forexTradeBars?.value),
    risk_per_trade: Number(els.forexTradeRiskPerTrade?.value),
    max_spread_points: Number(els.forexTradeMaxSpread?.value),
    rsi_period: Number(els.forexTradeRsiPeriod?.value),
    rsi_long_entry: Number(els.forexTradeRsiLongEntry?.value),
    rsi_short_entry: Number(els.forexTradeRsiShortEntry?.value),
    rsi_long_exit: Number(els.forexTradeRsiLongExit?.value),
    rsi_short_exit: Number(els.forexTradeRsiShortExit?.value),
    stop_loss_pct: Number(els.forexTradeStopLossPct?.value) / 100,
    take_profit_pct: Number(els.forexTradeTakeProfitPct?.value) / 100,
    use_trend_filter: Boolean(els.forexTradeUseTrendFilter?.checked),
    trend_ema_period: Number(els.forexTradeTrendEma?.value),
    symbol_keys,
    use_risk_based_lot: Boolean(els.forexTradeUseRiskLot?.checked),
    use_spread_filter: Boolean(els.forexTradeUseSpreadFilter?.checked),
    persist: true,
  };
}

async function saveForexTradeSettings({ silent = false } = {}) {
  setLoading(els.forexTradeSaveBtn, true, "Saving…");
  try {
    const response = await fetch("/api/forex-trade/settings", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(collectForexTradeSettings()),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(formatApiError(data.detail) || "Failed to save forex settings");
    if (data.forex_trade) {
      botConfig = botConfig || {};
      botConfig.bot = botConfig.bot || {};
      botConfig.bot.forex_trade = data.forex_trade;
      syncForexTradeSettingsFromConfig(data.forex_trade);
    }
    if (!silent) toast("Forex trade settings saved to config.yaml", "success");
  } catch (error) {
    toast(error.message, "error");
    throw error;
  } finally {
    setLoading(els.forexTradeSaveBtn, false);
  }
}

async function loadForexTradeSettings() {
  const [settingsResp, configResp] = await Promise.all([
    fetch("/api/forex-trade/settings", { cache: "no-store" }),
    fetch("/api/config", { cache: "no-store" }),
  ]);
  if (!settingsResp.ok) throw new Error("Failed to load forex trade settings");
  const settings = await settingsResp.json();
  if (configResp.ok) {
    const config = await configResp.json();
    botConfig = botConfig || {};
    botConfig.timeframe_options = config.timeframe_options || botConfig.timeframe_options;
    botConfig.bot = { ...(botConfig.bot || {}), ...(config.bot || {}), forex_trade: settings };
  }
  syncForexTradeSettingsFromConfig(settings);
}

function symbolGroupLabel(group) {
  return SYMBOL_GROUPS.find(([key]) => key === group)?.[1] || "Other";
}

function renderGroupedSymbolRow(item) {
  return `
        <tr class="${item.enabled ? "" : "row-disabled"}${!item.signal_active ? " row-signal-inactive" : ""}">
          <td>
            <label class="switch" title="${item.enabled ? "Bot scans this symbol" : "Bot scan off"}">
              <input
                class="symbol-enabled"
                type="checkbox"
                data-symbol="${escapeHtml(item.symbol)}"
                ${item.enabled ? "checked" : ""}
              >
              <span class="switch-slider"></span>
            </label>
          </td>
          <td>
            <label class="switch" title="${item.signal_active !== false ? "Telegram/Tradlia may copy" : "Signal copy off"}">
              <input
                class="symbol-signal-active"
                type="checkbox"
                data-symbol="${escapeHtml(item.symbol)}"
                ${item.signal_active !== false ? "checked" : ""}
              >
              <span class="switch-slider"></span>
            </label>
          </td>
          <td><span class="tag">${escapeHtml(item.market_key || item.symbol)}</span></td>
          <td>
            <input
              class="demo-symbol-input mono"
              type="text"
              data-symbol="${escapeHtml(item.symbol)}"
              value="${escapeHtml(item.demo_symbol || item.symbol)}"
              title="MT5 symbol on demo accounts"
            >
          </td>
          <td>
            <input
              class="live-symbol-input mono"
              type="text"
              data-symbol="${escapeHtml(item.symbol)}"
              value="${escapeHtml(item.live_symbol || item.symbol)}"
              title="MT5 symbol on live accounts"
            >
          </td>
          <td>
            <select
              class="timeframe-select"
              data-symbol="${escapeHtml(item.symbol)}"
              data-reset-timeframe="${escapeHtml(item.reset_timeframe || item.timeframe)}"
              title="Reset timeframe: ${escapeHtml(item.reset_timeframe || item.timeframe)}"
            >
              ${renderTimeframeOptions(item.timeframe)}
            </select>
          </td>
          <td>
            <input
              class="lot-input"
              type="number"
              min="0.01"
              step="0.01"
              data-symbol="${escapeHtml(item.symbol)}"
              data-reset-lot="${item.reset_lot_per_leg ?? item.lot_per_leg}"
              title="Reset lot: ${item.reset_lot_per_leg ?? item.lot_per_leg}"
              value="${item.lot_per_leg}"
            >
          </td>
          <td>${escapeHtml(item.confirmation)}</td>
          <td>${(item.sessions || []).map((s) => `<span class="tag">${escapeHtml(s)}</span>`).join("") || "—"}</td>
        </tr>
      `;
}

function renderSymbols(symbols) {
  if (!els.symbolsBody) return;

  const rows = Array.isArray(symbols) ? symbols : [];
  if (!rows.length) {
    els.symbolsBody.innerHTML = '<tr><td colspan="8" class="empty-row">No symbols in config.</td></tr>';
    scheduleResponsiveTables();
    return;
  }

  const grouped = new Map(SYMBOL_GROUPS.map(([key]) => [key, []]));
  for (const item of rows) {
    const group = grouped.has(item.asset_group) ? item.asset_group : "other";
    grouped.get(group).push(item);
  }

  els.symbolsBody.innerHTML = SYMBOL_GROUPS
    .flatMap(([group]) => {
      const items = grouped.get(group) || [];
      if (!items.length) return [];
      return [
        `<tr class="symbol-section-row"><td colspan="8"><span>${escapeHtml(symbolGroupLabel(group))}</span><small>${items.length} symbols</small></td></tr>`,
        ...items.map(renderGroupedSymbolRow),
      ];
    })
    .join("");
  scheduleResponsiveTables();
}

function updateSymbolStats(stats) {
  if (!stats) return;
  els.statSymbols.textContent = `${stats.enabled} / ${stats.total}`;
}

function symbolSettingsFromConfig() {
  const lots = {};
  const enabled = {};
  const signal_active = {};
  const timeframes = {};
  const demo_symbols = {};
  const live_symbols = {};
  for (const item of botConfig?.symbols || []) {
    lots[item.symbol] = item.lot_per_leg;
    enabled[item.symbol] = Boolean(item.enabled);
    signal_active[item.symbol] = item.signal_active !== false;
    timeframes[item.symbol] = item.timeframe;
    demo_symbols[item.symbol] = item.demo_symbol || item.symbol;
    live_symbols[item.symbol] = item.live_symbol || item.symbol;
  }
  return { lots, enabled, signal_active, timeframes, demo_symbols, live_symbols };
}

function collectSymbolSettings() {
  const lots = {};
  const enabled = {};
  const signal_active = {};
  const timeframes = {};
  const demo_symbols = {};
  const live_symbols = {};
  const lotInputs = els.symbolsBody.querySelectorAll(".lot-input");
  const enabledInputs = els.symbolsBody.querySelectorAll(".symbol-enabled");
  const signalActiveInputs = els.symbolsBody.querySelectorAll(".symbol-signal-active");
  const timeframeInputs = els.symbolsBody.querySelectorAll(".timeframe-select");
  const demoInputs = els.symbolsBody.querySelectorAll(".demo-symbol-input");
  const liveInputs = els.symbolsBody.querySelectorAll(".live-symbol-input");

  if (
    !lotInputs.length
    && !enabledInputs.length
    && !signalActiveInputs.length
    && !timeframeInputs.length
    && !demoInputs.length
    && !liveInputs.length
  ) {
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

  for (const input of signalActiveInputs) {
    const symbol = input.dataset.symbol;
    if (!symbol) continue;
    signal_active[symbol] = input.checked;
  }

  for (const input of timeframeInputs) {
    const symbol = input.dataset.symbol;
    if (!symbol || !input.value) {
      throw new Error(`Invalid timeframe for ${symbol || "symbol"}`);
    }
    timeframes[symbol] = input.value;
  }

  for (const input of demoInputs) {
    const symbol = input.dataset.symbol;
    const value = input.value?.trim();
    if (!symbol || !value) {
      throw new Error(`Invalid demo symbol for ${symbol || "symbol"}`);
    }
    demo_symbols[symbol] = value;
  }

  for (const input of liveInputs) {
    const symbol = input.dataset.symbol;
    const value = input.value?.trim();
    if (!symbol || !value) {
      throw new Error(`Invalid live symbol for ${symbol || "symbol"}`);
    }
    live_symbols[symbol] = value;
  }

  if (
    !Object.keys(lots).length
    || !Object.keys(enabled).length
    || !Object.keys(timeframes).length
    || !Object.keys(demo_symbols).length
    || !Object.keys(live_symbols).length
  ) {
    const fallback = symbolSettingsFromConfig();
    if (!Object.keys(lots).length) Object.assign(lots, fallback.lots);
    if (!Object.keys(enabled).length) Object.assign(enabled, fallback.enabled);
    if (!Object.keys(signal_active).length) Object.assign(signal_active, fallback.signal_active);
    if (!Object.keys(timeframes).length) Object.assign(timeframes, fallback.timeframes);
    if (!Object.keys(demo_symbols).length) Object.assign(demo_symbols, fallback.demo_symbols);
    if (!Object.keys(live_symbols).length) Object.assign(live_symbols, fallback.live_symbols);
  }

  return { lots, enabled, signal_active, timeframes, demo_symbols, live_symbols };
}

function defaultForexLotFromUi() {
  const value = Number(els.defaultForexLot?.value);
  return Number.isFinite(value) && value > 0 ? value : undefined;
}

function appendBrokerSymbolSuffixFromUi() {
  if (!els.appendBrokerSymbolSuffix) return undefined;
  return Boolean(els.appendBrokerSymbolSuffix.checked);
}

function mt5IsDemoFromUi() {
  const preferred = document.getElementById("settings-mt5-is-demo") || document.getElementById("mt5-is-demo");
  if (preferred instanceof HTMLInputElement) return Boolean(preferred.checked);
  const input = els.mt5IsDemoInputs().find((node) => node instanceof HTMLInputElement);
  if (!input) return undefined;
  return Boolean(input.checked);
}

function syncMt5IsDemoInputs(isDemo) {
  for (const input of els.mt5IsDemoInputs()) {
    if (input instanceof HTMLInputElement) {
      input.checked = Boolean(isDemo);
    }
  }
}

function updateAccountTypeBadge(configLike = botConfig) {
  if (!els.accountTypeBadge) return;
  const isDemo = configLike?.mt5?.is_demo !== false;
  els.accountTypeBadge.textContent = isDemo ? "Demo symbols" : "Live symbols";
  els.accountTypeBadge.className = `badge ${isDemo ? "badge-warn" : "badge-live"}`;
}

function updateBrokerSymbolSuffixHint(configLike = botConfig) {
  if (!els.brokerSymbolSuffixHint) return;
  const suffix = configLike?.mt5?.broker_symbol_suffix || "-VIP";
  const appendTag = configLike?.mt5?.append_broker_symbol_suffix !== false;
  if (appendTag) {
    els.brokerSymbolSuffixHint.textContent =
      "Broker tag on: fallback suffix for unknown symbols only. Configured demo/live symbol names take priority on each account.";
  } else {
    els.brokerSymbolSuffixHint.textContent =
      "Broker tag off: unknown symbols use plain names (BTCUSD). Configured demo/live symbol names are always used when set.";
  }
}

function formatApiError(detail) {
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail.map((item) => item.msg || JSON.stringify(item)).join("; ");
  }
  return "Request failed";
}

async function syncMt5IsDemoSetting({ persist = true, silent = false } = {}) {
  const isDemo = mt5IsDemoFromUi();
  if (isDemo === undefined) return null;

  const response = await fetch("/api/symbols/settings", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ is_demo: isDemo, persist }),
  });
  const data = await response.json();
  if (!response.ok) throw new Error(formatApiError(data.detail) || "Failed to save demo account setting");

  if (botConfig) {
    botConfig.mt5 = botConfig.mt5 || {};
    botConfig.mt5.is_demo = Boolean(data.is_demo);
    syncMt5IsDemoInputs(data.is_demo);
    updateAccountTypeBadge(botConfig);
  }
  if (!silent) {
    toast(
      data.is_demo ? "Using demo symbol names — saved to config.yaml" : "Using live symbol names — saved to config.yaml",
      "success",
    );
    await refreshLogs();
  }
  return data;
}

async function syncSymbolSettings({ persist = true, silent = false, rerender = false } = {}) {
  const { lots, enabled, signal_active, timeframes, demo_symbols, live_symbols } = collectSymbolSettings();
  const defaultForexLot = defaultForexLotFromUi();
  const appendBrokerSymbolSuffix = appendBrokerSymbolSuffixFromUi();
  if (
    !Object.keys(lots).length
    && !Object.keys(enabled).length
    && !Object.keys(signal_active).length
    && !Object.keys(timeframes).length
    && !Object.keys(demo_symbols).length
    && !Object.keys(live_symbols).length
    && defaultForexLot === undefined
    && appendBrokerSymbolSuffix === undefined
  ) {
    return { status: "noop", symbols: botConfig?.symbols || [], symbol_stats: botConfig?.symbol_stats || null };
  }

  const response = await fetch("/api/symbols/settings", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      lots,
      enabled,
      signal_active,
      timeframes,
      demo_symbols,
      live_symbols,
      default_forex_lot: defaultForexLot,
      append_broker_symbol_suffix: appendBrokerSymbolSuffix,
      persist,
    }),
  });
  const data = await response.json();
  if (!response.ok) throw new Error(formatApiError(data.detail) || "Failed to sync symbol settings");

  if (botConfig) {
    botConfig.symbols = data.symbols;
    botConfig.symbol_stats = data.symbol_stats;
    if (data.default_forex_lot != null) {
      botConfig.risk = botConfig.risk || {};
      botConfig.risk.default_forex_lot = data.default_forex_lot;
      if (els.defaultForexLot) els.defaultForexLot.value = data.default_forex_lot;
    }
    if (data.append_broker_symbol_suffix != null) {
      botConfig.mt5 = botConfig.mt5 || {};
      botConfig.mt5.append_broker_symbol_suffix = data.append_broker_symbol_suffix;
      if (els.appendBrokerSymbolSuffix) {
        els.appendBrokerSymbolSuffix.checked = Boolean(data.append_broker_symbol_suffix);
      }
    }
    if (data.broker_symbol_suffix) {
      botConfig.mt5 = botConfig.mt5 || {};
      botConfig.mt5.broker_symbol_suffix = data.broker_symbol_suffix;
    }
    if (data.is_demo != null) {
      botConfig.mt5 = botConfig.mt5 || {};
      botConfig.mt5.is_demo = Boolean(data.is_demo);
      syncMt5IsDemoInputs(data.is_demo);
      updateAccountTypeBadge(botConfig);
    }
    updateBrokerSymbolSuffixHint(botConfig);
  }
  updateSymbolStats(data.symbol_stats);
  if (rerender || !silent) renderSymbols(data.symbols);
  if (window.ChartPreview?.populateSymbols) {
    window.ChartPreview.populateSymbols(data.symbols);
  }

  if (!silent) {
    toast(persist ? "Symbol settings saved to config" : "Symbol settings applied", "success");
    await refreshLogs();
  }

  return data;
}

async function addCustomSymbol(event) {
  event.preventDefault();
  const symbol = els.customSymbolKey?.value?.trim();
  if (!symbol) {
    toast("Market key is required", "error");
    return;
  }

  const lotRaw = els.customSymbolLot?.value?.trim();
  const payload = {
    symbol,
    name: els.customSymbolName?.value?.trim() || null,
    demo_symbol: els.customSymbolDemo?.value?.trim() || null,
    live_symbol: els.customSymbolLive?.value?.trim() || null,
    timeframe: els.customSymbolTimeframe?.value || "M5",
    enabled: Boolean(els.customSymbolEnabled?.checked),
    persist: true,
  };
  if (lotRaw) {
    const lot = Number(lotRaw);
    if (!Number.isFinite(lot) || lot <= 0) {
      toast("Lot size must be a positive number", "error");
      return;
    }
    payload.lot_per_leg = lot;
  }

  setLoading(els.addCustomSymbolBtn, true);
  try {
    const response = await fetch("/api/symbols/add", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || "Failed to add symbol");

    if (botConfig) {
      botConfig.symbols = data.symbols;
      botConfig.symbol_stats = data.symbol_stats;
    }
    renderSymbols(data.symbols);
    updateSymbolStats(data.symbol_stats);
    if (window.ChartPreview?.populateSymbols) {
      window.ChartPreview.populateSymbols(data.symbols);
    }

    els.customSymbolKey.value = "";
    if (els.customSymbolName) els.customSymbolName.value = "";
    if (els.customSymbolDemo) els.customSymbolDemo.value = "";
    if (els.customSymbolLive) els.customSymbolLive.value = "";
    if (els.customSymbolLot) els.customSymbolLot.value = "";
    if (els.customSymbolTimeframe) els.customSymbolTimeframe.value = "M5";
    if (els.customSymbolEnabled) els.customSymbolEnabled.checked = true;

    toast(`Added ${symbol} to config`, "success");
    await refreshLogs();
  } catch (error) {
    toast(error.message, "error");
  } finally {
    setLoading(els.addCustomSymbolBtn, false);
  }
}

let settingsTimer = null;

function scheduleSettingsSync({ persist = false, silent = true, rerender = false } = {}) {
  if (!symbolSettingsReady) return;
  if (settingsTimer) clearTimeout(settingsTimer);
  settingsTimer = setTimeout(async () => {
    try {
      await syncSymbolSettings({ persist, silent, rerender });
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

function formatSnapshotTime(value) {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString();
}

function renderSnapshots(snapshots) {
  if (!els.snapshotsBody) return;
  if (!snapshots?.length) {
    els.snapshotsBody.innerHTML = '<tr><td colspan="6" class="empty-row">No saved snapshots yet.</td></tr>';
    scheduleResponsiveTables();
    return;
  }

  els.snapshotsBody.innerHTML = snapshots
    .map((item) => {
      const summary = item.summary || {};
      const note = item.note ? `<div class="tag">${escapeHtml(item.note)}</div>` : "";
      return `
        <tr data-slug="${escapeHtml(item.slug)}">
          <td>
            <strong>${escapeHtml(item.name)}</strong>
            ${note}
          </td>
          <td>${escapeHtml(formatStrategy(summary.strategy || "—"))}</td>
          <td>${summary.dry_run ? "Dry run" : "Live"}</td>
          <td>${summary.enabled_symbols ?? "—"} / ${summary.total_symbols ?? "—"}</td>
          <td>${escapeHtml(formatSnapshotTime(item.updated_at))}</td>
          <td class="snapshot-actions">
            <button class="btn btn-secondary btn-sm snapshot-apply-btn" type="button" data-slug="${escapeHtml(item.slug)}" data-name="${escapeHtml(item.name)}">Apply</button>
            <button class="btn btn-ghost btn-sm snapshot-delete-btn" type="button" data-slug="${escapeHtml(item.slug)}" data-name="${escapeHtml(item.name)}">Delete</button>
          </td>
        </tr>
      `;
    })
    .join("");
  scheduleResponsiveTables();
}

async function loadSnapshots() {
  if (!els.snapshotsBody) return [];
  const response = await fetch("/api/config/snapshots", { cache: "no-store" });
  const data = await response.json();
  if (!response.ok) throw new Error(formatApiError(data.detail) || "Failed to load snapshots");
  renderSnapshots(data.snapshots || []);
  return data.snapshots || [];
}

async function saveSnapshot(event) {
  event.preventDefault();
  const name = els.snapshotName?.value?.trim();
  if (!name) {
    toast("Enter a snapshot name", "error");
    return;
  }

  setLoading(els.snapshotSaveBtn, true);
  try {
    await syncSymbolSettings({ persist: false, silent: true, rerender: false });
    const response = await fetch("/api/config/snapshots", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        name,
        note: els.snapshotNote?.value?.trim() || "",
      }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(formatApiError(data.detail) || "Failed to save snapshot");

    if (els.snapshotName) els.snapshotName.value = "";
    if (els.snapshotNote) els.snapshotNote.value = "";
    await loadSnapshots();
    toast(`Snapshot saved: ${data.snapshot?.name || name}`, "success");
    await refreshLogs();
  } catch (error) {
    toast(error.message, "error");
  } finally {
    setLoading(els.snapshotSaveBtn, false);
  }
}

async function applySnapshot(slug, name) {
  const persist = Boolean(els.snapshotApplyPersist?.checked);
  const persistText = persist ? " and write to config.yaml" : " in memory only";
  const confirmed = window.confirm(`Apply snapshot "${name}"${persistText}?`);
  if (!confirmed) return;

  const row = els.snapshotsBody?.querySelector(`tr[data-slug="${CSS.escape(slug)}"]`);
  const button = row?.querySelector(".snapshot-apply-btn");
  setLoading(button, true, "Applying...");
  try {
    const response = await fetch(`/api/config/snapshots/${encodeURIComponent(slug)}/apply`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ persist }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(formatApiError(data.detail) || "Failed to apply snapshot");

    if (botConfig) {
      botConfig.symbols = data.symbols;
      botConfig.symbol_stats = data.symbol_stats;
    }
    await loadConfig();
    await refreshAutoRunStatus();
    toast(
      persist
        ? `Snapshot applied and saved: ${name}`
        : `Snapshot applied in memory: ${name}`,
      "success",
    );
    await refreshLogs();
  } catch (error) {
    toast(error.message, "error");
  } finally {
    setLoading(button, false);
  }
}

async function deleteSnapshot(slug, name) {
  const confirmed = window.confirm(`Delete snapshot "${name}"? This cannot be undone.`);
  if (!confirmed) return;

  const row = els.snapshotsBody?.querySelector(`tr[data-slug="${CSS.escape(slug)}"]`);
  const button = row?.querySelector(".snapshot-delete-btn");
  setLoading(button, true, "Deleting...");
  try {
    const response = await fetch(`/api/config/snapshots/${encodeURIComponent(slug)}`, {
      method: "DELETE",
    });
    const data = await response.json();
    if (!response.ok) throw new Error(formatApiError(data.detail) || "Failed to delete snapshot");
    await loadSnapshots();
    toast(`Snapshot deleted: ${name}`, "success");
    await refreshLogs();
  } catch (error) {
    toast(error.message, "error");
  } finally {
    setLoading(button, false);
  }
}

async function refreshSnapshots() {
  setLoading(els.snapshotRefreshBtn, true);
  try {
    await loadSnapshots();
  } catch (error) {
    toast(error.message, "error");
  } finally {
    setLoading(els.snapshotRefreshBtn, false);
  }
}

function renderMt5TestTradeResult(data) {
  if (!els.mt5TestTradeResult || !els.mt5TestTradeJson) return;
  els.mt5TestTradeJson.textContent = JSON.stringify(data, null, 2);
  els.mt5TestTradeResult.classList.remove("hidden");
}

function isLiveTradingMode() {
  if (botConfig?.bot?.dry_run != null) return !botConfig.bot.dry_run;
  return false;
}

async function placeMt5TestTrade() {
  const live = isLiveTradingMode();
  const confirmed = window.confirm(
    live
      ? "Place LIVE XAUUSD 0.01 BUY test trade on the MT5 account from config.yaml? No SL/TP — close manually in MT5."
      : "Place paper XAUUSD 0.01 BUY test trade?",
  );
  if (!confirmed) return;

  setLoading(els.mt5TestTradeBtn, true);
  try {
    const response = await fetch("/api/mt5/test-trade", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        symbol: "XAUUSD",
        side: "buy",
        volume: 0.01,
        confirm_live: live,
      }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(formatApiError(data.detail) || "Test trade failed");
    renderMt5TestTradeResult(data);
    if (data.status === "placed" || data.status === "paper") {
      toast(`Test trade ${data.status}`, "success");
    } else {
      toast(data.reason || "Test trade failed", "error");
    }
    await refreshLogs();
  } catch (error) {
    toast(error.message, "error");
  } finally {
    setLoading(els.mt5TestTradeBtn, false);
  }
}

async function resetLots() {
  if (!botConfig?.symbols?.length) {
    toast("Symbol settings are not loaded yet", "error");
    return;
  }

  const confirmed = window.confirm("Reset all lots to the default safe table and save config.yaml?");
  if (!confirmed) return;

  if (settingsTimer) {
    clearTimeout(settingsTimer);
    settingsTimer = null;
  }

  setLoading(els.resetLotsBtn, true, "Resetting...");
  try {
    for (const input of els.symbolsBody.querySelectorAll(".lot-input")) {
      const symbol = input.dataset.symbol;
      const item = botConfig.symbols.find((row) => row.symbol === symbol);
      const resetLot = Number(item?.reset_lot_per_leg ?? input.dataset.resetLot);
      if (Number.isFinite(resetLot) && resetLot > 0) {
        input.value = resetLot;
      }
    }
    await syncSymbolSettings({ persist: true, silent: false, rerender: true });
    toast("Lots reset to safe defaults", "success");
  } catch (error) {
    toast(error.message, "error");
  } finally {
    setLoading(els.resetLotsBtn, false);
  }
}

async function resetTimeframes() {
  if (!botConfig?.symbols?.length) {
    toast("Symbol settings are not loaded yet", "error");
    return;
  }

  const confirmed = window.confirm("Reset all symbols to their saved optimized timeframes and save config.yaml?");
  if (!confirmed) return;

  if (settingsTimer) {
    clearTimeout(settingsTimer);
    settingsTimer = null;
  }

  setLoading(els.resetTimeframesBtn, true, "Resetting...");
  try {
    const response = await fetch("/api/symbols/timeframes/reset", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ persist: true }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(formatApiError(data.detail) || "Failed to reset timeframes");
    if (botConfig) {
      botConfig.symbols = data.symbols;
      botConfig.symbol_stats = data.symbol_stats;
    }
    renderSymbols(data.symbols);
    toast("Timeframes reset", "success");
    await refreshLogs();
  } catch (error) {
    toast(error.message, "error");
  } finally {
    setLoading(els.resetTimeframesBtn, false);
  }
}

async function optimizeTimeframes() {
  if (!botConfig?.symbols?.length) {
    toast("Symbol settings are not loaded yet", "error");
    return;
  }

  const confirmed = window.confirm(
    "Backtest every enabled symbol across all MT5 timeframes for the last 30 days, save the best timeframe as default, and update config.yaml? This can take a while.",
  );
  if (!confirmed) return;

  const end = new Date();
  const start = new Date(end.getTime() - 30 * 24 * 60 * 60 * 1000);
  setLoading(els.optimizeTimeframesBtn, true, "Optimizing...");
  try {
    await syncSymbolSettings({ persist: false, silent: true, rerender: false });
    const response = await fetch("/api/symbols/timeframes/optimize", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        start: start.toISOString(),
        end: end.toISOString(),
        starting_balance: 1000,
        timeframes: timeframeOptions().map((item) => item.value || item),
        persist: true,
      }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(formatApiError(data.detail) || "Failed to optimize timeframes");
    if (botConfig) {
      botConfig.symbols = data.symbols;
      botConfig.symbol_stats = data.symbol_stats;
    }
    renderSymbols(data.symbols);
    const changed = (data.optimization?.symbols || []).filter((row) => row.current_timeframe !== row.best_timeframe).length;
    toast(`Timeframe optimization done: ${changed} symbol${changed === 1 ? "" : "s"} changed`, "success");
    await refreshLogs();
  } catch (error) {
    toast(error.message, "error");
  } finally {
    setLoading(els.optimizeTimeframesBtn, false);
  }
}

function formatCurrency(value) {
  return `$${Number(value).toFixed(2)}`;
}

function formatPrice(value) {
  if (value === 0) return "—";
  return Number(value).toFixed(5);
}

function formatOptionalPrice(value) {
  if (value === null || value === undefined || value === "" || value === 0) return "—";
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) return "—";
  return numeric.toFixed(5);
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
        (row, index) => `
          <tr
            data-sort-row="true"
            data-sort-index="${index}"
            data-sort-ticket="${Number(row.ticket || 0)}"
            data-sort-symbol="${escapeHtml(row.symbol || "")}"
            data-sort-side="${escapeHtml(row.side || "")}"
            data-sort-volume="${Number(row.volume || 0)}"
            data-sort-open="${Number(row.price_open || 0)}"
            data-sort-current="${Number(row.price_current || 0)}"
            data-sort-sl="${Number(row.sl || 0)}"
            data-sort-tp="${Number(row.tp || 0)}"
            data-sort-pnl="${Number(row.profit || 0)}"
            data-sort-comment="${escapeHtml(row.comment || "")}"
          >
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
        (row, index) => `
          <tr
            data-sort-row="true"
            data-sort-index="${index}"
            data-sort-time="${escapeHtml(row.time || "")}"
            data-sort-ticket="${Number(row.ticket || 0)}"
            data-sort-symbol="${escapeHtml(row.symbol || "")}"
            data-sort-side="${escapeHtml(row.side || "")}"
            data-sort-volume="${Number(row.volume || 0)}"
            data-sort-price="${Number(row.price || 0)}"
            data-sort-pnl="${Number(row.profit || 0)}"
            data-sort-comment="${escapeHtml(row.comment || "")}"
          >
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
  scheduleResponsiveTables();
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
  if (currentPage() !== "home") return;
  if (liveTimer) clearInterval(liveTimer);
  liveTimer = setInterval(refreshLiveData, 5000);
}

function setDefaultLiveSummaryPeriod() {
  if (!els.liveSummaryStart || !els.liveSummaryEnd) return;
  const end = new Date();
  const start = new Date(end.getTime() - 24 * 60 * 60 * 1000);
  if (!els.liveSummaryEnd.value) els.liveSummaryEnd.value = isoToLocalInput(end.toISOString());
  if (!els.liveSummaryStart.value) els.liveSummaryStart.value = isoToLocalInput(start.toISOString());
}

function tradeTypeLabel(value) {
  if (value === "rsi_bot") return "RSI bot";
  if (value === "signal_bot") return "Telegram signal";
  return "Other";
}

function renderLiveSummary(data) {
  if (!els.liveSummaryOverall) return;
  const overall = data.overall || {};
  els.liveSummaryOverall.innerHTML = `
    <div class="summary-card"><span class="label">Overall P/L</span><span class="value ${pnlClass(overall.net)}">${formatMoney(overall.net || 0)}</span></div>
    <div class="summary-card"><span class="label">Trades</span><span class="value">${overall.trades || 0}</span></div>
    <div class="summary-card"><span class="label">W / L / BE</span><span class="value">${overall.wins || 0} / ${overall.losses || 0} / ${overall.breakeven || 0}</span></div>
    <div class="summary-card"><span class="label">Win rate</span><span class="value">${overall.win_rate || 0}%</span></div>
  `;
  els.liveSummaryOverall.classList.remove("hidden");

  const maxAbs = Math.max(
    1,
    ...(data.summary || []).map((row) => Math.max(Math.abs(Number(row.win_amount || 0)), Math.abs(Number(row.loss_amount || 0)), Math.abs(Number(row.net || 0)))),
  );
  els.liveSummaryChart.innerHTML = (data.summary || [])
    .map((row) => {
      const winWidth = Math.max(4, Math.round(Math.abs(Number(row.win_amount || 0)) / maxAbs * 100));
      const lossWidth = Math.max(4, Math.round(Math.abs(Number(row.loss_amount || 0)) / maxAbs * 100));
      return `
        <article class="live-summary-card">
          <div class="live-summary-card-head">
            <strong>${escapeHtml(row.label || tradeTypeLabel(row.key))}</strong>
            <span class="${pnlClass(row.net)}">${formatMoney(row.net || 0)}</span>
          </div>
          <div class="live-summary-bars">
            <div class="live-summary-bar live-summary-win" style="width:${winWidth}%"><span>${formatMoney(row.win_amount || 0)}</span></div>
            <div class="live-summary-bar live-summary-loss" style="width:${lossWidth}%"><span>${formatMoney(row.loss_amount || 0)}</span></div>
          </div>
          <div class="live-summary-metrics">
            <span>${row.trades || 0} trades</span>
            <span>${row.wins || 0}W / ${row.losses || 0}L</span>
            <span>${row.win_rate || 0}% win</span>
          </div>
        </article>
      `;
    })
    .join("");
  els.liveSummaryChart.classList.remove("hidden");

  const symbolRows = data.by_symbol || [];
  if (symbolRows.length) {
    els.liveSummarySymbols.innerHTML = symbolRows
      .map((row, index) => `
        <tr
          data-sort-row="true"
          data-sort-index="${index}"
          data-sort-symbol="${escapeHtml(row.symbol || "")}"
          data-sort-trades="${Number(row.trades || 0)}"
          data-sort-wins="${Number(row.wins || 0)}"
          data-sort-pnl="${Number(row.net || 0)}"
        >
          <td><strong>${escapeHtml(row.symbol)}</strong></td>
          <td>${row.trades}</td>
          <td>${row.wins} / ${row.losses}</td>
          <td class="${pnlClass(row.net)}">${formatMoney(row.net)}</td>
        </tr>
      `)
      .join("");
    els.liveSummarySymbolsWrap.classList.remove("hidden");
  } else {
    els.liveSummarySymbolsWrap.classList.add("hidden");
    els.liveSummarySymbols.innerHTML = "";
  }

  const trades = data.trades || [];
  els.liveSummaryCount.textContent = `${trades.length} trade${trades.length === 1 ? "" : "s"}`;
  if (!trades.length) {
    els.liveSummaryBody.innerHTML = '<tr><td colspan="10" class="empty-row">No trade history in this period.</td></tr>';
  } else {
    els.liveSummaryBody.innerHTML = trades
      .map((row, index) => `
        <tr
          data-sort-row="true"
          data-sort-index="${index}"
          data-sort-closed="${escapeHtml(row.closed_at || row.opened_at || "")}"
          data-sort-type="${escapeHtml(tradeTypeLabel(row.bucket))}"
          data-sort-position="${Number(row.position_id || 0)}"
          data-sort-symbol="${escapeHtml(row.symbol || "")}"
          data-sort-side="${escapeHtml(row.side || "")}"
          data-sort-volume="${Number(row.volume || 0)}"
          data-sort-entry="${Number(row.entry_price || 0)}"
          data-sort-exit="${Number(row.exit_price || 0)}"
          data-sort-pnl="${Number(row.pnl || 0)}"
          data-sort-comment="${escapeHtml(row.comment || "")}"
        >
          <td>${formatTimestamp(row.closed_at || row.opened_at)}</td>
          <td><span class="tag">${escapeHtml(tradeTypeLabel(row.bucket))}</span></td>
          <td>${row.position_id}</td>
          <td><strong>${escapeHtml(row.symbol || "-")}</strong></td>
          <td class="side-${row.side || ""}">${String(row.side || "-").toUpperCase()}</td>
          <td>${row.volume ?? "-"}</td>
          <td>${formatOptionalPrice(row.entry_price)}</td>
          <td>${formatOptionalPrice(row.exit_price)}</td>
          <td class="${pnlClass(row.pnl)}">${formatMoney(row.pnl || 0)}</td>
          <td>${escapeHtml(row.comment || "-")}</td>
        </tr>
      `)
      .join("");
  }
  scheduleResponsiveTables();
}

async function loadLiveSummary(event) {
  if (event) event.preventDefault();
  if (!els.liveSummaryForm) return;
  const start = localInputToIso(els.liveSummaryStart.value);
  const end = localInputToIso(els.liveSummaryEnd.value);

  setLoading(els.liveSummaryBtn, true, "Loading...");
  try {
    const response = await fetch(`/api/live-summary?start=${encodeURIComponent(start)}&end=${encodeURIComponent(end)}`, {
      cache: "no-store",
    });
    const data = await response.json();
    if (!response.ok) throw new Error(formatApiError(data.detail) || "Failed to load live summary");
    renderLiveSummary(data);
  } catch (error) {
    toast(error.message, "error");
  } finally {
    setLoading(els.liveSummaryBtn, false);
  }
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

function updateStrategyLabels(strategy) {
  if (!strategy) return;
  if (els.strategyBadge) els.strategyBadge.textContent = formatStrategy(strategy);
  if (els.autoRunStrategyLabel) {
    els.autoRunStrategyLabel.textContent = `Strategy: ${formatStrategy(strategy)}`;
  }
}

function syncStrategyUi(strategy, { updateSelects = true } = {}) {
  if (!strategy) return;
  const normalized = canonicalStrategy(strategy);
  if (updateSelects) {
    if (els.autoRunStrategy) els.autoRunStrategy.value = normalized;
    if (els.strategy) els.strategy.value = normalized;
    const chartStrategy = document.getElementById("chart-strategy");
    if (chartStrategy) chartStrategy.value = normalized;
  }
  updateStrategyLabels(normalized);
  if (botConfig?.bot) botConfig.bot.strategy = normalized;
}

function selectedStrategy() {
  return canonicalStrategy(els.autoRunStrategy?.value || botConfig?.bot?.strategy);
}

async function onBotSettingsChanged({ silent = true } = {}) {
  try {
    await saveBotStrategy({ silent });
  } catch (error) {
    toast(error.message, "error");
  }
}

function mirrorDailyLossControls(source) {
  if (source === "live") {
    syncDailyLossControlValues({
      enabled: els.dailyLossGuardEnabled?.checked,
      pct: Number(els.dailyLossGuardPct?.value),
    });
    return;
  }
  syncDailyLossControlValues({
    enabled: els.telegramDailyLossGuardEnabled?.checked,
    pct: Number(els.telegramDailyLossGuardPct?.value),
  });
}

function dailyWinTargetLabelForMode(mode) {
  return mode === "usd" ? "Daily win target (USD)" : "Daily win target (% of start-of-day balance)";
}

function updateDailyWinTargetLabels(mode = dailyWinTargetModeFromUi()) {
  const label = dailyWinTargetLabelForMode(mode);
  if (els.dailyWinTargetLabel) els.dailyWinTargetLabel.textContent = label;
  if (els.telegramDailyWinTargetLabel) els.telegramDailyWinTargetLabel.textContent = label;
}

function dailyWinTargetModeFromUi() {
  const liveMode = els.dailyWinTargetMode?.value;
  if (liveMode) return liveMode;
  const telegramMode = els.telegramDailyWinTargetMode?.value;
  if (telegramMode) return telegramMode;
  return botConfig?.risk?.daily_win_target_mode || "percent";
}

function dailyWinGuardEnabledFromUi() {
  if (els.dailyWinGuardEnabled) return Boolean(els.dailyWinGuardEnabled.checked);
  if (els.telegramDailyWinGuardEnabled) return Boolean(els.telegramDailyWinGuardEnabled.checked);
  return Boolean(botConfig?.risk?.use_daily_win_guard);
}

function dailyWinTargetValueFromUi() {
  const raw = Number(els.dailyWinTargetValue?.value ?? els.telegramDailyWinTargetValue?.value);
  if (Number.isFinite(raw)) return raw;
  const risk = botConfig?.risk || {};
  if ((risk.daily_win_target_mode || "percent") === "usd") {
    return Number(risk.max_daily_win_usd ?? 0);
  }
  return Number(risk.max_daily_win_pct ?? 0);
}

function syncDailyWinControlValues({ enabled, mode, value }) {
  const normalizedMode = mode || "percent";
  if (els.dailyWinGuardEnabled && enabled != null) els.dailyWinGuardEnabled.checked = Boolean(enabled);
  if (els.telegramDailyWinGuardEnabled && enabled != null) {
    els.telegramDailyWinGuardEnabled.checked = Boolean(enabled);
  }
  if (els.dailyWinTargetMode && mode != null) els.dailyWinTargetMode.value = normalizedMode;
  if (els.telegramDailyWinTargetMode && mode != null) els.telegramDailyWinTargetMode.value = normalizedMode;
  if (els.dailyWinTargetValue && value != null) els.dailyWinTargetValue.value = value;
  if (els.telegramDailyWinTargetValue && value != null) els.telegramDailyWinTargetValue.value = value;
  updateDailyWinTargetLabels(normalizedMode);
}

function collectDailyWinSettings() {
  const mode = dailyWinTargetModeFromUi();
  const value = dailyWinTargetValueFromUi();
  return {
    use_daily_win_guard: dailyWinGuardEnabledFromUi(),
    daily_win_target_mode: mode,
    max_daily_win_pct: mode === "percent" ? value : null,
    max_daily_win_usd: mode === "usd" ? value : null,
  };
}

function mirrorDailyWinControls(source) {
  if (source === "live") {
    syncDailyWinControlValues({
      enabled: els.dailyWinGuardEnabled?.checked,
      mode: els.dailyWinTargetMode?.value,
      value: Number(els.dailyWinTargetValue?.value),
    });
    return;
  }
  syncDailyWinControlValues({
    enabled: els.telegramDailyWinGuardEnabled?.checked,
    mode: els.telegramDailyWinTargetMode?.value,
    value: Number(els.telegramDailyWinTargetValue?.value),
  });
}

async function onDailyLossSettingsChanged(source = "live") {
  mirrorDailyLossControls(source);
  mirrorDailyWinControls(source);
  try {
    await saveBotStrategy({ silent: true, persist: true });
  } catch (error) {
    toast(error.message, "error");
  }
}

function isDailyLossGuardEnabled() {
  if (els.dailyLossGuardEnabled) return Boolean(els.dailyLossGuardEnabled.checked);
  if (els.telegramDailyLossGuardEnabled) return Boolean(els.telegramDailyLossGuardEnabled.checked);
  return botConfig?.risk?.use_daily_loss_guard !== false;
}

function dailyLossGuardEnabledFromUi() {
  if (els.dailyLossGuardEnabled) return Boolean(els.dailyLossGuardEnabled.checked);
  if (els.telegramDailyLossGuardEnabled) return Boolean(els.telegramDailyLossGuardEnabled.checked);
  return botConfig?.risk?.use_daily_loss_guard !== false;
}

function dailyLossGuardPctFromUi() {
  const liveValue = Number(els.dailyLossGuardPct?.value);
  if (Number.isFinite(liveValue)) return liveValue;
  const telegramValue = Number(els.telegramDailyLossGuardPct?.value);
  if (Number.isFinite(telegramValue)) return telegramValue;
  return Number(botConfig?.risk?.max_daily_loss_pct ?? 15);
}

function syncDailyLossControlValues({ enabled, pct }) {
  if (els.dailyLossGuardEnabled && enabled != null) {
    els.dailyLossGuardEnabled.checked = Boolean(enabled);
  }
  if (els.telegramDailyLossGuardEnabled && enabled != null) {
    els.telegramDailyLossGuardEnabled.checked = Boolean(enabled);
  }
  if (els.dailyLossGuardPct && pct != null) {
    els.dailyLossGuardPct.value = pct;
  }
  if (els.telegramDailyLossGuardPct && pct != null) {
    els.telegramDailyLossGuardPct.value = pct;
  }
}

function isDailyGuardHalted(dailyRisk) {
  return Boolean(dailyRisk?.halted);
}

let dailyGuardClockTimer = null;
let lastUtcDayKey = null;

function utcDayKey(date = new Date()) {
  return date.toISOString().slice(0, 10);
}

function formatUtcDateTime(date, { includeSeconds = true } = {}) {
  const datePart = date.toLocaleDateString("en-GB", {
    weekday: "short",
    day: "numeric",
    month: "short",
    year: "numeric",
    timeZone: "UTC",
  });
  const timePart = date.toLocaleTimeString("en-GB", {
    hour: "2-digit",
    minute: "2-digit",
    second: includeSeconds ? "2-digit" : undefined,
    hour12: false,
    timeZone: "UTC",
  });
  return `${datePart} · ${timePart} UTC`;
}

function utcMidnightCountdown(now = new Date()) {
  const resetAt = new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate() + 1, 0, 0, 0, 0));
  const totalSec = Math.max(0, Math.floor((resetAt - now) / 1000));
  return {
    resetAt,
    hours: Math.floor(totalSec / 3600),
    minutes: Math.floor((totalSec % 3600) / 60),
    seconds: totalSec % 60,
  };
}

function formatUtcCountdown({ hours, minutes, seconds }) {
  const pad = (value) => String(value).padStart(2, "0");
  if (hours > 0) return `${hours}h ${pad(minutes)}m ${pad(seconds)}s`;
  if (minutes > 0) return `${minutes}m ${pad(seconds)}s`;
  return `${seconds}s`;
}

function formatUtcResetAt(date) {
  const datePart = date.toLocaleDateString("en-GB", {
    weekday: "short",
    day: "numeric",
    month: "short",
    year: "numeric",
    timeZone: "UTC",
  });
  return `00:00:00 UTC (${datePart})`;
}

function dailyGuardResetClockTargets() {
  return [els.dailyGuardResetClock, els.telegramDailyGuardResetClock].filter(Boolean);
}

function renderDailyGuardResetClock() {
  const targets = dailyGuardResetClockTargets();
  if (!targets.length) return;

  const now = new Date();
  const dayKey = utcDayKey(now);
  const countdown = utcMidnightCountdown(now);
  const resetLabel = formatUtcResetAt(countdown.resetAt);

  if (lastUtcDayKey && lastUtcDayKey !== dayKey) {
    void refreshDailyRiskStatus();
  }
  lastUtcDayKey = dayKey;

  const html = `
    <div class="daily-guard-reset-clock-head">
      <span class="daily-guard-reset-clock-title">UTC day clock</span>
      <span class="daily-guard-reset-clock-live">${escapeHtml(formatUtcDateTime(now))}</span>
    </div>
    <div class="daily-guard-reset-clock-grid">
      ${dailyGuardStatItem("Time left today", formatUtcCountdown(countdown))}
      ${dailyGuardStatItem("Guards refresh at", resetLabel)}
    </div>
    <p class="daily-guard-reset-clock-note">
      Daily loss and win guards reset at UTC midnight. Stats are read from MT5 deal history for the logged-in account (not cached balances from a previous account).
    </p>
  `;

  for (const target of targets) {
    target.className = "daily-guard-reset-clock field-full";
    target.innerHTML = html;
  }
}

function startDailyGuardClock() {
  const targets = dailyGuardResetClockTargets();
  if (!targets.length) return;
  if (dailyGuardClockTimer) clearInterval(dailyGuardClockTimer);
  renderDailyGuardResetClock();
  dailyGuardClockTimer = setInterval(renderDailyGuardResetClock, 1000);
}

function pnlValueClass(value) {
  const amount = Number(value) || 0;
  if (amount > 0) return "value-positive";
  if (amount < 0) return "value-negative";
  return "";
}

function dailyGuardStatItem(label, value, valueClass = "") {
  const safeClass = valueClass ? ` ${valueClass}` : "";
  return `
    <div class="daily-guard-stat-item">
      <span class="daily-guard-stat-label">${escapeHtml(label)}</span>
      <span class="daily-guard-stat-value${safeClass}">${escapeHtml(value)}</span>
    </div>
  `;
}

function dailyGuardProgressBar(used, total, variant) {
  const safeTotal = Math.max(0, Number(total) || 0);
  const safeUsed = Math.max(0, Number(used) || 0);
  const pct = safeTotal > 0 ? Math.min(100, (safeUsed / safeTotal) * 100) : 0;
  const caption = variant === "win" ? "of target" : "of limit";
  return `
    <div class="daily-guard-stat-progress daily-guard-stat-progress--${variant}">
      <div class="daily-guard-stat-progress-bar" style="width:${pct.toFixed(1)}%"></div>
    </div>
    <p class="daily-guard-stat-progress-caption">${pct.toFixed(1)}% ${caption}</p>
  `;
}

function renderDailyGuardPlaceholder(target, message, variant) {
  if (!target) return;
  target.className = `daily-guard-stat daily-guard-stat--${variant} field-full is-muted`;
  target.innerHTML = `<p class="daily-guard-stat-placeholder">${escapeHtml(message)}</p>`;
}

function renderDailyLossStatus(dailyRisk, target) {
  if (!target) return;
  if (!dailyRisk || dailyRisk.error) {
    const message = dailyRisk?.error ? `Loss tracking unavailable: ${dailyRisk.error}` : "Loss tracking: —";
    renderDailyGuardPlaceholder(target, message, "loss");
    return;
  }

  const lossOn = Boolean(dailyRisk.loss_guard_enabled ?? dailyRisk.use_daily_loss_guard);
  if (!lossOn) {
    renderDailyGuardPlaceholder(target, "Daily loss guard is off.", "loss");
    return;
  }

  const startEquity = dailyRisk.start_equity ?? dailyRisk.start_balance ?? 0;
  const currentEquity = Number(dailyRisk.equity ?? startEquity);
  const dailyPnl = Number(dailyRisk.daily_pnl || 0);
  const loss = Math.max(0, Number(dailyRisk.loss ?? Math.max(0, startEquity - currentEquity)));
  const limit = Number(dailyRisk.loss_limit || 0);
  const floorEquity = Number(dailyRisk.loss_floor_equity ?? startEquity - limit);
  const remaining = Number(dailyRisk.loss_remaining ?? dailyRisk.remaining ?? Math.max(0, limit - loss));
  const halted = Boolean(dailyRisk.loss_halted || (dailyRisk.halted && dailyRisk.halt_reason === "loss"));
  const headline = halted ? "Daily loss limit reached" : "Loss tracking";

  target.className = `daily-guard-stat daily-guard-stat--loss field-full${halted ? " is-halted" : ""}`;
  target.innerHTML = `
    <div class="daily-guard-stat-head">
      <span class="daily-guard-stat-title">${escapeHtml(headline)}</span>
      ${halted ? '<span class="daily-guard-stat-badge">Blocked</span>' : ""}
    </div>
    <div class="daily-guard-stat-grid">
      ${dailyGuardStatItem("Start", formatLossAmount(startEquity))}
      ${dailyGuardStatItem("Equity", formatLossAmount(currentEquity))}
      ${dailyGuardStatItem("Day P/L", formatMoney(dailyPnl), pnlValueClass(dailyPnl))}
      ${dailyGuardStatItem("Loss", `${formatLossAmount(loss)} / ${formatLossAmount(limit)}`)}
      ${dailyGuardStatItem("Stop at", formatLossAmount(floorEquity))}
      ${dailyGuardStatItem("Remaining", `${formatLossAmount(remaining)} left`)}
    </div>
    ${dailyGuardProgressBar(loss, limit, "loss")}
  `;
}

function renderDailyWinStatus(dailyRisk, target) {
  if (!target) return;
  if (!dailyRisk || dailyRisk.error) {
    const message = dailyRisk?.error ? `Win tracking unavailable: ${dailyRisk.error}` : "Win tracking: —";
    renderDailyGuardPlaceholder(target, message, "win");
    return;
  }

  const winOn = Boolean(dailyRisk.win_guard_enabled ?? dailyRisk.use_daily_win_guard);
  if (!winOn) {
    renderDailyGuardPlaceholder(target, "Daily win guard is off.", "win");
    return;
  }

  const startEquity = dailyRisk.start_equity ?? dailyRisk.start_balance ?? 0;
  const currentEquity = Number(dailyRisk.equity ?? startEquity);
  const dailyPnl = Number(dailyRisk.daily_pnl || 0);
  const gain = Number(dailyRisk.gain || Math.max(0, dailyPnl));
  const winTarget = Number(dailyRisk.win_target || 0);
  const winGoalEquity = Number(dailyRisk.win_goal_equity ?? startEquity + winTarget);
  const winRemaining = Number(dailyRisk.win_remaining ?? Math.max(0, winTarget - gain));
  const halted = Boolean(dailyRisk.win_halted || (dailyRisk.halted && dailyRisk.halt_reason === "win"));
  const headline = halted ? "Daily win target reached" : "Win tracking";

  target.className = `daily-guard-stat daily-guard-stat--win field-full${halted ? " is-halted" : ""}`;
  target.innerHTML = `
    <div class="daily-guard-stat-head">
      <span class="daily-guard-stat-title">${escapeHtml(headline)}</span>
      ${halted ? '<span class="daily-guard-stat-badge">Blocked</span>' : ""}
    </div>
    <div class="daily-guard-stat-grid">
      ${dailyGuardStatItem("Start", formatLossAmount(startEquity))}
      ${dailyGuardStatItem("Equity", formatLossAmount(currentEquity))}
      ${dailyGuardStatItem("Day P/L", formatMoney(dailyPnl), pnlValueClass(dailyPnl))}
      ${dailyGuardStatItem("Profit", `${formatLossAmount(gain)} / ${formatLossAmount(winTarget)}`)}
      ${dailyGuardStatItem("Goal at", formatLossAmount(winGoalEquity))}
      ${dailyGuardStatItem("To goal", `${formatLossAmount(winRemaining)} left`)}
    </div>
    ${dailyGuardProgressBar(gain, winTarget, "win")}
  `;
}

function renderDailyRiskStatuses(dailyRisk) {
  renderDailyLossStatus(dailyRisk, els.dailyLossStatus);
  renderDailyWinStatus(dailyRisk, els.dailyWinStatus);
  renderDailyLossStatus(dailyRisk, els.telegramDailyLossStatus);
  renderDailyWinStatus(dailyRisk, els.telegramDailyWinStatus);
}

function syncDailyRiskSettings(configLike = botConfig) {
  syncDailyLossControlValues({
    enabled: configLike?.risk?.use_daily_loss_guard !== false,
    pct: configLike?.risk?.max_daily_loss_pct ?? 15,
  });
  const winMode = configLike?.risk?.daily_win_target_mode || "percent";
  const winValue = winMode === "usd"
    ? configLike?.risk?.max_daily_win_usd ?? 100
    : configLike?.risk?.max_daily_win_pct ?? 5;
  syncDailyWinControlValues({
    enabled: Boolean(configLike?.risk?.use_daily_win_guard),
    mode: winMode,
    value: winValue,
  });
}

function renderAutoRunStatus(status, includeDailyRisk = true) {
  if (!els.autoRunLabel || !els.autoRunDot) return;

  const running = Boolean(status.running);
  const serverStrategy = status.strategy || botConfig?.bot?.strategy;
  const displayStrategy = running
    ? serverStrategy
    : (els.autoRunStrategy?.value || serverStrategy);
  els.autoRunDot.classList.toggle("running", running);
  els.autoRunLabel.textContent = running ? "Running" : "Stopped";
  els.autoRunScans.textContent = `${status.scans_completed || 0} scans · ${status.last_signals || 0} signals · ${status.last_placed || 0} placed`;
  els.autoRunLast.textContent = `Last scan: ${formatTimestamp(status.last_scan_at)}`;
  if (running) {
    syncStrategyUi(serverStrategy);
  } else {
    updateStrategyLabels(displayStrategy);
  }
  els.autoRunStartBtn.disabled = running;
  els.autoRunStopBtn.disabled = !running;
  if (els.autoRunStrategy) els.autoRunStrategy.disabled = running;
  if (els.autoRunSignalAlgorithm) els.autoRunSignalAlgorithm.disabled = running;
  if (els.autoRunSaveBtn) els.autoRunSaveBtn.disabled = running;
  if (els.autoRunSaveStrategy) els.autoRunSaveStrategy.disabled = running;

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
  } else if (isDailyGuardHalted(status.daily_risk)) {
    if (status.daily_risk?.halt_reason === "win") {
      els.autoRunHint.textContent = `Daily win guard active: gain ${formatLossAmount(status.daily_risk.gain)} reached target ${formatLossAmount(status.daily_risk.win_target)}. New trades are blocked for the rest of the UTC day.`;
    } else {
      els.autoRunHint.textContent = `Daily loss guard active: drawdown ${formatLossAmount(status.daily_risk.loss)} reached limit ${formatLossAmount(status.daily_risk.loss_limit)}. New trades are blocked for the rest of the UTC day.`;
    }
    els.autoRunHint.className = "panel-hint live-warning";
  } else if (!running) {
    const strategyText = formatStrategy(displayStrategy);
    els.autoRunHint.textContent = status.dry_run
      ? `Auto run is stopped. Choose a TP protection rule, then start to scan symbols in paper mode (${strategyText}).`
      : `Auto run is stopped. Choose a TP protection rule, then start to scan enabled symbols and place live MT5 orders (${strategyText}).`;
    els.autoRunHint.className = "panel-hint";
  } else if (status.dry_run) {
    els.autoRunHint.textContent = `Paper mode: ${formatStrategy(displayStrategy)}. Listening every ${status.poll_seconds}s. Signals are logged but no live orders are sent.`;
    els.autoRunHint.className = "panel-hint";
  } else {
    const profile = status.trade_decision_profile || botConfig?.bot?.trade_decision_profile || "safe";
    const filters = status.decision_filters || botConfig?.decision_filters;
    const profileText = `${profile} profile, ${describeDecisionFilters(filters)}`;
    els.autoRunHint.textContent = `Live mode: ${formatStrategy(displayStrategy)}. Listening every ${status.poll_seconds}s. New signals auto-place orders in MT5, ${profileText}.`;
    els.autoRunHint.className = "panel-hint live-warning";
  }
  if (includeDailyRisk && status.daily_risk?.start_equity != null && status.daily_risk?.equity != null) {
    renderDailyRiskStatuses(status.daily_risk);
  }
}

async function refreshDailyRiskStatus() {
  try {
    const response = await fetch("/api/daily-risk", { cache: "no-store" });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || "Failed to load daily risk");
    renderDailyRiskStatuses(data);
    return data;
  } catch (error) {
    renderDailyRiskStatuses({ error: error.message });
    return null;
  }
}

async function refreshAutoRunStatus(includeMt5 = true) {
  try {
    const query = includeMt5 ? "?include_mt5=true" : "";
    const response = await fetch(`/api/auto-run/status${query}`, { cache: "no-store" });
    if (!response.ok) throw new Error("Failed to load auto-run status");
    const status = await response.json();
    renderAutoRunStatus(status, includeMt5);
    if (!includeMt5) {
      void refreshDailyRiskStatus();
    }
  } catch (error) {
    toast(error.message, "error");
  }
}

async function saveBotStrategy({ strategy, persist, silent = false } = {}) {
  const saveToConfig = persist ?? Boolean(els.autoRunSaveStrategy?.checked);
  const selected = els.autoRunStrategy
    ? canonicalStrategy(strategy ?? selectedStrategy())
    : canonicalStrategy(strategy ?? botConfig?.bot?.strategy ?? "signal_with_tp_protection");
  setLoading(els.autoRunSaveBtn, true);
  try {
    const response = await fetch("/api/bot/settings", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        strategy: selected,
        signal_algorithm: els.autoRunSignalAlgorithm?.value || botConfig?.bot?.signal_algorithm,
        use_daily_loss_guard: dailyLossGuardEnabledFromUi(),
        max_daily_loss_pct: dailyLossGuardPctFromUi(),
        ...collectDailyWinSettings(),
        persist: saveToConfig,
      }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || "Failed to save bot settings");
    syncStrategyUi(data.strategy);
    if (data.signal_algorithm) syncSignalAlgorithmUi(data.signal_algorithm);
    if (botConfig?.bot) {
      botConfig.bot.strategy = data.strategy;
      botConfig.bot.signal_algorithm = data.signal_algorithm;
    }
    if (data.risk && botConfig) {
      botConfig.risk = { ...(botConfig.risk || {}), ...data.risk };
      syncDailyRiskSettings(botConfig);
    }
    if (data.auto_run) renderAutoRunStatus(data.auto_run);
    void refreshDailyRiskStatus();
    void refreshAutoRunStatus(false);
    if (!silent) {
      toast(saveToConfig ? "Bot settings saved to config.yaml" : "Bot settings applied in memory", "success");
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
        signal_algorithm: els.autoRunSignalAlgorithm?.value || botConfig?.bot?.signal_algorithm,
        strategy_persist: Boolean(els.autoRunSaveStrategy?.checked),
        persist: false,
      }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || "Failed to start auto run");
    syncStrategyUi(data.strategy || els.autoRunStrategy?.value);
    if (data.signal_algorithm) syncSignalAlgorithmUi(data.signal_algorithm);
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
  if (currentPage() !== "home") return;
  if (loopTimer) clearInterval(loopTimer);
  loopTimer = setInterval(() => {
    refreshAutoRunStatus(false);
    refreshDailyRiskStatus();
  }, 5000);
}

function telegramStatusClass(status) {
  const value = String(status || "").toLowerCase();
  if (value === "placed" || value === "paper" || value === "breakeven") return "value-positive";
  if (value === "failed" || value === "error" || value.includes("fail")) return "value-negative";
  if (value === "skipped" || value === "stale" || value === "signal_inactive") return "value-neutral";
  return "value-neutral";
}

function formatTelegramAccountResults(accountResults) {
  if (!Array.isArray(accountResults) || !accountResults.length) return "";
  return accountResults
    .map((item) => {
      const name = item.account_name || item.account_id || "account";
      if (item.status === "placed" || item.status === "paper") {
        const ticket = item.ticket || (item.tickets && item.tickets[0]) || "?";
        return `${name}: ${item.status} ticket ${ticket}`;
      }
      return `${name}: ${item.reason || item.error || item.status || "failed"}`;
    })
    .join(" · ");
}

function renderTelegramActionStatusBadge(statusEl, result) {
  if (!statusEl) return;
  const status = String(result?.status || "unknown");
  const summary = formatTelegramAccountResults(result?.account_results);
  const reason = result?.reason || summary;
  statusEl.textContent = summary || reason || status;
  statusEl.className = `telegram-action-status ${telegramStatusClass(status)}`;
  statusEl.classList.remove("hidden");
}

function formatTelegramParsedSignal(signal) {
  if (!signal?.action || signal.action === "none") return "—";
  const bits = [String(signal.action).toUpperCase(), signal.symbol || ""];
  if (signal.entry_low != null && signal.entry_high != null) {
    bits.push(`${signal.entry_low}-${signal.entry_high}`);
  } else if (signal.entry != null) {
    bits.push(String(signal.entry));
  }
  return bits.join(" ");
}

function renderTelegramActionLog(actions) {
  if (!els.telegramActionLogBody) return;
  const items = Array.isArray(actions) ? actions.slice().reverse() : [];
  if (!items.length) {
    els.telegramActionLogBody.innerHTML = '<p class="empty-row">No copy actions yet.</p>';
    return;
  }
  els.telegramActionLogBody.innerHTML = items
    .map((item) => {
      const status = String(item.status || "unknown");
      const kind = item.hard_copy ? "Hard copy" : item.kind === "signal_copy" ? "Auto copy" : item.kind || "Action";
      const bits = [kind, status.toUpperCase()];
      if (item.channel) bits.push(item.channel);
      if (item.symbol) bits.push(item.symbol);
      const accountSummary = formatTelegramAccountResults(item.result?.account_results);
      const detail = accountSummary || item.result?.execution_reason || item.reason || item.result?.reason || "";
      return `
        <article class="telegram-action-log-item">
          <div class="telegram-action-log-head">
            <span class="${telegramStatusClass(status)}">${escapeHtml(bits.join(" · "))}</span>
            <span class="mono">${formatTimestamp(item.at)}</span>
          </div>
          ${detail ? `<p class="telegram-action-log-detail">${escapeHtml(detail)}</p>` : ""}
        </article>
      `;
    })
    .join("");
}

function telegramActionsFingerprintValue(actions) {
  return (actions || [])
    .map((item) => [
      item.at,
      item.kind,
      item.status,
      item.channel,
      item.symbol,
      item.reason,
      item.result?.status,
    ].join(":"))
    .join("|");
}

function updateTelegramActionLogIfChanged(actions) {
  const fingerprint = telegramActionsFingerprintValue(actions);
  if (fingerprint === telegramActionsFingerprint) return;
  telegramActionsFingerprint = fingerprint;
  renderTelegramActionLog(actions);
}

function telegramExpandStorageKey(rowKey, field) {
  return `${rowKey}::${field}`;
}

function syncTelegramSettingsFromStatus(status, { force = false } = {}) {
  if (!force) {
    const active = document.activeElement;
    if (active === els.telegramIgnoreOpen || active === els.telegramProtectTp) return;
  }
  if (els.telegramIgnoreOpen && status.ignore_open_symbol_trades != null) {
    els.telegramIgnoreOpen.checked = Boolean(status.ignore_open_symbol_trades);
  }
  if (els.telegramProtectTp && status.protect_tp != null) {
    els.telegramProtectTp.checked = Boolean(status.protect_tp);
  }
  if (els.telegramOpenGuard) {
    els.telegramOpenGuard.textContent = status.ignore_open_symbol_trades ? "On" : "Off";
  }
}

function updateTelegramLastPanels(status) {
  const signal = status.last_signal;
  if (els.telegramLastParsed) {
    els.telegramLastParsed.textContent = formatTelegramParsedSignal(signal);
  }
  if (els.telegramLastAction && els.telegramLastActionJson) {
    const action = status.last_action;
    if (action?.result) {
      const bits = [];
      if (action.channel) bits.push(action.channel);
      if (action.at) bits.push(formatTimestamp(action.at));
      if (action.result?.status) bits.push(String(action.result.status));
      if (action.result?.hard_copy) bits.push("hard copy");
      if (els.telegramLastActionMeta) {
        els.telegramLastActionMeta.textContent = bits.length ? bits.join(" · ") : "Latest trade action";
      }
      renderTelegramActionStatusBadge(els.telegramLastActionStatus, action.result);
      const payload = JSON.stringify(
        {
          signal: action.signal || status.last_signal || null,
          result: action.result,
        },
        null,
        2,
      );
      if (els.telegramLastActionJson.textContent !== payload) {
        els.telegramLastActionJson.textContent = payload;
      }
      els.telegramLastAction.classList.remove("hidden");
    } else if (status.last_result) {
      if (els.telegramLastActionMeta) {
        els.telegramLastActionMeta.textContent = status.last_channel
          ? `${status.last_channel} · ${formatTimestamp(status.last_action_at)}`
          : formatTimestamp(status.last_action_at);
      }
      renderTelegramActionStatusBadge(els.telegramLastActionStatus, status.last_result);
      const payload = JSON.stringify(status.last_result, null, 2);
      if (els.telegramLastActionJson.textContent !== payload) {
        els.telegramLastActionJson.textContent = payload;
      }
      els.telegramLastAction.classList.remove("hidden");
    } else {
      els.telegramLastAction.classList.add("hidden");
      els.telegramLastActionJson.textContent = "";
      if (els.telegramLastActionMeta) els.telegramLastActionMeta.textContent = "";
      els.telegramLastActionStatus?.classList.add("hidden");
    }
  }
  if (els.telegramLastResult && els.telegramLastResultJson) {
    if (status.last_signal) {
      const payload = JSON.stringify(status.last_signal, null, 2);
      if (els.telegramLastResultJson.textContent !== payload) {
        els.telegramLastResultJson.textContent = payload;
      }
      els.telegramLastResult.classList.remove("hidden");
    } else {
      els.telegramLastResult.classList.add("hidden");
      els.telegramLastResultJson.textContent = "";
    }
  }
}

function renderTelegramStatus(status, { full = false } = {}) {
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
      `${status.messages_seen || 0} messages · ${status.parsed_signals || 0} parsed · ${status.placed || 0} placed · ${status.failed || 0} failed · ${status.skipped || 0} skipped`;
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
    } else if (!status.llm_configured) {
      els.telegramHint.textContent =
        "LLM API key missing. Add telegram_signals.openai_api_key (primary) or gemini_api_key (fallback) in config.yaml.";
      els.telegramHint.className = "panel-hint live-warning";
    } else if (botConfig && !botConfig.bot.dry_run) {
      els.telegramHint.textContent = "Live mode: copied Telegram signals will place real MT5 orders after validation.";
      els.telegramHint.className = "panel-hint live-warning";
    } else {
      els.telegramHint.textContent = "Dry run mode: copied Telegram signals are parsed and logged without live orders.";
      els.telegramHint.className = "panel-hint";
    }
  }

  updateTelegramLastPanels(status);
  updateTelegramActionLogIfChanged(status.recent_actions || []);
  if (els.telegramLlm && (status.openai_model || status.gemini_model)) {
    els.telegramLlm.textContent = formatSignalParserLabel({
      openai_api_key_configured: status.openai_api_key_configured,
      openai_model: status.openai_model,
      gemini_api_key_configured: status.gemini_api_key_configured,
      gemini_model: status.gemini_model,
    });
  }
  syncTelegramSettingsFromStatus(status, { force: full });
  updateTelegramMessagesIfChanged(
    status.recent_messages || [],
    status.channels || botConfig?.telegram_signals?.channels || [],
    { force: full },
  );
  if (full) {
    renderTelegramChannels(status.channels || botConfig?.telegram_signals?.channels || []);
  }
}

function renderTelegramChannels(channels) {
  if (!els.telegramChannelsBody) return;
  const list = Array.isArray(channels) ? channels : [];
  if (els.telegramChannels) {
    els.telegramChannels.textContent = `${list.filter((channel) => channel.enabled).length} active / ${list.length} total`;
  }
  if (!list.length) {
    els.telegramChannelsBody.innerHTML = '<tr><td colspan="4" class="empty-row">No channels configured yet.</td></tr>';
    scheduleResponsiveTables();
    return;
  }
  els.telegramChannelsBody.innerHTML = list
    .map((channel) => {
      const url = String(channel.url || "");
      const name = escapeHtml(String(channel.name || "—"));
      const enabled = Boolean(channel.enabled);
      const statusClass = enabled ? "channel-status-active" : "channel-status-disabled";
      const statusLabel = enabled ? "Active" : "Disabled";
      return `
        <tr class="${enabled ? "" : "row-disabled"}">
          <td><span class="channel-status ${statusClass}">${statusLabel}</span></td>
          <td>${name}</td>
          <td><a href="${escapeHtml(url)}" target="_blank" rel="noopener noreferrer">${escapeHtml(url).slice(0, 72)}</a></td>
          <td class="table-actions">
            ${
              enabled
                ? `<button type="button" class="btn btn-secondary btn-sm telegram-channel-disable-btn" data-url="${escapeHtml(url)}">Disable</button>`
                : `<button type="button" class="btn btn-primary btn-sm telegram-channel-enable-btn" data-url="${escapeHtml(url)}">Enable</button>`
            }
            <button type="button" class="btn btn-danger btn-sm telegram-channel-remove-btn" data-url="${escapeHtml(url)}">Remove</button>
          </td>
        </tr>
      `;
    })
    .join("");
  scheduleResponsiveTables();
}

async function addTelegramChannel(event) {
  event.preventDefault();
  const url = String(els.telegramChannelUrl?.value || "").trim();
  if (!url) {
    toast("Paste a Telegram Web chat link first.", "error");
    return;
  }
  setLoading(els.telegramChannelAddBtn, true);
  try {
    const response = await fetch("/api/telegram-signals/channels", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        url,
        name: String(els.telegramChannelName?.value || "").trim() || null,
        enabled: Boolean(els.telegramChannelEnabled?.checked),
        persist: true,
      }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || "Failed to add channel");
    if (botConfig?.telegram_signals) botConfig.telegram_signals.channels = data.channels || [];
    renderTelegramChannels(data.channels || []);
    els.telegramChannelForm?.reset();
    if (els.telegramChannelEnabled) els.telegramChannelEnabled.checked = true;
    toast(`Added channel ${data.channel?.name || ""}`.trim(), "success");
  } catch (error) {
    toast(error.message, "error");
  } finally {
    setLoading(els.telegramChannelAddBtn, false);
  }
}

async function updateTelegramChannel(url, patch) {
  const response = await fetch("/api/telegram-signals/channels", {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ url, persist: true, ...patch }),
  });
  const data = await response.json();
  if (!response.ok) throw new Error(data.detail || "Failed to update channel");
  if (botConfig?.telegram_signals) botConfig.telegram_signals.channels = data.channels || [];
  renderTelegramChannels(data.channels || []);
  return data;
}

async function saveTelegramSettings({ silent = false } = {}) {
  if (!els.telegramIgnoreOpen) return null;
  setLoading(els.telegramSaveBtn, true);
  try {
    const response = await fetch("/api/telegram-signals/settings", {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        ignore_open_symbol_trades: Boolean(els.telegramIgnoreOpen.checked),
        protect_tp: Boolean(els.telegramProtectTp?.checked),
        browser_headless: Boolean(els.telegramBrowserHeadless?.checked),
        persist: true,
      }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || "Failed to save Telegram settings");
    if (botConfig?.telegram_signals) {
      botConfig.telegram_signals.ignore_open_symbol_trades = Boolean(data.ignore_open_symbol_trades);
      botConfig.telegram_signals.protect_tp = Boolean(data.protect_tp);
    }
    if (els.telegramOpenGuard) {
      els.telegramOpenGuard.textContent = data.ignore_open_symbol_trades ? "On" : "Off";
    }
    if (!silent) {
      toast("Telegram settings saved to config.yaml", "success");
    }
    await saveBotStrategy({ persist: true, silent: true });
    return data;
  } catch (error) {
    if (!silent) toast(error.message, "error");
    throw error;
  } finally {
    setLoading(els.telegramSaveBtn, false);
  }
}

async function removeTelegramChannel(url) {
  const confirmed = window.confirm("Remove this Telegram channel from the copier list?");
  if (!confirmed) return;
  try {
    const response = await fetch("/api/telegram-signals/channels/remove", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url, persist: true }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || "Failed to remove channel");
    if (botConfig?.telegram_signals) botConfig.telegram_signals.channels = data.channels || [];
    renderTelegramChannels(data.channels || []);
    toast(`Removed ${data.channel?.name || "channel"}`, "success");
  } catch (error) {
    toast(error.message, "error");
  }
}

function formatLlmResponse(item) {
  const parsed = item?.parsed;
  if (parsed && typeof parsed === "object") {
    const parts = [];
    if (parsed.action) parts.push(`action=${parsed.action}`);
    if (parsed.symbol) parts.push(`symbol=${parsed.symbol}`);
    if (parsed.entry != null && parsed.entry !== "") parts.push(`entry=${parsed.entry}`);
    if (parsed.stop_loss != null) parts.push(`sl=${parsed.stop_loss}`);
    else if (item?.result?.sl_synthetic && item?.result?.sl != null) parts.push(`sl=${item.result.sl} (default 1:1 TP2)`);
    if (Array.isArray(parsed.tps) && parsed.tps.length) parts.push(`tps=[${parsed.tps.join(", ")}]`);
    if (Array.isArray(item?.result?.tickets) && item.result.tickets.length) {
      parts.push(`tickets=[${item.result.tickets.join(", ")}]`);
    }
    if (parsed.confidence != null) parts.push(`confidence=${parsed.confidence}`);
    if (parts.length) return parts.join(" · ");
    return JSON.stringify(parsed);
  }

  const result = item?.result;
  if (result && typeof result === "object") {
    if (result.status === "breakeven" || result.status === "paper") {
      const entry = result.entry_price != null ? `@ ${result.entry_price}` : "";
      return `Breakeven command → move SL to entry ${entry}`.trim();
    }
    if (result.status === "placed" || result.status === "paper") {
      const bits = [result.status];
      if (result.symbol) bits.push(result.symbol);
      if (result.action) bits.push(String(result.action).toUpperCase());
      if (result.entry_price != null) bits.push(`entry=${result.entry_price}`);
      if (result.sl != null) bits.push(`sl=${result.sl}${result.sl_synthetic ? " (default)" : ""}`);
      if (Array.isArray(result.tickets) && result.tickets.length) bits.push(`tickets=${result.tickets.join(",")}`);
      return bits.join(" · ");
    }
    if (result.status === "updated") {
      const bits = ["SL updated"];
      if (result.sl != null) bits.push(`sl=${result.sl}`);
      if (Array.isArray(result.tickets) && result.tickets.length) {
        const ticketIds = result.tickets.map((item) => item.ticket ?? item).join(",");
        bits.push(`tickets=${ticketIds}`);
      }
      return bits.join(" · ");
    }
    if (result.reason) return String(result.reason);
  }

  if (item?.status === "parse_failed") return "LLM parse failed";
  if (item?.reason?.includes("OpenAI") || item?.reason?.includes("Gemini")) return String(item.reason);
  if (item?.status === "empty") return "No message text to analyze";
  return "—";
}

function canHardCopyTelegramMessage(item) {
  if (!item?.message_id) return false;
  const text = String(item?.text || item?.text_preview || "").trim();
  if (!text) return false;
  const upper = text.toUpperCase();
  if (/\b(BREAKEVEN|BREAK[\s-]?EVEN)\b/.test(upper)) return false;
  if (item?.parsed?.action && item.parsed.action !== "none") return true;
  return /\b(BUY|SELL)\b/.test(upper) && /\b(SL|STOP|TP|TARGET|STOPLOSS)\b/.test(upper);
}

function telegramActionPayload(item) {
  const payload = {};
  if (item?.parsed) payload.parsed = item.parsed;
  if (item?.result) payload.result = item.result;
  if (item?.trade_hash) payload.trade_hash = item.trade_hash;
  if (!Object.keys(payload).length) {
    if (item?.reason) payload.reason = item.reason;
    if (item?.status) payload.status = item.status;
  }
  return payload;
}

function telegramMessageText(item) {
  return String(item?.text || item?.text_preview || "").trim();
}

function renderTelegramExpandableText(text, rowKey, field) {
  const cleaned = text || "—";
  const needsToggle = cleaned.length > 180 || cleaned.includes("\n");
  if (!needsToggle) {
    return `<div class="telegram-msg-cell">${escapeHtml(cleaned)}</div>`;
  }
  const expanded = telegramExpandedFields.has(telegramExpandStorageKey(rowKey, field));
  return `
    <div class="telegram-msg-cell ${expanded ? "is-expanded" : "is-collapsed"}" data-expand-field="${escapeHtml(field)}" data-expand-key="${escapeHtml(rowKey)}">${escapeHtml(cleaned)}</div>
    <button type="button" class="telegram-expand-btn" data-expand-field="${escapeHtml(field)}" data-expand-key="${escapeHtml(rowKey)}">${expanded ? "See less" : "See more"}</button>
  `;
}

function renderTelegramActionJsonCell(item, rowKey, jsonOverride = null) {
  const payload = jsonOverride == null ? telegramActionPayload(item) : null;
  const json = jsonOverride ?? JSON.stringify(payload, null, 2);
  if (!json || json === "{}") {
    return `<span class="value-neutral">${escapeHtml(formatLlmResponse(item))}</span>`;
  }
  const expanded = telegramExpandedFields.has(telegramExpandStorageKey(rowKey, "json"));
  if (expanded) {
    return `
      <pre class="telegram-json-full" data-expand-target="json" data-expand-key="${escapeHtml(rowKey)}">${escapeHtml(json)}</pre>
      <button type="button" class="telegram-expand-btn" data-expand-field="json" data-expand-key="${escapeHtml(rowKey)}">Hide JSON</button>
    `;
  }
  const preview = json.length > 160 ? `${json.slice(0, 160)}…` : json;
  return `
    <div class="telegram-json-preview is-collapsed" data-expand-field="json" data-expand-key="${escapeHtml(rowKey)}">${escapeHtml(preview)}</div>
    <button type="button" class="telegram-expand-btn" data-expand-field="json" data-expand-key="${escapeHtml(rowKey)}">See JSON</button>
  `;
}

function renderTelegramMessageRow(item) {
  const status = String(item.status || "unknown");
  const statusClass = status === "placed" || status === "paper"
    ? "value-positive"
    : status === "watching" || status === "latest" || status === "breakeven" || status === "seen"
      ? "value-positive"
      : status.includes("failed")
        ? "value-negative"
        : status === "stale" || status === "empty"
          ? "value-negative"
          : "value-neutral";
  const rowKey = String(item.message_id || `${item.channel_name}-${item.updated_at}`);
  const isReply = Boolean(item.is_reply);
  const replyLabel = isReply
    ? '<span class="badge badge-muted">Yes</span>'
    : '<span class="badge badge-accent">No</span>';
  const hardCopyEnabled = canHardCopyTelegramMessage(item);
  const messageId = String(item.message_id || "");
  const actionCell = hardCopyEnabled
    ? `<button type="button" class="btn btn-primary btn-sm telegram-hard-copy-btn" data-message-id="${escapeHtml(messageId)}" title="Force place at market; only checks TPs vs live price">Hard copy</button>`
    : '<span class="value-neutral">—</span>';
  const messageCell = renderTelegramExpandableText(telegramMessageText(item), rowKey, "message");
  const actionPayload = telegramActionPayload(item);
  const actionJson = JSON.stringify(actionPayload, null, 2);
  return `
  <tr data-message-row="${escapeHtml(rowKey)}">
      <td class="${statusClass}">${escapeHtml(status)}</td>
      <td>${replyLabel}</td>
      <td>${formatTimestamp(item.updated_at)}</td>
      <td>${messageCell}</td>
      <td data-full-json="${encodeURIComponent(actionJson)}">${renderTelegramActionJsonCell(item, rowKey, actionJson)}</td>
      <td>${escapeHtml(String(item.reason || item.result?.reason || "—"))}</td>
      <td class="table-actions">${actionCell}</td>
    </tr>
  `;
}

function telegramMessagesFingerprintValue(messages) {
  return (messages || [])
    .map((item) => [
      item.message_id,
      item.status,
      item.updated_at,
      item.reason,
      item.result?.status,
      item.result?.reason,
    ].join(":"))
    .join("|");
}

function updateTelegramMessagesIfChanged(messages, channels = [], { force = false } = {}) {
  const fingerprint = telegramMessagesFingerprintValue(messages);
  if (!force && telegramUserInteracting) return;
  if (!force && fingerprint === telegramMessagesFingerprint) return;
  telegramMessagesFingerprint = fingerprint;
  renderTelegramMessages(messages, channels);
}

function renderTelegramMessages(messages, channels = []) {
  if (!els.telegramMessagesByChannel) return;
  if (!messages.length) {
    els.telegramMessagesByChannel.innerHTML = '<p class="empty-row">No Telegram messages tracked yet.</p>';
    return;
  }

  const channelOrder = (channels || []).map((channel) => channel.name);
  const grouped = new Map();
  for (const item of messages) {
    const name = String(item.channel_name || "Unknown channel");
    if (!grouped.has(name)) grouped.set(name, []);
    grouped.get(name).push(item);
  }

  const names = [...new Set([...channelOrder.filter(Boolean), ...grouped.keys()])];
  els.telegramMessagesByChannel.innerHTML = names
    .filter((name) => grouped.has(name))
    .map((name) => {
      const rows = grouped.get(name) || [];
      const sorted = rows.slice().sort((a, b) => String(b.updated_at || "").localeCompare(String(a.updated_at || "")));
      return `
        <section class="telegram-channel-group">
          <div class="telegram-channel-group-header">
            <h4>${escapeHtml(name)}</h4>
            <span class="telegram-channel-group-count">${sorted.length} message${sorted.length === 1 ? "" : "s"}</span>
          </div>
          <div class="table-wrap">
            <table class="data-table data-table-compact">
              <thead>
                <tr>
                  <th>Status</th>
                  <th>Reply</th>
                  <th>Updated</th>
                  <th>Message</th>
                  <th>Action JSON</th>
                  <th>Reason</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                ${sorted.map((item) => renderTelegramMessageRow(item)).join("")}
              </tbody>
            </table>
          </div>
        </section>
      `;
    })
    .join("");
  scheduleResponsiveTables();
}

function toggleTelegramExpand(button) {
  const field = button.dataset.expandField;
  const key = button.dataset.expandKey;
  if (!field || !key) return;
  const storageKey = telegramExpandStorageKey(key, field);
  const row = button.closest("tr");
  if (!row) return;

  if (field === "message") {
    const cell = row.querySelector(`.telegram-msg-cell[data-expand-key="${CSS.escape(key)}"]`);
    if (!cell) return;
    const collapsed = cell.classList.toggle("is-collapsed");
    cell.classList.toggle("is-expanded", !collapsed);
    if (collapsed) telegramExpandedFields.delete(storageKey);
    else telegramExpandedFields.add(storageKey);
    button.textContent = collapsed ? "See more" : "See less";
    return;
  }

  if (field === "json") {
    const cell = button.closest("td[data-full-json]");
    if (!cell) return;
    if (telegramExpandedFields.has(storageKey)) telegramExpandedFields.delete(storageKey);
    else telegramExpandedFields.add(storageKey);
    let json = "";
    try {
      json = decodeURIComponent(cell.dataset.fullJson || "");
    } catch (_error) {
      json = cell.dataset.fullJson || "";
    }
    cell.innerHTML = renderTelegramActionJsonCell({ message_id: key }, key, json);
    cell.dataset.fullJson = encodeURIComponent(json);
  }
}

function formatSignalParserLabel(telegram) {
  const openai = telegram.openai_api_key_configured
    ? `OpenAI ${telegram.openai_model || "gpt-4o-mini"}`
    : "OpenAI missing";
  const gemini = telegram.gemini_api_key_configured
    ? `Gemini ${telegram.gemini_model || "gemini"}`
    : "Gemini missing";
  return `${openai} · ${gemini} fallback`;
}

function renderTelegramConfig(config) {
  if (!config.telegram_signals) return;
  const telegram = config.telegram_signals;
  if (els.telegramLlm) {
    els.telegramLlm.textContent = formatSignalParserLabel(telegram);
  }
  if (els.telegramOpenGuard) {
    els.telegramOpenGuard.textContent = telegram.ignore_open_symbol_trades ? "On" : "Off";
  }
  if (els.telegramIgnoreOpen) {
    els.telegramIgnoreOpen.checked = Boolean(telegram.ignore_open_symbol_trades);
  }
  if (els.telegramProtectTp) {
    els.telegramProtectTp.checked = telegram.protect_tp !== false;
  }
  if (els.telegramBrowserHeadless && telegram.browser_headless != null) {
    els.telegramBrowserHeadless.checked = Boolean(telegram.browser_headless);
  }
  if (els.telegramChannels) {
    els.telegramChannels.textContent = `${(telegram.channels || []).filter((channel) => channel.enabled).length} active / ${(telegram.channels || []).length} total`;
  }
  renderTelegramChannels(telegram.channels || []);
  if (els.telegramPoll) {
    els.telegramPoll.textContent = `${telegram.poll_seconds}s`;
  }
  if (config.tradlia_signals && els.tradliaPoll) {
    els.tradliaPoll.textContent = `${config.tradlia_signals.poll_seconds}s`;
  }
}

function renderTradliaStatus(status) {
  if (!els.tradliaLabel) return;
  const running = Boolean(status.running);
  els.tradliaDot?.classList.toggle("running", running);
  els.tradliaLabel.textContent = running ? "Running" : "Stopped";
  if (els.tradliaStartBtn) els.tradliaStartBtn.disabled = running;
  if (els.tradliaStopBtn) els.tradliaStopBtn.disabled = !running;
  if (els.tradliaUpdated) {
    els.tradliaUpdated.textContent = `Tradlia: ${running ? "watching" : "stopped"}`;
    els.tradliaUpdated.classList.toggle("ok", running);
  }
  if (els.tradliaCounts) {
    els.tradliaCounts.textContent = `${status.messages_seen || 0} messages · ${status.placed || 0} placed`;
  }
  if (els.tradliaApi) {
    const ok = status.api_configured;
    els.tradliaApi.textContent = ok ? "Configured" : "Missing";
    els.tradliaApi.className = `value ${ok ? "value-positive" : "value-negative"}`;
  }
  if (els.tradliaLlm) {
    els.tradliaLlm.textContent = status.llm_configured ? "Ready" : "Missing API key";
  }
  if (els.tradliaPoll) {
    els.tradliaPoll.textContent = `${status.poll_seconds || "—"}s`;
  }
  const signal = status.last_signal;
  if (els.tradliaLastParsed) {
    els.tradliaLastParsed.textContent = formatTelegramParsedSignal(signal);
  }
  if (els.tradliaLast) {
    els.tradliaLast.textContent = status.last_channel
      ? `Last: ${status.last_channel}`
      : "Last signal: —";
  }
  if (els.tradliaActionLogBody && Array.isArray(status.recent_actions)) {
    const items = status.recent_actions.slice().reverse();
    els.tradliaActionLogBody.innerHTML = items.length
      ? items
          .map((item) => {
            const detail = item.reason || item.result?.execution_reason || item.result?.reason || "";
            return `
        <article class="telegram-action-log-item">
          <div class="telegram-action-log-head">
            <span class="${telegramStatusClass(item.status)}">${escapeHtml([item.kind, item.status, item.channel].filter(Boolean).join(" · "))}</span>
            <span class="mono">${formatTimestamp(item.at)}</span>
          </div>
          ${detail ? `<p class="telegram-action-log-detail">${escapeHtml(detail)}</p>` : ""}
        </article>`;
          })
          .join("")
      : '<p class="empty-row">No Tradlia copy actions yet.</p>';
  }
  const action = status.last_action;
  if (els.tradliaLastAction && els.tradliaLastActionJson) {
    if (action?.result) {
      if (els.tradliaLastActionMeta) {
        els.tradliaLastActionMeta.textContent = [action.channel, action.at, action.result?.status].filter(Boolean).join(" · ");
      }
      renderTelegramActionStatusBadge(els.tradliaLastActionStatus, action.result);
      els.tradliaLastActionJson.textContent = JSON.stringify(action, null, 2);
      els.tradliaLastAction.classList.remove("hidden");
    } else {
      els.tradliaLastAction.classList.add("hidden");
    }
  }
}

async function refreshTradliaStatus() {
  try {
    const response = await fetch("/api/tradlia-signals/status", { cache: "no-store" });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || "Failed to load Tradlia status");
    renderTradliaStatus(data);
    if (els.tradliaHint) {
      els.tradliaHint.textContent = data.running
        ? "Polling Tradlia for new signals…"
        : "Start when API credentials are set in config or environment variables.";
    }
    return data;
  } catch (error) {
    if (els.tradliaError) {
      els.tradliaError.textContent = error.message;
      els.tradliaError.classList.remove("hidden");
    }
    return null;
  }
}

async function startTradliaCopier() {
  if (botConfig && !botConfig.bot.dry_run) {
    const confirmed = window.confirm(
      "Live trading is enabled. Tradlia copied signals will place real MT5 orders. Continue?",
    );
    if (!confirmed) return;
  }
  setLoading(els.tradliaStartBtn, true);
  try {
    const response = await fetch("/api/tradlia-signals/start", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ protect_tp: Boolean(els.telegramProtectTp?.checked) }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || "Failed to start Tradlia copier");
    renderTradliaStatus(data);
    toast("Tradlia copier started", "success");
  } catch (error) {
    toast(error.message, "error");
  } finally {
    setLoading(els.tradliaStartBtn, false);
  }
}

async function stopTradliaCopier() {
  setLoading(els.tradliaStopBtn, true);
  try {
    const response = await fetch("/api/tradlia-signals/stop", { method: "POST" });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || "Failed to stop Tradlia copier");
    renderTradliaStatus(data);
    toast("Tradlia copier stopped", "info");
  } catch (error) {
    toast(error.message, "error");
  } finally {
    setLoading(els.tradliaStopBtn, false);
  }
}

function startTradliaPolling() {
  if (tradliaTimer) return;
  tradliaTimer = window.setInterval(() => {
    if (currentPage() !== "tradlia-signals") return;
    void refreshTradliaStatus();
  }, 5000);
}

function stopTradliaPolling() {
  if (!tradliaTimer) return;
  window.clearInterval(tradliaTimer);
  tradliaTimer = null;
}

async function refreshTelegramStatus({ full = false } = {}) {
  if (!els.telegramLabel) return;
  try {
    const response = await fetch("/api/telegram-signals/status", { cache: "no-store" });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || "Failed to load Telegram copier status");
    renderTelegramStatus(data, { full });
    void refreshDailyRiskStatus();
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
    renderTelegramStatus(data, { full: true });
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
    renderTelegramStatus(data, { full: true });
    toast("Telegram copier stopped", "info");
    await refreshLogs();
  } catch (error) {
    toast(error.message, "error");
  } finally {
    setLoading(els.telegramStopBtn, false);
  }
}

async function hardCopyTelegramMessage(messageId, button) {
  if (!messageId) {
    toast("Missing message id for hard copy. Refresh the page and try again.", "error");
    return;
  }
  const confirmed = window.confirm(
    "Hard copy this signal and place it at market now? Skips age, dedup, daily guard, and open-trade checks. Only validates TPs against live price.",
  );
  if (!confirmed) return;

  setLoading(button, true);
  try {
    const response = await fetch("/api/telegram-signals/hard-copy", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message_id: messageId }),
    });
    let data = {};
    try {
      data = await response.json();
    } catch (_error) {
      data = {};
    }
    if (!response.ok) {
      throw new Error(formatApiError(data.detail) || `Hard copy failed (${response.status})`);
    }
    renderTelegramStatus(data, { full: true });
    const copy = data.copy_result || data;
    const status = copy.status || "unknown";
    const accountSummary = formatTelegramAccountResults(copy.account_results || copy.result?.account_results);
    if (status === "placed" || status === "paper") {
      const legs = copy.legs || copy.tickets?.length || 1;
      const base = `Hard copy ${status}: ${copy.symbol || ""} ${String(copy.action || "").toUpperCase()} (${legs} leg${legs === 1 ? "" : "s"})`.trim();
      toast(accountSummary ? `${base} · ${accountSummary}` : base, "success");
    } else {
      toast(formatApiError(copy.reason) || accountSummary || `Hard copy ${status}`, "info");
    }
    await refreshLogs();
  } catch (error) {
    toast(error.message, "error");
  } finally {
    setLoading(button, false);
  }
}

async function clearTelegramMessages() {
  const confirmed = window.confirm(
    "Hard clear all Telegram messages from the state database, reset dedup cache, and wipe counters? This cannot be undone.",
  );
  if (!confirmed) return;

  setLoading(els.telegramClearBtn, true);
  try {
    const response = await fetch("/api/telegram-signals/clear-messages", { method: "POST" });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || "Failed to clear Telegram messages");
    renderTelegramStatus(data, { full: true });
    toast(
      `Hard cleared ${data.messages_removed || 0} message${data.messages_removed === 1 ? "" : "s"} from database`,
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
  if (currentPage() !== "telegram-signals") return;
  if (telegramTimer) clearInterval(telegramTimer);
  telegramTimer = setInterval(() => refreshTelegramStatus(), 5000);
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

  if (els.defaultForexLot && config.risk?.default_forex_lot != null) {
    els.defaultForexLot.value = config.risk.default_forex_lot;
  }
  if (els.appendBrokerSymbolSuffix) {
    els.appendBrokerSymbolSuffix.checked = config.mt5?.append_broker_symbol_suffix !== false;
  }
  syncMt5IsDemoInputs(config.mt5?.is_demo !== false);
  updateAccountTypeBadge(config);
  updateBrokerSymbolSuffixHint(config);
  syncDailyRiskSettings(config);

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
    syncSignalAlgorithmUi(config.bot?.signal_algorithm);
    syncForexTradeSettingsFromConfig(config.bot?.forex_trade);
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
  } catch (error) {
    toast(error.message, "error");
  }
}

function backtestLegCount(symbolRow) {
  return (symbolRow.position_legs ?? symbolRow.trade_logs?.reduce(
    (total, trade) => total + Number(trade.legs || (trade.tps || []).length || 1),
    0,
  ) ?? 0);
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
            <span class="backtest-trade-meta">${symbolRow.trade_logs.length} setup${symbolRow.trade_logs.length === 1 ? "" : "s"} · ${formatMoney(symbolRow.pnl)}</span>
            <span class="backtest-trade-meta">${backtestLegCount(symbolRow)} position leg${backtestLegCount(symbolRow) === 1 ? "" : "s"}</span>
          </summary>
          <div class="table-wrap table-wrap-wide">
            <table class="data-table data-table-backtest">
              <thead>
                <tr>
                  <th>Time</th>
                  <th>Side</th>
                  <th>Mode</th>
                  <th>Legs</th>
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
                        <td>${escapeHtml(trade.execution_mode || "split")}</td>
                        <td>${trade.legs || (trade.tps || []).length || 1}</td>
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

function formatExitKind(value) {
  if (!value) return "—";
  return String(value).replace(/_/g, " ").toUpperCase();
}

function renderBacktestDailyTradeRows(tradeRows, startBalance) {
  if (!tradeRows?.length) {
    return `<tr><td colspan="13" class="empty-row">No position legs this day.</td></tr>`;
  }

  const rows = [];
  if (startBalance != null) {
    rows.push(`
      <tr class="daily-trade-start">
        <td colspan="12">Day open balance</td>
        <td>${formatMoney(startBalance)}</td>
      </tr>
    `);
  }

  rows.push(
    ...tradeRows.map(
      (trade, index) => `
        <tr
          data-sort-row="true"
          data-sort-index="${index}"
          data-sort-exit="${escapeHtml(trade.exit_time || "")}"
          data-sort-symbol="${escapeHtml(trade.symbol || "")}"
          data-sort-side="${escapeHtml(trade.side || "")}"
          data-sort-leg="${Number(trade.leg || 0)}"
          data-sort-entry="${Number(trade.entry ?? 0)}"
          data-sort-sl="${Number(trade.sl ?? 0)}"
          data-sort-tp="${Number(trade.tp ?? 0)}"
          data-sort-exit-price="${Number(trade.exit_price ?? 0)}"
          data-sort-lot="${Number(trade.lot ?? 0)}"
          data-sort-pnl="${Number(trade.pnl ?? 0)}"
          data-sort-balance="${Number(trade.balance_after ?? 0)}"
          data-sort-exit-kind="${escapeHtml(formatExitKind(trade.exit_kind))}"
        >
          <td class="row-number">${index + 1}</td>
          <td>${formatTimestamp(trade.exit_time)}</td>
          <td><strong>${escapeHtml(trade.symbol || "—")}</strong></td>
          <td class="side-${trade.side || ""}">${trade.side ? String(trade.side).toUpperCase() : "—"}</td>
          <td>${trade.leg && trade.legs ? `${trade.leg}/${trade.legs}` : "—"}</td>
          <td>${formatOptionalPrice(trade.entry)}</td>
          <td>${formatOptionalPrice(trade.sl)}</td>
          <td>${formatOptionalPrice(trade.tp)}</td>
          <td>${formatOptionalPrice(trade.exit_price)}</td>
          <td>${trade.lot ?? "—"}</td>
          <td class="${pnlClass(trade.pnl)}">${formatMoney(trade.pnl)}</td>
          <td>${formatMoney(trade.balance_after)}</td>
          <td>${escapeHtml(formatExitKind(trade.exit_kind))}</td>
        </tr>
      `,
    ),
  );

  return rows.join("");
}

function renderBacktestDaily(dailyRows) {
  if (!dailyRows || !dailyRows.length) {
    els.backtestDailyWrap.classList.add("hidden");
    els.backtestDailyBody.innerHTML = "";
    return;
  }

  els.backtestDailyBody.innerHTML = dailyRows
    .map(
      (row, index) => `
        <tr
          class="backtest-daily-row"
          data-sort-row="true"
          data-sort-index="${index}"
          data-sort-date="${escapeHtml(row.date || "")}"
          data-sort-legs="${Number(row.trades || 0)}"
          data-sort-wins="${Number(row.wins || 0)}"
          data-sort-pnl="${Number(row.pnl || 0)}"
          data-sort-balance="${Number(row.balance || 0)}"
        >
          <td class="daily-date-cell">
            <button type="button" class="daily-expand-btn" aria-expanded="false" aria-label="Show trades for ${escapeHtml(row.date)}">▸</button>
            <strong>${escapeHtml(row.date)}</strong>
          </td>
          <td>${row.trades}</td>
          <td>${row.wins} / ${row.losses}</td>
          <td class="${pnlClass(row.pnl)}">${formatMoney(row.pnl)}</td>
          <td>${formatMoney(row.balance)}</td>
        </tr>
        <tr class="backtest-daily-detail hidden">
          <td colspan="5">
            <div class="daily-trades-inner table-wrap">
              <table class="data-table data-table-compact data-table-backtest daily-trades-table">
                <thead>
                  <tr>
                    <th>#</th>
                    <th>${sortHeader("Exit (UTC)", "exit", "date", "asc")}</th>
                    <th>${sortHeader("Symbol", "symbol")}</th>
                    <th>${sortHeader("Side", "side")}</th>
                    <th>${sortHeader("Leg", "leg", "number", "asc")}</th>
                    <th>${sortHeader("Entry", "entry", "number")}</th>
                    <th>${sortHeader("SL", "sl", "number")}</th>
                    <th>${sortHeader("TP", "tp", "number")}</th>
                    <th>${sortHeader("Exit price", "exit-price", "number")}</th>
                    <th>${sortHeader("Lot", "lot", "number")}</th>
                    <th>${sortHeader("PnL", "pnl", "number")}</th>
                    <th>${sortHeader("Balance after", "balance", "number")}</th>
                    <th>${sortHeader("Exit", "exit-kind")}</th>
                  </tr>
                </thead>
                <tbody>
                  ${renderBacktestDailyTradeRows(row.trade_rows, row.start_balance)}
                </tbody>
              </table>
            </div>
          </td>
        </tr>
      `,
    )
    .join("");
  els.backtestDailyWrap.classList.remove("hidden");
}

function toggleBacktestDailyRow(button) {
  const summaryRow = button.closest(".backtest-daily-row");
  const detailRow = summaryRow?.nextElementSibling;
  if (!detailRow?.classList.contains("backtest-daily-detail")) return;

  const expanded = button.getAttribute("aria-expanded") === "true";
  button.setAttribute("aria-expanded", expanded ? "false" : "true");
  button.textContent = expanded ? "▸" : "▾";
  detailRow.classList.toggle("hidden", expanded);
  summaryRow.classList.toggle("is-expanded", !expanded);
}

function renderBacktestResult(data) {
  els.backtestRaw.textContent = JSON.stringify(data, null, 2);

  const totalClass = pnlClass(data.total_pnl);
  const rawSignals = (data.symbols || []).reduce((sum, row) => sum + (row.raw_signals || 0), 0);
  const skippedSignals = (data.symbols || []).reduce((sum, row) => sum + (row.skipped_signals || 0), 0);
  const rules = data.decision_rules || {};
  const pollHint = rules.poll_seconds ? `${rules.poll_seconds}s poll · ${rules.scan_bars || 600} bars` : "";
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
      <span class="label">Live mirror</span>
      <span class="value" style="font-size:0.85rem">${escapeHtml(pollHint)} · ${rules.enabled_symbols ?? "—"} symbols</span>
    </div>
    <div class="summary-card">
      <span class="label">Signal gate</span>
      <span class="value" style="font-size:0.95rem">${rawSignals} raw / ${skippedSignals} skipped</span>
    </div>
  `;
  els.backtestSummary.classList.remove("hidden");
  els.backtestResults.classList.remove("hidden");
  renderBacktestDaily(data.daily_performance);

  els.backtestBody.innerHTML = (data.symbols || [])
    .map(
      (row, index) => row.error
        ? `
        <tr
          data-sort-row="true"
          data-sort-index="${index}"
          data-sort-symbol="${escapeHtml(row.symbol || "")}"
          data-sort-signals="${Number(row.raw_signals || 0)}"
          data-sort-setups="0"
          data-sort-legs="0"
          data-sort-win-rate="0"
          data-sort-pnl="-999999999"
          data-sort-dd="999999999"
        >
          <td><strong>${escapeHtml(row.symbol)}</strong><div class="tag">${escapeHtml(row.name)} · ${escapeHtml(row.timeframe || "")}</div></td>
          <td colspan="7" class="value-negative">${escapeHtml(row.error)}</td>
        </tr>
      `
      : `
        <tr
          data-sort-row="true"
          data-sort-index="${index}"
          data-sort-symbol="${escapeHtml(row.symbol || "")}"
          data-sort-signals="${Number(row.raw_signals ?? row.trades ?? 0)}"
          data-sort-setups="${Number(row.trades || 0)}"
          data-sort-legs="${Number(row.position_legs ?? backtestLegCount(row))}"
          data-sort-win-rate="${Number(row.win_rate || 0)}"
          data-sort-pnl="${Number(row.pnl || 0)}"
          data-sort-dd="${Number(row.max_drawdown || 0)}"
        >
          <td><strong>${escapeHtml(row.symbol)}</strong><div class="tag">${escapeHtml(row.name)} · ${escapeHtml(row.timeframe || "")}</div></td>
          <td>${row.raw_signals ?? row.trades} raw / ${row.skipped_signals ?? 0} skipped</td>
          <td>${row.trades}</td>
          <td>${row.position_legs ?? backtestLegCount(row)}</td>
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
  scheduleResponsiveTables();
}

async function loadConfig() {
  const page = currentPage();
  if (page === "settings") {
    await loadSymbolSettings();
    await loadForexTradeSettings();
    return;
  }
  const response = await fetch("/api/config", { cache: "no-store" });
  if (!response.ok) throw new Error("Failed to load config");
  const config = await response.json();
  renderConfig(config);
}

async function loadSymbolSettings() {
  const response = await fetch("/api/symbols", { cache: "no-store" });
  if (!response.ok) throw new Error("Failed to load symbol settings");
  const data = await response.json();
  symbolSettingsReady = false;
  if (botConfig) {
    botConfig.symbols = data.symbols || [];
    botConfig.symbol_stats = data.symbol_stats || null;
    botConfig.risk = botConfig.risk || {};
    if (data.default_forex_lot != null) botConfig.risk.default_forex_lot = data.default_forex_lot;
    if (data.timeframe_options) botConfig.timeframe_options = data.timeframe_options;
    if (data.broker_symbol_suffix) {
      botConfig.mt5 = botConfig.mt5 || {};
      botConfig.mt5.broker_symbol_suffix = data.broker_symbol_suffix;
    }
    if (data.append_broker_symbol_suffix != null) {
      botConfig.mt5 = botConfig.mt5 || {};
      botConfig.mt5.append_broker_symbol_suffix = data.append_broker_symbol_suffix;
    }
    if (data.is_demo != null) {
      botConfig.mt5 = botConfig.mt5 || {};
      botConfig.mt5.is_demo = Boolean(data.is_demo);
    }
  } else {
    botConfig = {
      symbols: data.symbols || [],
      symbol_stats: data.symbol_stats || null,
      risk: { default_forex_lot: data.default_forex_lot },
      timeframe_options: data.timeframe_options || [],
      mt5: {
        broker_symbol_suffix: data.broker_symbol_suffix || "-VIP",
        append_broker_symbol_suffix: data.append_broker_symbol_suffix !== false,
        is_demo: data.is_demo !== false,
      },
    };
  }
  try {
    renderSymbols(data.symbols || []);
  } catch (error) {
    if (els.symbolsBody) {
      els.symbolsBody.innerHTML = `<tr><td colspan="8" class="empty-row">${escapeHtml(error.message)}</td></tr>`;
    }
    throw error;
  }
  symbolSettingsReady = true;
  if (els.defaultForexLot && data.default_forex_lot != null) {
    els.defaultForexLot.value = data.default_forex_lot;
  }
  if (els.appendBrokerSymbolSuffix) {
    els.appendBrokerSymbolSuffix.checked = data.append_broker_symbol_suffix !== false;
  }
  if (data.is_demo != null) {
    syncMt5IsDemoInputs(data.is_demo);
    if (botConfig) {
      botConfig.mt5 = botConfig.mt5 || {};
      botConfig.mt5.is_demo = Boolean(data.is_demo);
    }
    updateAccountTypeBadge(botConfig);
  }
  updateBrokerSymbolSuffixHint(botConfig);
  updateSymbolStats(data.symbol_stats);
}

async function runBacktest(event) {
  event.preventDefault();

  const start = localInputToIso(els.start.value);
  const end = localInputToIso(els.end.value);
  const startingBalance = Number(els.startingBalance.value);

  if (!Number.isFinite(startingBalance) || startingBalance <= 0) {
    toast("Starting balance must be greater than 0", "error");
    return;
  }

  setLoading(els.backtestBtn, true, "Running backtest…");

  try {
    const signalAlgorithm = els.backtestSignalAlgorithm?.value || botConfig?.bot?.signal_algorithm || "rsi_divergence";
    toast(`Backtest running (${formatSignalAlgorithm(signalAlgorithm)})`, "info");
    const query = new URLSearchParams({
      start,
      end,
      starting_balance: String(startingBalance),
      signal_algorithm: signalAlgorithm,
    });
    const response = await fetch(`/api/backtest?${query.toString()}`);
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

  const aiParsed = els.manualTradeText?.dataset.aiParsed === "true";
  const confirmed = window.confirm(
    aiParsed
      ? `AI parsed this signal:\n\n${text}\n\nReview it carefully. Place real MT5 market orders now?`
      : "This will place real MT5 market orders with the pasted SL and TPs. Continue?",
  );
  if (!confirmed) return;

  setLoading(els.manualTradeBtn, true, "Sending live trade...");
  try {
    const response = await fetch("/api/manual-trade", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text, confirm_live: true }),
    });
    let data = {};
    try {
      data = await response.json();
    } catch (_error) {
      data = {};
    }
    if (!response.ok) {
      throw new Error(formatApiError(data.detail) || `Manual trade failed (${response.status})`);
    }
    renderManualTradeResult(data);
    const status = String(data.status || "");
    const placed = data.tickets?.length || (data.ticket ? 1 : 0);
    const failed = data.failed?.length || 0;
    if (status === "placed" || status === "paper") {
      toast(`Manual trade sent: ${placed} placed`, "success");
    } else {
      toast(formatManualTradeFailure(data), "error");
    }
    if (els.manualTradeText) delete els.manualTradeText.dataset.aiParsed;
    await refreshLiveData();
    await refreshLogs();
  } catch (error) {
    renderManualTradeResult({ status: "failed", reason: error.message });
    toast(error.message, "error");
  } finally {
    setLoading(els.manualTradeBtn, false);
  }
}

function clearManualTradeResult() {
  els.manualTradeResult?.classList.add("hidden");
  els.manualTradeResult?.classList.remove("is-failed", "is-success", "is-paper");
  if (els.manualTradeStatus) els.manualTradeStatus.textContent = "";
  if (els.manualTradeResultSummary) els.manualTradeResultSummary.textContent = "";
}

function formatManualTradeFailure(data) {
  if (data?.reason) return String(data.reason);
  if (Array.isArray(data?.failed) && data.failed.length) {
    return data.failed.map((item) => item.reason || item.error || JSON.stringify(item)).join("; ");
  }
  if (data?.retcode != null) return `MT5 retcode=${data.retcode}`;
  return "Trade failed — see details below";
}

function renderManualTradeResult(data) {
  if (!els.manualTradeResult || !els.manualTradeStatus) return;
  const status = String(data?.status || "unknown");
  const isSuccess = status === "placed" || status === "paper";
  const isFailed = status === "failed" || status === "skipped" || status === "error";
  els.manualTradeResult.classList.toggle("is-failed", isFailed);
  els.manualTradeResult.classList.toggle("is-success", isSuccess);
  els.manualTradeResult.classList.toggle("is-paper", status === "paper");
  let summary = "";
  if (data?.quick_test) {
    summary = isSuccess
      ? `Quick test OK — ${data.symbol || "EURUSD"} ${String(data.side || "buy").toUpperCase()} @ ${data.entry_price ?? data.entry ?? "market"}`
      : formatManualTradeFailure(data);
  } else if (isSuccess) {
    const tickets = data.tickets?.length || (data.ticket ? 1 : 0);
    summary = status === "paper"
      ? `Paper trade OK — ${data.symbol} ${String(data.side || "").toUpperCase()} (${data.lot} lot)`
      : `Trade placed — ${tickets} ticket(s) on ${data.symbol} ${String(data.side || "").toUpperCase()}`;
  } else if (isFailed) {
    summary = formatManualTradeFailure(data);
  } else {
    summary = `Status: ${status}`;
  }
  if (els.manualTradeResultSummary) els.manualTradeResultSummary.textContent = summary;
  els.manualTradeStatus.textContent = JSON.stringify(data, null, 2);
  els.manualTradeResult.classList.remove("hidden");
}

async function placeMt5QuickTest(symbol, triggerBtn, volume = 0.01) {
  const normalized = String(symbol || "EURUSD").trim().toUpperCase();
  const live = isLiveTradingMode();
  const confirmed = window.confirm(
    live
      ? `Place LIVE ${normalized} ${volume} BUY test trade? No SL/TP — close manually in MT5. This only checks that orders reach the broker.`
      : `Place paper ${normalized} ${volume} BUY test trade?`,
  );
  if (!confirmed) return;

  setLoading(triggerBtn, true, "Sending test...");
  try {
    const response = await fetch("/api/mt5/test-trade", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        symbol: normalized,
        side: "buy",
        volume,
        confirm_live: live,
      }),
    });
    let data = {};
    try {
      data = await response.json();
    } catch (_error) {
      data = {};
    }
    if (!response.ok) {
      throw new Error(formatApiError(data.detail) || `Quick test failed (${response.status})`);
    }
    renderManualTradeResult({
      ...data,
      quick_test: true,
      symbol: data.symbol || normalized,
      side: data.side || "buy",
    });
    if (data.status === "placed" || data.status === "paper") {
      toast(`${normalized} quick test ${data.status}`, "success");
    } else {
      toast(formatManualTradeFailure(data), "error");
    }
    await refreshLiveData();
    await refreshLogs();
  } catch (error) {
    renderManualTradeResult({
      status: "failed",
      reason: error.message,
      quick_test: true,
      symbol: normalized,
      side: "buy",
    });
    toast(error.message, "error");
  } finally {
    setLoading(triggerBtn, false);
  }
}

function readClipboardImageFile(clipboardData) {
  const items = clipboardData?.items;
  if (!items) return null;
  for (const item of items) {
    if (!item.type.startsWith("image/")) continue;
    const file = item.getAsFile();
    if (file) return file;
  }
  return null;
}

function handleManualTradeImagePaste(event) {
  if (currentPage() !== "manual-trade") return;
  const file = readClipboardImageFile(event.clipboardData);
  if (!file) return;
  event.preventDefault();
  bindManualTradeImageInput(file);
  els.manualTradeImageDrop?.classList.add("is-focused");
  toast("Screenshot pasted — click Parse image with AI", "success");
}

function setManualTradeImageFile(file) {
  manualTradeImageFile = file || null;
  if (els.manualTradeParseBtn) els.manualTradeParseBtn.disabled = !manualTradeImageFile;
  if (!els.manualTradeImageName) return;
  if (!manualTradeImageFile) {
    els.manualTradeImageName.textContent = "No image selected";
    if (els.manualTradeImagePreview) {
      els.manualTradeImagePreview.src = "";
      els.manualTradeImagePreview.classList.add("hidden");
    }
    return;
  }
  els.manualTradeImageName.textContent = `${manualTradeImageFile.name || "Pasted image"} (${Math.round(manualTradeImageFile.size / 1024)} KB)`;
  if (els.manualTradeImagePreview) {
    els.manualTradeImagePreview.src = URL.createObjectURL(manualTradeImageFile);
    els.manualTradeImagePreview.classList.remove("hidden");
  }
}

function bindManualTradeImageInput(file) {
  if (!file || !file.type?.startsWith("image/")) {
    toast("Choose an image file", "error");
    return;
  }
  setManualTradeImageFile(file);
}

async function parseManualTradeImage() {
  if (!manualTradeImageFile) {
    toast("Choose or paste an image first", "error");
    return;
  }
  setLoading(els.manualTradeParseBtn, true, "Parsing image…");
  try {
    const formData = new FormData();
    formData.append("image", manualTradeImageFile, manualTradeImageFile.name || "signal.png");
    const response = await fetch("/api/manual-trade/parse-image", {
      method: "POST",
      body: formData,
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || "Image parse failed");

    const parsedText = String(data.text || "").trim();
    if (!parsedText) throw new Error("AI returned an empty trade signal");

    const reviewConfirmed = window.confirm(
      `AI parsed this trade signal (${data.provider || "llm"}):\n\n${parsedText}\n\nUse this text in the box below? You can edit it before placing the trade.`,
    );
    if (!reviewConfirmed) {
      toast("Image parse cancelled", "info");
      return;
    }

    if (els.manualTradeText) {
      els.manualTradeText.value = parsedText;
      els.manualTradeText.dataset.aiParsed = "true";
      els.manualTradeText.focus();
    }
    if (els.manualTradeParseHint) {
      els.manualTradeParseHint.textContent =
        `AI parsed via ${data.provider || "LLM"}. Review the text below, edit if needed, then click Place live test trade.`;
      els.manualTradeParseHint.classList.remove("hidden");
    }
    toast("Trade signal loaded from image — review before placing", "success");
  } catch (error) {
    toast(error.message, "error");
  } finally {
    setLoading(els.manualTradeParseBtn, false);
  }
}

function initManualTradeImageInput() {
  els.manualTradeImageBtn?.addEventListener("click", () => els.manualTradeImageInput?.click());
  els.manualTradeImageInput?.addEventListener("change", (event) => {
    const file = event.target.files?.[0];
    if (file) bindManualTradeImageInput(file);
  });
  els.manualTradeParseBtn?.addEventListener("click", parseManualTradeImage);
  document.addEventListener("paste", handleManualTradeImagePaste);
  els.manualTradeImageDrop?.addEventListener("click", (event) => {
    if (event.target.closest("button, input, a")) return;
    els.manualTradeImageDrop.focus();
    els.manualTradeImageDrop.classList.add("is-focused");
  });
  els.manualTradeImageDrop?.addEventListener("focus", () => {
    els.manualTradeImageDrop.classList.add("is-focused");
  });
  els.manualTradeImageDrop?.addEventListener("blur", () => {
    els.manualTradeImageDrop.classList.remove("is-focused");
  });
  els.manualTradeImageDrop?.addEventListener("dragover", (event) => {
    event.preventDefault();
    els.manualTradeImageDrop.classList.add("is-dragover");
  });
  els.manualTradeImageDrop?.addEventListener("dragleave", () => {
    els.manualTradeImageDrop.classList.remove("is-dragover");
  });
  els.manualTradeImageDrop?.addEventListener("drop", (event) => {
    event.preventDefault();
    els.manualTradeImageDrop.classList.remove("is-dragover");
    const file = event.dataTransfer?.files?.[0];
    if (file) bindManualTradeImageInput(file);
  });
  els.manualTradeText?.addEventListener("input", () => {
    if (els.manualTradeText.dataset.aiParsed) delete els.manualTradeText.dataset.aiParsed;
  });
}

function startLogPolling() {
  if (currentPage() !== "logs") return;
  if (logTimer) clearInterval(logTimer);
  logTimer = setInterval(refreshLogs, 1500);
}

async function init() {
  applyPageVisibility();

  try {
    await loadConfig();
  } catch (error) {
    toast(error.message, "error");
  }

  window.addEventListener("app:toast", (event) => {
    toast(event.detail.message, event.detail.type || "info");
  });
  window.addEventListener("resize", updateResponsiveTables, { passive: true });
  els.navToggle?.addEventListener("click", toggleMobileNav);
  els.mainNav?.addEventListener("click", (event) => {
    if (event.target.closest(".nav-link")) closeMobileNav();
  });
  document.addEventListener("click", (event) => {
    const button = event.target.closest(".sort-button[data-sort-key]");
    if (!button) return;
    applySortableTableSort(button);
  });

  els.backtestForm?.addEventListener("submit", runBacktest);
  els.backtestDailyBody?.addEventListener("click", (event) => {
    const button = event.target.closest(".daily-expand-btn");
    if (button) toggleBacktestDailyRow(button);
  });
  els.runOnceBtn?.addEventListener("click", runOnce);
  els.manualTradeForm?.addEventListener("submit", placeManualTrade);
  els.manualTradeQuickTestEurusdBtn?.addEventListener("click", () => {
    void placeMt5QuickTest("EURUSD", els.manualTradeQuickTestEurusdBtn);
  });
  els.manualTradeQuickTestBtcusdBtn?.addEventListener("click", () => {
    void placeMt5QuickTest("BTCUSD", els.manualTradeQuickTestBtcusdBtn);
  });
  els.manualTradeDismissBtn?.addEventListener("click", clearManualTradeResult);
  initManualTradeImageInput();
  els.liveSummaryForm?.addEventListener("submit", loadLiveSummary);
  els.resetLotsBtn?.addEventListener("click", resetLots);
  els.resetTimeframesBtn?.addEventListener("click", resetTimeframes);
  els.optimizeTimeframesBtn?.addEventListener("click", optimizeTimeframes);
  els.saveLotsBtn?.addEventListener("click", saveLots);
  els.addCustomSymbolForm?.addEventListener("submit", addCustomSymbol);
  els.forexTradeSaveBtn?.addEventListener("click", () => saveForexTradeSettings({ silent: false }));
  els.snapshotForm?.addEventListener("submit", saveSnapshot);
  els.mt5TestTradeBtn?.addEventListener("click", placeMt5TestTrade);
  els.snapshotRefreshBtn?.addEventListener("click", refreshSnapshots);
  els.snapshotsBody?.addEventListener("click", (event) => {
    const applyBtn = event.target.closest(".snapshot-apply-btn");
    if (applyBtn) {
      applySnapshot(applyBtn.dataset.slug, applyBtn.dataset.name);
      return;
    }
    const deleteBtn = event.target.closest(".snapshot-delete-btn");
    if (deleteBtn) {
      deleteSnapshot(deleteBtn.dataset.slug, deleteBtn.dataset.name);
    }
  });
  els.symbolsBody?.addEventListener("change", (event) => {
    if (!event.target.matches(".lot-input, .symbol-enabled, .symbol-signal-active, .timeframe-select")) return;
    const row = event.target.closest("tr");
    if (row && (event.target.matches(".symbol-enabled") || event.target.matches(".symbol-signal-active"))) {
      row.classList.toggle("row-disabled", !row.querySelector(".symbol-enabled")?.checked);
      row.classList.toggle("row-signal-inactive", !row.querySelector(".symbol-signal-active")?.checked);
    }
    scheduleSettingsSync({ persist: false, silent: true });
  });
  els.defaultForexLot?.addEventListener("change", () => {
    scheduleSettingsSync({ persist: false, silent: true });
  });
  els.appendBrokerSymbolSuffix?.addEventListener("change", () => {
    updateBrokerSymbolSuffixHint({
      mt5: {
        broker_symbol_suffix: botConfig?.mt5?.broker_symbol_suffix || "-VIP",
        append_broker_symbol_suffix: appendBrokerSymbolSuffixFromUi(),
      },
    });
    scheduleSettingsSync({ persist: false, silent: true });
  });
  for (const input of els.mt5IsDemoInputs()) {
    input.addEventListener("change", () => {
      const isDemo = mt5IsDemoFromUi();
      syncMt5IsDemoInputs(isDemo);
      if (botConfig) {
        botConfig.mt5 = botConfig.mt5 || {};
        botConfig.mt5.is_demo = Boolean(isDemo);
      }
      updateAccountTypeBadge(botConfig);
      void syncMt5IsDemoSetting({ persist: true, silent: false });
    });
  }
  els.autoRunStartBtn?.addEventListener("click", startAutoRun);
  els.autoRunStopBtn?.addEventListener("click", stopAutoRun);
  els.autoRunSaveBtn?.addEventListener("click", () => saveBotStrategy({ silent: false, persist: true }));
  els.autoRunStrategy?.addEventListener("change", () => onBotSettingsChanged());
  els.autoRunSignalAlgorithm?.addEventListener("change", () => onBotSettingsChanged());
  els.dailyLossGuardEnabled?.addEventListener("change", () => onDailyLossSettingsChanged("live"));
  els.dailyLossGuardPct?.addEventListener("change", () => onDailyLossSettingsChanged("live"));
  els.dailyWinGuardEnabled?.addEventListener("change", () => onDailyLossSettingsChanged("live"));
  els.dailyWinTargetMode?.addEventListener("change", () => onDailyLossSettingsChanged("live"));
  els.dailyWinTargetValue?.addEventListener("change", () => onDailyLossSettingsChanged("live"));
  els.telegramDailyLossGuardEnabled?.addEventListener("change", () => onDailyLossSettingsChanged("telegram"));
  els.telegramDailyLossGuardPct?.addEventListener("change", () => onDailyLossSettingsChanged("telegram"));
  els.telegramDailyWinGuardEnabled?.addEventListener("change", () => onDailyLossSettingsChanged("telegram"));
  els.telegramDailyWinTargetMode?.addEventListener("change", () => onDailyLossSettingsChanged("telegram"));
  els.telegramDailyWinTargetValue?.addEventListener("change", () => onDailyLossSettingsChanged("telegram"));
  els.telegramStartBtn?.addEventListener("click", startTelegramSignals);
  els.telegramStopBtn?.addEventListener("click", stopTelegramSignals);
  els.tradliaStartBtn?.addEventListener("click", startTradliaCopier);
  els.tradliaStopBtn?.addEventListener("click", stopTradliaCopier);
  els.telegramSaveBtn?.addEventListener("click", () => saveTelegramSettings({ silent: false }));
  els.telegramClearBtn?.addEventListener("click", clearTelegramMessages);
  els.telegramChannelForm?.addEventListener("submit", addTelegramChannel);
  const onTelegramSettingChanged = () => {
    saveTelegramSettings({ silent: true }).catch(() => {});
  };
  els.telegramIgnoreOpen?.addEventListener("change", onTelegramSettingChanged);
  els.telegramProtectTp?.addEventListener("change", onTelegramSettingChanged);
  els.telegramChannelsBody?.addEventListener("click", async (event) => {
    const enableBtn = event.target.closest(".telegram-channel-enable-btn");
    if (enableBtn) {
      try {
        await updateTelegramChannel(enableBtn.dataset.url, { enabled: true });
        toast("Channel enabled", "success");
      } catch (error) {
        toast(error.message, "error");
      }
      return;
    }
    const disableBtn = event.target.closest(".telegram-channel-disable-btn");
    if (disableBtn) {
      try {
        await updateTelegramChannel(disableBtn.dataset.url, { enabled: false });
        toast("Channel disabled — skipped on next poll", "info");
      } catch (error) {
        toast(error.message, "error");
      }
      return;
    }
    const button = event.target.closest(".telegram-channel-remove-btn");
    if (button) removeTelegramChannel(button.dataset.url);
  });
  els.telegramMessagesByChannel?.addEventListener("pointerdown", () => {
    telegramUserInteracting = true;
  });
  els.telegramMessagesByChannel?.addEventListener("focusin", () => {
    telegramUserInteracting = true;
  });
  document.addEventListener("pointerdown", (event) => {
    if (!els.telegramMessagesByChannel?.contains(event.target)) {
      telegramUserInteracting = false;
    }
  });
  els.telegramMessagesByChannel?.addEventListener("click", (event) => {
    const expandBtn = event.target.closest(".telegram-expand-btn");
    if (expandBtn) {
      toggleTelegramExpand(expandBtn);
      return;
    }
    const hardCopyBtn = event.target.closest(".telegram-hard-copy-btn");
    if (!hardCopyBtn) return;
    hardCopyTelegramMessage(hardCopyBtn.dataset.messageId, hardCopyBtn);
  });
  els.refreshLogsBtn?.addEventListener("click", refreshLogs);
  els.logFilter?.addEventListener("input", renderLogs);

  setDefaultLiveSummaryPeriod();

  window.addEventListener("app:strategy-change", (event) => {
    const strategy = event.detail?.strategy;
    if (!strategy) return;
    syncStrategyUi(strategy);
  });

  window.applyBotStrategy = saveBotStrategy;
  window.selectedBotStrategy = selectedStrategy;

  window.addEventListener("pageshow", (event) => {
    if (event.persisted) {
      void loadConfig().catch((error) => toast(error.message, "error"));
      if (currentPage() === "home") {
        void refreshAutoRunStatus(true);
        void refreshLiveData();
      }
    }
  });

  const page = currentPage();
  if (page === "logs") {
    startLogPolling();
    void refreshLogs();
  }
  if (page === "home") {
    startLoopPolling();
    startLivePolling();
    startDailyGuardClock();
    void refreshAutoRunStatus(true);
    void refreshDailyRiskStatus();
    void refreshLiveData();
  } else if (page === "telegram-signals") {
    startTelegramPolling();
    startDailyGuardClock();
    void refreshTelegramStatus({ full: true });
  } else if (page === "tradlia-signals") {
    startTradliaPolling();
    void refreshTradliaStatus();
  } else if (page === "live-summary") {
    void loadLiveSummary();
  }

  if (botConfig && window.ChartPreview) {
    try {
      ChartPreview.initChartPreview(botConfig);
    } catch (error) {
      toast(error.message, "error");
    }
  }

  void loadSnapshots().catch((error) => toast(error.message, "error"));
  scheduleResponsiveTables();
}

init();

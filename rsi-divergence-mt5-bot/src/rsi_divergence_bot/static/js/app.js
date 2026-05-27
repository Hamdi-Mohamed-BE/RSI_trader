const SIGNAL_ALGORITHM_LABELS = {
  rsi_divergence: "RSI divergence",
  silver_optimized: "Silver optimized (XAU/XAG/BTC trend pullback)",
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
  "mt5-accounts": "MT5 accounts",
  "manual-trade": "Manual trade",
  "live-summary": "Live summary",
  "telegram-signals": "Telegram signals",
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
  snapshotForm: document.getElementById("snapshot-form"),
  snapshotName: document.getElementById("snapshot-name"),
  snapshotNote: document.getElementById("snapshot-note"),
  snapshotSaveBtn: document.getElementById("snapshot-save-btn"),
  snapshotRefreshBtn: document.getElementById("snapshot-refresh-btn"),
  snapshotApplyPersist: document.getElementById("snapshot-apply-persist"),
  snapshotsBody: document.getElementById("snapshots-body"),
  mt5TradingMode: document.getElementById("mt5-trading-mode"),
  mt5ActiveAccount: document.getElementById("mt5-active-account"),
  mt5AccountsStatus: document.getElementById("mt5-accounts-status"),
  mt5AccountForm: document.getElementById("mt5-account-form"),
  mt5AccountName: document.getElementById("mt5-account-name"),
  mt5AccountLogin: document.getElementById("mt5-account-login"),
  mt5AccountPassword: document.getElementById("mt5-account-password"),
  mt5AccountServer: document.getElementById("mt5-account-server"),
  mt5AccountSuffix: document.getElementById("mt5-account-suffix"),
  mt5AccountPath: document.getElementById("mt5-account-path"),
  mt5AccountEnabled: document.getElementById("mt5-account-enabled"),
  mt5AccountPrimary: document.getElementById("mt5-account-primary"),
  mt5AccountSaveBtn: document.getElementById("mt5-account-save-btn"),
  mt5AccountsBody: document.getElementById("mt5-accounts-body"),
  mt5AccountsReloadBtn: document.getElementById("mt5-accounts-reload-btn"),
  mt5AccountFormTitle: document.getElementById("mt5-account-form-title"),
  mt5AccountEditId: document.getElementById("mt5-account-edit-id"),
  mt5AccountCancelBtn: document.getElementById("mt5-account-cancel-btn"),
  mt5TestTradeBtn: document.getElementById("mt5-test-trade-btn"),
  mt5TestTradeResult: document.getElementById("mt5-test-trade-result"),
  mt5TestTradeJson: document.getElementById("mt5-test-trade-json"),
  mt5StatEnabled: document.getElementById("mt5-stat-enabled"),
  mt5StatMode: document.getElementById("mt5-stat-mode"),
  mt5StatWorkers: document.getElementById("mt5-stat-workers"),
  mt5StatPool: document.getElementById("mt5-stat-pool"),
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
  autoRunSignalAlgorithm: document.getElementById("auto-run-signal-algorithm"),
  backtestSignalAlgorithm: document.getElementById("backtest-signal-algorithm"),
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
  telegramSettingsPersist: document.getElementById("telegram-settings-persist"),
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
let botConfig = null;
let manualTradeImageFile = null;
let symbolSettingsReady = false;
let mt5AccountsState = null;
let mt5RuntimeTimer = null;
let mt5AccountsTimer = null;

function currentPage() {
  const path = window.location.pathname.replace(/\/+$/, "") || "/";
  if (path === "/backtest") return "backtest";
  if (path === "/settings") return "settings";
  if (path === "/mt5-accounts") return "mt5-accounts";
  if (path === "/manual-trade") return "manual-trade";
  if (path === "/live-summary") return "live-summary";
  if (path === "/telegram-signals") return "telegram-signals";
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

function symbolGroupLabel(group) {
  return SYMBOL_GROUPS.find(([key]) => key === group)?.[1] || "Other";
}

function renderGroupedSymbolRow(item) {
  return `
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
  const timeframes = {};
  for (const item of botConfig?.symbols || []) {
    lots[item.symbol] = item.lot_per_leg;
    enabled[item.symbol] = Boolean(item.enabled);
    timeframes[item.symbol] = item.timeframe;
  }
  return { lots, enabled, timeframes };
}

function collectSymbolSettings() {
  const lots = {};
  const enabled = {};
  const timeframes = {};
  const lotInputs = els.symbolsBody.querySelectorAll(".lot-input");
  const enabledInputs = els.symbolsBody.querySelectorAll(".symbol-enabled");
  const timeframeInputs = els.symbolsBody.querySelectorAll(".timeframe-select");

  if (!lotInputs.length && !enabledInputs.length && !timeframeInputs.length) {
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

  for (const input of timeframeInputs) {
    const symbol = input.dataset.symbol;
    if (!symbol || !input.value) {
      throw new Error(`Invalid timeframe for ${symbol || "symbol"}`);
    }
    timeframes[symbol] = input.value;
  }

  if (!Object.keys(lots).length || !Object.keys(enabled).length || !Object.keys(timeframes).length) {
    const fallback = symbolSettingsFromConfig();
    if (!Object.keys(lots).length) Object.assign(lots, fallback.lots);
    if (!Object.keys(enabled).length) Object.assign(enabled, fallback.enabled);
    if (!Object.keys(timeframes).length) Object.assign(timeframes, fallback.timeframes);
  }

  return { lots, enabled, timeframes };
}

function defaultForexLotFromUi() {
  const value = Number(els.defaultForexLot?.value);
  return Number.isFinite(value) && value > 0 ? value : undefined;
}

function appendBrokerSymbolSuffixFromUi() {
  if (!els.appendBrokerSymbolSuffix) return undefined;
  return Boolean(els.appendBrokerSymbolSuffix.checked);
}

function updateBrokerSymbolSuffixHint(configLike = botConfig) {
  if (!els.brokerSymbolSuffixHint) return;
  const suffix = configLike?.mt5?.broker_symbol_suffix || "-VIP";
  const appendTag = configLike?.mt5?.append_broker_symbol_suffix !== false;
  if (appendTag) {
    els.brokerSymbolSuffixHint.textContent =
      `Broker tag on: orders use symbols like BTCUSD${suffix} (or each MT5 account's suffix, e.g. -STD). Telegram auto-register tries suffixed names first.`;
  } else {
    els.brokerSymbolSuffixHint.textContent =
      "Broker tag off: orders use plain symbol names (BTCUSD, EURUSD, …) with no -VIP / -STD suffix.";
  }
}

function formatApiError(detail) {
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail.map((item) => item.msg || JSON.stringify(item)).join("; ");
  }
  return "Request failed";
}

async function syncSymbolSettings({ persist = true, silent = false, rerender = false } = {}) {
  const { lots, enabled, timeframes } = collectSymbolSettings();
  const defaultForexLot = defaultForexLotFromUi();
  const appendBrokerSymbolSuffix = appendBrokerSymbolSuffixFromUi();
  if (
    !Object.keys(lots).length
    && !Object.keys(enabled).length
    && !Object.keys(timeframes).length
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
      timeframes,
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

function renderMt5Accounts(data) {
  mt5AccountsState = data;
  if (els.mt5TradingMode && data.trading_mode) {
    els.mt5TradingMode.value = data.trading_mode;
  }
  if (els.mt5ActiveAccount) {
    const accounts = data.accounts || [];
    const selected = data.active_account_id ? String(data.active_account_id) : "";
    els.mt5ActiveAccount.innerHTML = accounts
      .map(
        (account) =>
          `<option value="${account.id}"${String(account.id) === selected ? " selected" : ""}>${escapeHtml(account.name)} (${account.login})</option>`,
      )
      .join("");
    if (!accounts.length) {
      els.mt5ActiveAccount.innerHTML = '<option value="">No accounts</option>';
    }
  }
  const workers = data.workers || [];
  const workerMap = Object.fromEntries(workers.map((item) => [String(item.account_id), item]));
  const accounts = data.accounts || [];
  const enabledCount = data.enabled_count ?? accounts.filter((item) => item.enabled).length;
  const workersAlive = workers.filter((item) => item.alive).length;
  const sessionMode = data.session_mode === "sequential" ? "Sequential" : "Parallel";
  const modeLabel = data.trading_mode === "single" ? "Single" : "Parallel";
  if (els.mt5AccountsStatus) {
    els.mt5AccountsStatus.textContent =
      `${enabledCount} enabled · ${modeLabel} targets · ${sessionMode} login · pool ${data.pool_active ? "active" : "config fallback"}`;
    if (Array.isArray(data.path_warnings) && data.path_warnings.length) {
      els.mt5AccountsStatus.textContent += ` · WARNING: ${data.path_warnings[0]}`;
      els.mt5AccountsStatus.className = "panel-hint mt5-status-line live-warning";
    } else {
      els.mt5AccountsStatus.className = "panel-hint mt5-status-line";
    }
  }
  if (els.mt5StatEnabled) els.mt5StatEnabled.textContent = String(enabledCount);
  if (els.mt5StatMode) els.mt5StatMode.textContent = modeLabel;
  if (els.mt5StatWorkers) els.mt5StatWorkers.textContent = `${workers.filter((item) => item.connected).length}/${accounts.length || 0}`;
  if (els.mt5StatPool) els.mt5StatPool.textContent = data.pool_active ? "Active" : "Fallback";
  if (!els.mt5AccountsBody) return;
  if (!accounts.length) {
    els.mt5AccountsBody.innerHTML =
      '<tr><td colspan="7" class="empty-row">No MT5 accounts yet. Add one in the form on the left.</td></tr>';
    scheduleResponsiveTables();
    return;
  }
  els.mt5AccountsBody.innerHTML = accounts
    .map((account) => {
      const worker = workerMap[String(account.id)] || {};
      const workerLabel = worker.active
        ? "Active session"
        : worker.connected
          ? "Last login OK"
          : worker.error
            ? `Error: ${worker.error}`
            : worker.alive
              ? "Idle — login on trade"
              : "Idle";
      const workerClass = worker.connected || worker.active ? "badge badge-accent" : worker.error ? "badge badge-muted" : "badge badge-muted";
      const active =
        data.trading_mode === "single" && String(data.active_account_id) === String(account.id)
          ? '<span class="badge badge-accent">Active</span>'
          : "";
      return `
        <tr data-account-id="${account.id}">
          <td>
            <strong>${escapeHtml(account.name)}</strong>
            ${account.is_primary ? '<span class="badge badge-accent">Primary</span>' : ""}
            ${active}
          </td>
          <td class="mono">${account.login}</td>
          <td>${escapeHtml(account.server)}</td>
          <td class="mono">${escapeHtml(account.symbol_suffix || "—")}</td>
          <td>
            <div class="mt5-status-badges">
              <span class="badge ${account.enabled ? "badge-accent" : "badge-muted"}">${account.enabled ? "Enabled" : "Disabled"}</span>
            </div>
          </td>
          <td><span class="${workerClass}">${escapeHtml(workerLabel)}</span></td>
          <td>
            <div class="mt5-action-group">
              <button type="button" class="btn btn-ghost btn-sm mt5-account-use-btn" data-id="${account.id}">Activate</button>
              <button type="button" class="btn btn-ghost btn-sm mt5-account-edit-btn" data-id="${account.id}">Edit</button>
              <button type="button" class="btn btn-ghost btn-sm mt5-account-toggle-btn" data-id="${account.id}" data-enabled="${account.enabled ? "1" : "0"}">${account.enabled ? "Disable" : "Enable"}</button>
              <button type="button" class="btn btn-ghost btn-sm mt5-account-primary-btn" data-id="${account.id}" ${account.is_primary ? "disabled" : ""}>Set primary</button>
              <button type="button" class="btn btn-ghost btn-sm mt5-account-delete-btn" data-id="${account.id}">Delete</button>
            </div>
          </td>
        </tr>
      `;
    })
    .join("");
  scheduleResponsiveTables();
}

function resetMt5AccountForm() {
  els.mt5AccountForm?.reset();
  if (els.mt5AccountEditId) els.mt5AccountEditId.value = "";
  if (els.mt5AccountEnabled) els.mt5AccountEnabled.checked = true;
  if (els.mt5AccountPrimary) els.mt5AccountPrimary.checked = false;
  if (els.mt5AccountPassword) {
    els.mt5AccountPassword.required = true;
    els.mt5AccountPassword.placeholder = "";
  }
  if (els.mt5AccountFormTitle) els.mt5AccountFormTitle.textContent = "Add account";
  if (els.mt5AccountSaveBtn) els.mt5AccountSaveBtn.querySelector(".btn-label").textContent = "Add account";
  els.mt5AccountCancelBtn?.classList.add("hidden");
}

function startEditMt5Account(accountId) {
  const account = (mt5AccountsState?.accounts || []).find((item) => String(item.id) === String(accountId));
  if (!account) {
    toast("Account not found", "error");
    return;
  }
  if (els.mt5AccountEditId) els.mt5AccountEditId.value = String(account.id);
  if (els.mt5AccountName) els.mt5AccountName.value = account.name || "";
  if (els.mt5AccountLogin) els.mt5AccountLogin.value = String(account.login || "");
  if (els.mt5AccountPassword) {
    els.mt5AccountPassword.value = "";
    els.mt5AccountPassword.required = false;
    els.mt5AccountPassword.placeholder = "Leave blank to keep current password";
  }
  if (els.mt5AccountServer) els.mt5AccountServer.value = account.server || "";
  if (els.mt5AccountSuffix) els.mt5AccountSuffix.value = account.symbol_suffix || "";
  if (els.mt5AccountPath) els.mt5AccountPath.value = account.mt5_path || "";
  if (els.mt5AccountEnabled) els.mt5AccountEnabled.checked = Boolean(account.enabled);
  if (els.mt5AccountPrimary) els.mt5AccountPrimary.checked = Boolean(account.is_primary);
  if (els.mt5AccountFormTitle) els.mt5AccountFormTitle.textContent = `Edit ${account.name}`;
  if (els.mt5AccountSaveBtn) els.mt5AccountSaveBtn.querySelector(".btn-label").textContent = "Save changes";
  els.mt5AccountCancelBtn?.classList.remove("hidden");
  els.mt5AccountName?.focus();
  window.scrollTo({ top: 0, behavior: "smooth" });
}

async function loadMt5Accounts() {
  const response = await fetch("/api/mt5-accounts", { cache: "no-store" });
  const data = await response.json();
  if (!response.ok) throw new Error(formatApiError(data.detail) || "Failed to load MT5 accounts");
  renderMt5Accounts(data);
  return data;
}

async function patchMt5Account(accountId, partial, { silent = false, successMessage = "Account updated" } = {}) {
  const response = await fetch(`/api/mt5-accounts/${encodeURIComponent(accountId)}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(partial),
  });
  const data = await response.json();
  if (!response.ok) throw new Error(formatApiError(data.detail) || "Failed to update MT5 account");
  renderMt5Accounts(data);
  if (!silent) toast(successMessage, "success");
  return data;
}

async function saveMt5Account(event) {
  event.preventDefault();
  const login = Number(els.mt5AccountLogin?.value);
  if (!Number.isFinite(login) || login <= 0) {
    toast("Login must be a positive number", "error");
    return;
  }
  const editingId = els.mt5AccountEditId?.value?.trim();
  const payload = {
    name: els.mt5AccountName?.value?.trim(),
    login,
    server: els.mt5AccountServer?.value?.trim(),
    symbol_suffix: els.mt5AccountSuffix?.value?.trim() || "",
    mt5_path: els.mt5AccountPath?.value?.trim() || null,
    enabled: Boolean(els.mt5AccountEnabled?.checked),
    is_primary: Boolean(els.mt5AccountPrimary?.checked),
  };
  const password = els.mt5AccountPassword?.value || "";
  if (password || !editingId) {
    payload.password = password;
  }
  if (!editingId && !password) {
    toast("Password is required for new accounts", "error");
    return;
  }
  setLoading(els.mt5AccountSaveBtn, true);
  try {
    const response = await fetch(
      editingId ? `/api/mt5-accounts/${encodeURIComponent(editingId)}` : "/api/mt5-accounts",
      {
        method: editingId ? "PATCH" : "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      },
    );
    const data = await response.json();
    if (!response.ok) {
      throw new Error(formatApiError(data.detail) || `Failed to ${editingId ? "update" : "add"} MT5 account`);
    }
    resetMt5AccountForm();
    renderMt5Accounts(data);
    toast(
      editingId
        ? `MT5 account updated: ${data.account?.name || payload.name}`
        : `MT5 account added: ${data.account?.name || payload.name}`,
      "success",
    );
  } catch (error) {
    toast(error.message, "error");
  } finally {
    setLoading(els.mt5AccountSaveBtn, false);
  }
}

async function updateMt5Runtime(partial, { silent = false } = {}) {
  const response = await fetch("/api/mt5-accounts/runtime/settings", {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(partial),
  });
  const data = await response.json();
  if (!response.ok) throw new Error(formatApiError(data.detail) || "Failed to update MT5 runtime settings");
  renderMt5Accounts(data);
  if (!silent) toast("MT5 trading mode updated", "success");
  return data;
}

async function deleteMt5Account(accountId, name) {
  const confirmed = window.confirm(`Delete MT5 account "${name}"?`);
  if (!confirmed) return;
  const row = els.mt5AccountsBody?.querySelector(`tr[data-account-id="${CSS.escape(String(accountId))}"]`);
  const button = row?.querySelector(".mt5-account-delete-btn");
  setLoading(button, true, "Deleting...");
  try {
    const response = await fetch(`/api/mt5-accounts/${encodeURIComponent(accountId)}`, { method: "DELETE" });
    const data = await response.json();
    if (!response.ok) throw new Error(formatApiError(data.detail) || "Failed to delete MT5 account");
    renderMt5Accounts(data);
    toast(`MT5 account deleted: ${name}`, "success");
  } catch (error) {
    toast(error.message, "error");
  } finally {
    setLoading(button, false);
  }
}

async function reloadMt5Workers() {
  setLoading(els.mt5AccountsReloadBtn, true);
  try {
    const response = await fetch("/api/mt5-accounts/reload", { method: "POST" });
    const data = await response.json();
    if (!response.ok) throw new Error(formatApiError(data.detail) || "Failed to reload MT5 workers");
    renderMt5Accounts(data);
    toast("MT5 workers reloaded", "success");
  } catch (error) {
    toast(error.message, "error");
  } finally {
    setLoading(els.mt5AccountsReloadBtn, false);
  }
}

function renderMt5TestTradeResult(data) {
  if (!els.mt5TestTradeResult || !els.mt5TestTradeJson) return;
  els.mt5TestTradeJson.textContent = JSON.stringify(data, null, 2);
  els.mt5TestTradeResult.classList.remove("hidden");
}

async function placeMt5TestTrade() {
  const targetCount = (mt5AccountsState?.accounts || []).filter((item) => item.enabled).length;
  if (!targetCount) {
    toast("No enabled MT5 accounts configured", "error");
    return;
  }
  const live = botConfig && !botConfig.bot.dry_run;
  const confirmed = window.confirm(
    live
      ? `Place LIVE XAUUSD 0.01 BUY test trade on ${targetCount} enabled account${targetCount === 1 ? "" : "s"} (sequential login)? No SL/TP — close manually in MT5.`
      : `Place paper XAUUSD 0.01 BUY test trade on ${targetCount} enabled account${targetCount === 1 ? "" : "s"}?`,
  );
  if (!confirmed) return;

  setLoading(els.mt5TestTradeBtn, true);
  try {
    const response = await fetch("/api/mt5-accounts/test-trade", {
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
    renderMt5Accounts(data);
    renderMt5TestTradeResult(data);
    const placedCount = (data.account_results || []).filter((item) => item.status === "placed" || item.status === "paper").length;
    const failedCount = (data.account_results || []).filter((item) => item.status === "failed").length;
    if (data.status === "placed" || data.status === "paper") {
      toast(`Test trade ${data.status} on ${placedCount}/${targetCount} account(s)`, "success");
    } else {
      toast(data.reason || `Test trade failed (${failedCount}/${targetCount})`, "error");
    }
    await refreshLogs();
  } catch (error) {
    toast(error.message, "error");
  } finally {
    setLoading(els.mt5TestTradeBtn, false);
  }
}

function scheduleMt5RuntimeSave(partial) {
  if (mt5RuntimeTimer) clearTimeout(mt5RuntimeTimer);
  mt5RuntimeTimer = setTimeout(() => {
    updateMt5Runtime(partial, { silent: true }).catch((error) => toast(error.message, "error"));
  }, 350);
}

function startMt5AccountsPolling() {
  if (mt5AccountsTimer) clearInterval(mt5AccountsTimer);
  mt5AccountsTimer = setInterval(() => {
    if (currentPage() !== "mt5-accounts") return;
    loadMt5Accounts().catch(() => {});
  }, 8000);
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

function renderAutoRunStatus(status) {
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
  } else if (status.daily_risk?.enabled && status.daily_risk?.halted) {
    els.autoRunHint.textContent = `Daily loss guard active: loss ${formatMoney(status.daily_risk.loss)} reached limit ${formatMoney(status.daily_risk.loss_limit)}. New trades are blocked until the next UTC day.`;
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
}

async function refreshAutoRunStatus(includeMt5 = false) {
  try {
    const query = includeMt5 ? "?include_mt5=true" : "";
    const response = await fetch(`/api/auto-run/status${query}`, { cache: "no-store" });
    if (!response.ok) throw new Error("Failed to load auto-run status");
    renderAutoRunStatus(await response.json());
  } catch (error) {
    toast(error.message, "error");
  }
}

async function saveBotStrategy({ strategy, persist, silent = false } = {}) {
  if (!els.autoRunStrategy) return null;
  const selected = canonicalStrategy(strategy ?? selectedStrategy());
  const saveToConfig = persist ?? Boolean(els.autoRunSaveStrategy?.checked);
  setLoading(els.autoRunSaveBtn, true);
  try {
    const response = await fetch("/api/bot/settings", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        strategy: selected,
        signal_algorithm: els.autoRunSignalAlgorithm?.value || botConfig?.bot?.signal_algorithm,
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
    if (data.auto_run) renderAutoRunStatus(data.auto_run);
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
  loopTimer = setInterval(() => refreshAutoRunStatus(false), 5000);
}

function telegramStatusClass(status) {
  const value = String(status || "").toLowerCase();
  if (value === "placed" || value === "paper" || value === "breakeven") return "value-positive";
  if (value === "failed" || value === "error" || value.includes("fail")) return "value-negative";
  if (value === "skipped" || value === "stale") return "value-neutral";
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
      const detail = accountSummary || item.reason || item.result?.reason || "";
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

  const signal = status.last_signal;
  if (els.telegramLastParsed) {
    els.telegramLastParsed.textContent = signal?.action && signal.action !== "none"
      ? `${String(signal.action).toUpperCase()} ${signal.symbol || ""}`
      : "—";
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
      els.telegramLastActionJson.textContent = JSON.stringify(
        {
          signal: action.signal || status.last_signal || null,
          result: action.result,
        },
        null,
        2,
      );
      els.telegramLastAction.classList.remove("hidden");
    } else if (status.last_result) {
      if (els.telegramLastActionMeta) {
        els.telegramLastActionMeta.textContent = status.last_channel
          ? `${status.last_channel} · ${formatTimestamp(status.last_action_at)}`
          : formatTimestamp(status.last_action_at);
      }
      renderTelegramActionStatusBadge(els.telegramLastActionStatus, status.last_result);
      els.telegramLastActionJson.textContent = JSON.stringify(status.last_result, null, 2);
      els.telegramLastAction.classList.remove("hidden");
    } else {
      els.telegramLastAction.classList.add("hidden");
      els.telegramLastActionJson.textContent = "";
      if (els.telegramLastActionMeta) els.telegramLastActionMeta.textContent = "";
      els.telegramLastActionStatus?.classList.add("hidden");
    }
  }
  renderTelegramActionLog(status.recent_actions || []);
  if (els.telegramLastResult && els.telegramLastResultJson) {
    if (status.last_signal) {
      els.telegramLastResultJson.textContent = JSON.stringify(status.last_signal, null, 2);
      els.telegramLastResult.classList.remove("hidden");
    } else {
      els.telegramLastResult.classList.add("hidden");
      els.telegramLastResultJson.textContent = "";
    }
  }
  if (els.telegramLlm && (status.openai_model || status.gemini_model)) {
    els.telegramLlm.textContent = formatSignalParserLabel({
      openai_api_key_configured: status.openai_api_key_configured,
      openai_model: status.openai_model,
      gemini_api_key_configured: status.gemini_api_key_configured,
      gemini_model: status.gemini_model,
    });
  }
  if (els.telegramIgnoreOpen && status.ignore_open_symbol_trades != null) {
    els.telegramIgnoreOpen.checked = Boolean(status.ignore_open_symbol_trades);
  }
  if (els.telegramOpenGuard) {
    els.telegramOpenGuard.textContent = status.ignore_open_symbol_trades ? "On" : "Off";
  }
  renderTelegramMessages(status.recent_messages || [], status.channels || botConfig?.telegram_signals?.channels || []);
  renderTelegramChannels(status.channels || botConfig?.telegram_signals?.channels || []);
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
  const persist = Boolean(els.telegramSettingsPersist?.checked);
  try {
    const response = await fetch("/api/telegram-signals/settings", {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        ignore_open_symbol_trades: Boolean(els.telegramIgnoreOpen.checked),
        persist,
      }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || "Failed to save Telegram settings");
    if (botConfig?.telegram_signals) {
      botConfig.telegram_signals.ignore_open_symbol_trades = Boolean(data.ignore_open_symbol_trades);
    }
    if (els.telegramOpenGuard) {
      els.telegramOpenGuard.textContent = data.ignore_open_symbol_trades ? "On" : "Off";
    }
    if (!silent) {
      toast(persist ? "Telegram settings saved" : "Telegram settings applied", "success");
    }
    return data;
  } catch (error) {
    if (!silent) toast(error.message, "error");
    throw error;
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
    if (Array.isArray(parsed.tps) && parsed.tps.length) parts.push(`tps=[${parsed.tps.join(", ")}]`);
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
  return `
    <div class="telegram-msg-cell is-collapsed" data-expand-field="${escapeHtml(field)}" data-expand-key="${escapeHtml(rowKey)}">${escapeHtml(cleaned)}</div>
    <button type="button" class="telegram-expand-btn" data-expand-field="${escapeHtml(field)}" data-expand-key="${escapeHtml(rowKey)}">See more</button>
  `;
}

function renderTelegramActionJsonCell(item, rowKey) {
  const payload = telegramActionPayload(item);
  const json = JSON.stringify(payload, null, 2);
  if (!json || json === "{}") {
    return `<span class="value-neutral">${escapeHtml(formatLlmResponse(item))}</span>`;
  }
  const preview = json.length > 160 ? `${json.slice(0, 160)}…` : json;
  return `
    <div class="telegram-json-preview is-collapsed" data-expand-field="json" data-expand-key="${escapeHtml(rowKey)}">${escapeHtml(preview)}</div>
    <button type="button" class="telegram-expand-btn" data-expand-field="json" data-expand-key="${escapeHtml(rowKey)}">See JSON</button>
    <pre class="telegram-json-full hidden" data-expand-target="json" data-expand-key="${escapeHtml(rowKey)}">${escapeHtml(json)}</pre>
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
  const messageId = escapeHtml(String(item.message_id || ""));
  const actionCell = hardCopyEnabled
    ? `<button type="button" class="btn btn-primary btn-sm telegram-hard-copy-btn" data-message-id="${messageId}" title="Force place at market; only checks TPs vs live price">Hard copy</button>`
    : '<span class="value-neutral">—</span>';
  const messageCell = renderTelegramExpandableText(telegramMessageText(item), rowKey, "message");
  return `
    <tr data-message-row="${escapeHtml(rowKey)}">
      <td class="${statusClass}">${escapeHtml(status)}</td>
      <td>${replyLabel}</td>
      <td>${formatTimestamp(item.updated_at)}</td>
      <td>${messageCell}</td>
      <td>${renderTelegramActionJsonCell(item, rowKey)}</td>
      <td>${escapeHtml(String(item.reason || item.result?.reason || "—"))}</td>
      <td class="table-actions">${actionCell}</td>
    </tr>
  `;
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
  const row = button.closest("tr");
  if (!row) return;

  if (field === "message") {
    const cell = row.querySelector(`.telegram-msg-cell[data-expand-key="${CSS.escape(key)}"]`);
    if (!cell) return;
    const collapsed = cell.classList.toggle("is-collapsed");
    button.textContent = collapsed ? "See more" : "See less";
    return;
  }

  if (field === "json") {
    const preview = row.querySelector(`.telegram-json-preview[data-expand-key="${CSS.escape(key)}"]`);
    const full = row.querySelector(`.telegram-json-full[data-expand-key="${CSS.escape(key)}"]`);
    if (!preview || !full) return;
    const hidden = full.classList.toggle("hidden");
    preview.classList.toggle("is-collapsed", hidden);
    preview.classList.toggle("hidden", !hidden);
    button.textContent = hidden ? "See JSON" : "Hide JSON";
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
  if (els.telegramChannels) {
    els.telegramChannels.textContent = `${(telegram.channels || []).filter((channel) => channel.enabled).length} active / ${(telegram.channels || []).length} total`;
  }
  renderTelegramChannels(telegram.channels || []);
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

async function hardCopyTelegramMessage(messageId, button) {
  if (!messageId) return;
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
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || "Hard copy failed");
    renderTelegramStatus(data);
    const status = data.status || data.result?.status || "unknown";
    const accountSummary = formatTelegramAccountResults(data.account_results || data.result?.account_results);
    if (status === "placed" || status === "paper") {
      const legs = data.legs || data.tickets?.length || 1;
      const base = `Hard copy ${status}: ${data.symbol || ""} ${String(data.action || "").toUpperCase()} (${legs} leg${legs === 1 ? "" : "s"})`.trim();
      toast(accountSummary ? `${base} · ${accountSummary}` : base, "success");
    } else {
      toast(accountSummary || data.reason || `Hard copy ${status}`, status === "failed" ? "error" : "info");
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
    renderTelegramStatus(data);
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

  if (els.defaultForexLot && config.risk?.default_forex_lot != null) {
    els.defaultForexLot.value = config.risk.default_forex_lot;
  }
  if (els.appendBrokerSymbolSuffix) {
    els.appendBrokerSymbolSuffix.checked = config.mt5?.append_broker_symbol_suffix !== false;
  }
  updateBrokerSymbolSuffixHint(config);

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
    return;
  }
  if (page === "mt5-accounts") {
    await loadMt5Accounts();
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
  } else {
    botConfig = {
      symbols: data.symbols || [],
      symbol_stats: data.symbol_stats || null,
      risk: { default_forex_lot: data.default_forex_lot },
      timeframe_options: data.timeframe_options || [],
      mt5: {
        broker_symbol_suffix: data.broker_symbol_suffix || "-VIP",
        append_broker_symbol_suffix: data.append_broker_symbol_suffix !== false,
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
    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.detail || "Manual trade failed");
    }
    els.manualTradeStatus.textContent = JSON.stringify(data, null, 2);
    els.manualTradeResult.classList.remove("hidden");
    const placed = data.tickets?.length || 0;
    const failed = data.failed?.length || 0;
    toast(`Manual trade sent: ${placed} placed, ${failed} failed`, failed ? "error" : "success");
    if (els.manualTradeText) delete els.manualTradeText.dataset.aiParsed;
    await refreshLiveData();
    await refreshLogs();
  } catch (error) {
    toast(error.message, "error");
  } finally {
    setLoading(els.manualTradeBtn, false);
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
  initManualTradeImageInput();
  els.liveSummaryForm?.addEventListener("submit", loadLiveSummary);
  els.resetLotsBtn?.addEventListener("click", resetLots);
  els.resetTimeframesBtn?.addEventListener("click", resetTimeframes);
  els.optimizeTimeframesBtn?.addEventListener("click", optimizeTimeframes);
  els.saveLotsBtn?.addEventListener("click", saveLots);
  els.snapshotForm?.addEventListener("submit", saveSnapshot);
  els.mt5AccountForm?.addEventListener("submit", saveMt5Account);
  els.mt5AccountCancelBtn?.addEventListener("click", resetMt5AccountForm);
  els.mt5AccountsReloadBtn?.addEventListener("click", reloadMt5Workers);
  els.mt5TestTradeBtn?.addEventListener("click", placeMt5TestTrade);
  els.mt5TradingMode?.addEventListener("change", () => {
    scheduleMt5RuntimeSave({ trading_mode: els.mt5TradingMode.value });
  });
  els.mt5ActiveAccount?.addEventListener("change", () => {
    const value = els.mt5ActiveAccount.value;
    scheduleMt5RuntimeSave({
      active_account_id: value ? Number(value) : null,
      trading_mode: "single",
    });
    if (els.mt5TradingMode) els.mt5TradingMode.value = "single";
  });
  els.mt5AccountsBody?.addEventListener("click", (event) => {
    const useBtn = event.target.closest(".mt5-account-use-btn");
    if (useBtn) {
      const accountId = Number(useBtn.dataset.id);
      if (els.mt5ActiveAccount) els.mt5ActiveAccount.value = String(accountId);
      if (els.mt5TradingMode) els.mt5TradingMode.value = "single";
      updateMt5Runtime({ trading_mode: "single", active_account_id: accountId }).catch((error) =>
        toast(error.message, "error"),
      );
      return;
    }
    const editBtn = event.target.closest(".mt5-account-edit-btn");
    if (editBtn) {
      startEditMt5Account(Number(editBtn.dataset.id));
      return;
    }
    const toggleBtn = event.target.closest(".mt5-account-toggle-btn");
    if (toggleBtn) {
      const accountId = Number(toggleBtn.dataset.id);
      const enabled = toggleBtn.dataset.enabled !== "1";
      patchMt5Account(accountId, { enabled }, { successMessage: enabled ? "Account enabled" : "Account disabled" }).catch(
        (error) => toast(error.message, "error"),
      );
      return;
    }
    const primaryBtn = event.target.closest(".mt5-account-primary-btn");
    if (primaryBtn) {
      patchMt5Account(Number(primaryBtn.dataset.id), { is_primary: true }, { successMessage: "Primary account updated" }).catch(
        (error) => toast(error.message, "error"),
      );
      return;
    }
    const deleteBtn = event.target.closest(".mt5-account-delete-btn");
    if (deleteBtn) {
      const row = deleteBtn.closest("tr");
      const name = row?.querySelector("strong")?.textContent?.trim() || "account";
      deleteMt5Account(Number(deleteBtn.dataset.id), name);
    }
  });
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
    if (!event.target.matches(".lot-input, .symbol-enabled, .timeframe-select")) return;
    const row = event.target.closest("tr");
    if (row && event.target.matches(".symbol-enabled")) {
      row.classList.toggle("row-disabled", !event.target.checked);
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
  els.autoRunStartBtn?.addEventListener("click", startAutoRun);
  els.autoRunStopBtn?.addEventListener("click", stopAutoRun);
  els.autoRunSaveBtn?.addEventListener("click", () => saveBotStrategy({ silent: false, persist: true }));
  els.autoRunStrategy?.addEventListener("change", () => onBotSettingsChanged());
  els.autoRunSignalAlgorithm?.addEventListener("change", () => onBotSettingsChanged());
  els.telegramStartBtn?.addEventListener("click", startTelegramSignals);
  els.telegramStopBtn?.addEventListener("click", stopTelegramSignals);
  els.telegramClearBtn?.addEventListener("click", clearTelegramMessages);
  els.telegramChannelForm?.addEventListener("submit", addTelegramChannel);
  els.telegramIgnoreOpen?.addEventListener("change", () => {
    saveTelegramSettings({ silent: false }).catch(() => {});
  });
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
    void refreshAutoRunStatus(true);
    void refreshLiveData();
  } else if (page === "telegram-signals") {
    startTelegramPolling();
    void refreshTelegramStatus();
  } else if (page === "mt5-accounts") {
    startMt5AccountsPolling();
    void loadMt5Accounts();
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

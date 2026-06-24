(() => {
  const SPEEDS = [1, 2, 5, 10, 20, 50];
  const TIMEFRAME_MS = { M1: 900, M2: 850, M3: 800, M4: 750, M5: 650, M6: 620, M10: 560, M12: 540, M15: 500, M20: 460, M30: 400, H1: 350 };
  const WINDOW_BARS = 90;

  let chart = null;
  let series = null;
  let priceLines = [];
  let payload = null;
  let cursor = -1;
  let playing = false;
  let playTimer = null;
  let speed = 10;
  let shownEvents = new Set();
  let activeEventId = null;
  let lastRenderedCursor = -1;
  let symbolConfigBySymbol = new Map();
  let timeframeOptions = ["M1", "M5", "M15", "M30", "H1"].map((value) => ({ value, label: value }));

  const els = {};

  function q(id) {
    return document.getElementById(id);
  }

  function bindElements() {
    els.form = q("chart-preview-form");
    els.symbol = q("chart-symbol");
    els.timeframe = q("chart-timeframe");
    els.start = q("chart-start");
    els.end = q("chart-end");
    els.strategy = q("chart-strategy");
    els.runBtn = q("chart-preview-btn");
    els.wrap = q("chart-preview-wrap");
    els.container = q("chart-container");
    els.summary = q("chart-preview-summary");
    els.playBtn = q("chart-play-btn");
    els.pauseBtn = q("chart-pause-btn");
    els.resetBtn = q("chart-reset-btn");
    els.liveBadge = q("chart-live-badge");
    els.autoplay = q("chart-autoplay");
    els.speed = q("chart-speed");
    els.scrub = q("chart-scrub");
    els.timeLabel = q("chart-time-label");
    els.eventLog = q("chart-event-log");
    els.tradeDetail = q("chart-trade-detail");
  }

  function destroyChart() {
    stopPlayback();
    priceLines = [];
    shownEvents = new Set();
    activeEventId = null;
    lastRenderedCursor = -1;
    if (chart) {
      chart.remove();
      chart = null;
      series = null;
    }
  }

  function createChart() {
    destroyChart();
    chart = LightweightCharts.createChart(els.container, {
      layout: {
        background: { color: "#0f1419" },
        textColor: "#94a3b8",
      },
      grid: {
        vertLines: { color: "#1e293b" },
        horzLines: { color: "#1e293b" },
      },
      crosshair: { mode: LightweightCharts.CrosshairMode.Normal },
      rightPriceScale: { borderColor: "#334155" },
      timeScale: {
        borderColor: "#334155",
        timeVisible: true,
        secondsVisible: false,
        rightOffset: 8,
      },
      width: els.container.clientWidth,
      height: 420,
    });

    series = chart.addCandlestickSeries({
      upColor: "#22d3a5",
      downColor: "#f87171",
      borderUpColor: "#22d3a5",
      borderDownColor: "#f87171",
      wickUpColor: "#22d3a5",
      wickDownColor: "#f87171",
    });

    const ro = new ResizeObserver(() => {
      if (chart && els.container) {
        chart.applyOptions({ width: els.container.clientWidth });
      }
    });
    ro.observe(els.container);
  }

  function clearPriceLines() {
    if (!series) return;
    for (const line of priceLines) {
      series.removePriceLine(line);
    }
    priceLines = [];
  }

  function addPriceLine(price, color, title) {
    if (!series) return;
    const line = series.createPriceLine({
      price,
      color,
      lineWidth: 1,
      lineStyle: 2,
      axisLabelVisible: true,
      title,
    });
    priceLines.push(line);
  }

  function formatTs(unix) {
    if (!unix) return "—";
    return new Date(unix * 1000).toLocaleString();
  }

  function formatPrice(value) {
    if (value == null || Number.isNaN(Number(value))) return "—";
    const n = Number(value);
    if (Math.abs(n) >= 1000) return n.toFixed(2);
    if (Math.abs(n) >= 10) return n.toFixed(3);
    if (Math.abs(n) >= 1) return n.toFixed(4);
    return n.toFixed(5);
  }

  function formatMoney(value) {
    const n = Number(value);
    if (!Number.isFinite(n)) return "—";
    const sign = n > 0 ? "+" : "";
    return `${sign}$${n.toFixed(2)}`;
  }

  function pnlClass(value) {
    const n = Number(value);
    if (n > 0) return "value-positive";
    if (n < 0) return "value-negative";
    return "value-neutral";
  }

  function escapeHtml(value) {
    return String(value)
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;");
  }

  function localInputToIso(value) {
    if (!value) return "";
    return `${value}:00+00:00`;
  }

  function isoToLocalInput(iso) {
    const date = new Date(iso);
    const pad = (n) => String(n).padStart(2, "0");
    return `${date.getUTCFullYear()}-${pad(date.getUTCMonth() + 1)}-${pad(date.getUTCDate())}T${pad(date.getUTCHours())}:${pad(date.getUTCMinutes())}`;
  }

  function playbackIntervalMs() {
    const tf = payload?.timeframe || "M5";
    const base = TIMEFRAME_MS[tf] || 500;
    return Math.max(20, base / speed);
  }

  function setLiveState(on) {
    els.liveBadge?.classList.toggle("hidden", !on);
    els.liveBadge?.classList.toggle("badge-running", on);
    els.container?.classList.toggle("chart-live", on);
  }

  function buildMarkers(upToTime) {
    if (!payload) return [];
    const markers = [];
    for (const event of payload.events) {
      if (event.bar_time > upToTime) continue;
      if (event.type === "trade") {
        markers.push({
          time: event.bar_time,
          position: event.side === "buy" ? "belowBar" : "aboveBar",
          color: event.side === "buy" ? "#22d3a5" : "#f87171",
          shape: event.side === "buy" ? "arrowUp" : "arrowDown",
          text: `${event.side.toUpperCase()} ${formatMoney(event.pnl)}`,
        });
        if (event.exit_time && event.exit_time <= upToTime) {
          markers.push({
            time: event.exit_time,
            position: "inBar",
            color: event.pnl >= 0 ? "#4ade80" : "#fb7185",
            shape: "circle",
            text: event.exit_kind ? event.exit_kind.toUpperCase() : "EXIT",
          });
        }
      } else {
        markers.push({
          time: event.bar_time,
          position: "inBar",
          color: "#64748b",
          shape: "square",
          text: "SKIP",
        });
      }
    }
    markers.sort((a, b) => a.time - b.time);
    return markers;
  }

  function renderTradeDetail(event) {
    if (!event) {
      els.tradeDetail.innerHTML = '<p class="chart-detail-empty">Press Live replay — candles and trades appear bar by bar like real time.</p>';
      return;
    }
    const tps = (event.tps || []).map((tp) => formatPrice(tp)).join(" · ");
    els.tradeDetail.innerHTML = `
      <div class="chart-detail-grid">
        <div><span class="label">Type</span><strong>${escapeHtml(event.type)}</strong></div>
        <div><span class="label">Side</span><strong class="side-${event.side}">${escapeHtml(String(event.side).toUpperCase())}</strong></div>
        <div><span class="label">Entry</span><strong>${formatPrice(event.entry)}</strong></div>
        <div><span class="label">SL</span><strong>${formatPrice(event.sl)}</strong></div>
        <div><span class="label">TPs</span><strong>${tps || "—"}</strong></div>
        <div><span class="label">PnL</span><strong class="${pnlClass(event.pnl)}">${formatMoney(event.pnl)}</strong></div>
        <div><span class="label">Signal time</span><strong>${formatTs(event.bar_time)}</strong></div>
        <div><span class="label">Exit</span><strong>${event.exit_kind ? escapeHtml(event.exit_kind.toUpperCase()) : "—"} ${event.exit_time ? `@ ${formatTs(event.exit_time)}` : ""}</strong></div>
        <div class="chart-detail-wide"><span class="label">Reason</span><strong>${escapeHtml(event.reason || "—")}</strong></div>
      </div>
    `;
  }

  function appendEventLog(event) {
    const row = document.createElement("div");
    row.className = `chart-event-row chart-event-${event.type}`;
    row.dataset.eventId = String(event.id);
    row.innerHTML = `
      <span class="chart-event-time">${formatTs(event.bar_time)}</span>
      <span class="chart-event-type">${event.type === "trade" ? event.side.toUpperCase() : "SKIP"}</span>
      <span class="chart-event-msg">${escapeHtml(event.type === "trade" ? `entry ${formatPrice(event.entry)} · ${formatMoney(event.pnl)}` : event.reason)}</span>
    `;
    row.addEventListener("click", () => {
      activeEventId = event.id;
      focusEvent(event);
      renderTradeDetail(event);
    });
    els.eventLog.appendChild(row);
    row.scrollIntoView({ block: "nearest", behavior: "smooth" });
  }

  function focusEvent(event) {
    if (!chart || !payload) return;
    clearPriceLines();
    if (event.type === "trade") {
      addPriceLine(event.entry, "#38bdf8", "Entry");
      addPriceLine(event.sl, "#f87171", "SL");
      (event.tps || []).forEach((tp, index) => addPriceLine(tp, "#22d3a5", `TP${index + 1}`));
    }
    const idx = payload.candles.findIndex((c) => c.time >= event.bar_time);
    if (idx >= 0) {
      chart.timeScale().setVisibleLogicalRange({ from: Math.max(0, idx - 40), to: idx + 20 });
    }
    renderTradeDetail(event);
  }

  function syncEvents(upToTime) {
    for (const event of payload.events) {
      if (event.bar_time <= upToTime && !shownEvents.has(event.id)) {
        shownEvents.add(event.id);
        appendEventLog(event);
        if (event.type === "trade") {
          activeEventId = event.id;
          clearPriceLines();
          addPriceLine(event.entry, "#38bdf8", "Entry");
          addPriceLine(event.sl, "#f87171", "SL");
          (event.tps || []).forEach((tp, index) => addPriceLine(tp, "#22d3a5", `TP${index + 1}`));
          renderTradeDetail(event);
        }
      }
    }
  }

  function scrollToCursor() {
    if (!chart || !payload) return;
    const from = Math.max(0, cursor - WINDOW_BARS + 15);
    const to = cursor + 15;
    chart.timeScale().setVisibleLogicalRange({ from, to });
  }

  function renderCandles(forceFull = false) {
    if (!payload || !series) return;
    const candles = payload.candles;
    if (!candles.length || cursor < 0) {
      series.setData([]);
      series.setMarkers([]);
      return;
    }

    if (forceFull || cursor < lastRenderedCursor || !playing) {
      series.setData(candles.slice(0, cursor + 1));
      lastRenderedCursor = cursor;
    } else if (cursor === lastRenderedCursor + 1) {
      series.update(candles[cursor]);
      lastRenderedCursor = cursor;
      els.container?.classList.add("chart-tick");
      setTimeout(() => els.container?.classList.remove("chart-tick"), 120);
    } else {
      series.setData(candles.slice(0, cursor + 1));
      lastRenderedCursor = cursor;
    }

    const upToTime = candles[cursor].time;
    series.setMarkers(buildMarkers(upToTime));
    scrollToCursor();
  }

  function updateFrame(forceFull = false) {
    if (!payload || !series) return;
    const candles = payload.candles;
    if (!candles.length) return;

    cursor = Math.max(-1, Math.min(cursor, candles.length - 1));
    if (cursor < 0) {
      els.scrub.max = String(candles.length - 1);
      els.scrub.value = "0";
      els.timeLabel.textContent = "Ready — press Live replay";
      series.setData([]);
      series.setMarkers([]);
      return;
    }

    renderCandles(forceFull);

    const upToTime = candles[cursor].time;
    els.scrub.max = String(candles.length - 1);
    els.scrub.value = String(cursor);
    els.timeLabel.textContent = `${formatTs(upToTime)} · bar ${cursor + 1}/${candles.length}`;
    syncEvents(upToTime);
  }

  function stopPlayback() {
    playing = false;
    setLiveState(false);
    if (playTimer) {
      clearInterval(playTimer);
      playTimer = null;
    }
    els.playBtn.disabled = false;
    els.pauseBtn.disabled = true;
  }

  function startPlayback() {
    if (!payload || !payload.candles.length) return;
    if (cursor >= payload.candles.length - 1) {
      resetPlayback();
    }
    stopPlayback();
    playing = true;
    setLiveState(true);
    els.playBtn.disabled = true;
    els.pauseBtn.disabled = false;

    if (cursor < 0) {
      cursor = 0;
      updateFrame(true);
    }

    playTimer = setInterval(() => {
      if (cursor >= payload.candles.length - 1) {
        stopPlayback();
        return;
      }
      cursor += 1;
      updateFrame(false);
    }, playbackIntervalMs());
  }

  function resetPlayback() {
    stopPlayback();
    cursor = -1;
    lastRenderedCursor = -1;
    shownEvents = new Set();
    activeEventId = null;
    els.eventLog.innerHTML = "";
    clearPriceLines();
    renderTradeDetail(null);
    updateFrame(true);
  }

  function prepareReplay(autoplay = true) {
    resetPlayback();
    if (autoplay && payload?.candles?.length) {
      setTimeout(() => startPlayback(), 350);
    }
  }

  function renderSummary(data) {
    const s = data.summary;
    const timeframeNote = data.settings_timeframe_match
      ? data.timeframe
      : `${data.timeframe} (configured ${data.configured_timeframe})`;
    els.summary.innerHTML = `
      <div class="summary-card"><span class="label">Symbol</span><span class="value">${escapeHtml(data.symbol)} · ${escapeHtml(timeframeNote)}</span></div>
      <div class="summary-card"><span class="label">Bars</span><span class="value">${s.bars}</span></div>
      <div class="summary-card"><span class="label">Trades</span><span class="value">${s.trades} <small>(${s.skipped} skipped)</small></span></div>
      <div class="summary-card"><span class="label">PnL</span><span class="value ${pnlClass(s.pnl)}">${formatMoney(s.pnl)}</span></div>
    `;
    els.summary.classList.remove("hidden");
  }

  async function runChartPreview(event) {
    event.preventDefault();
    const symbol = els.symbol.value;
    const timeframe = els.timeframe.value;
    const start = localInputToIso(els.start.value);
    const end = localInputToIso(els.end.value);

    els.runBtn.disabled = true;
    const label = els.runBtn.querySelector(".btn-label");
    if (label) label.textContent = "Loading chart…";

    try {
      const url = `/api/backtest/chart?symbol=${encodeURIComponent(symbol)}&timeframe=${encodeURIComponent(timeframe)}&start=${encodeURIComponent(start)}&end=${encodeURIComponent(end)}`;
      const response = await fetch(url);
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Chart backtest failed");

      payload = data;
      els.wrap.classList.remove("hidden");
      renderSummary(data);
      createChart();
      prepareReplay(Boolean(els.autoplay?.checked));
    } catch (error) {
      window.dispatchEvent(new CustomEvent("app:toast", { detail: { message: error.message, type: "error" } }));
    } finally {
      els.runBtn.disabled = false;
      if (label) label.textContent = "Load chart replay";
    }
  }

  function populateSymbols(symbols) {
    if (!els.symbol) return;
    const items = symbols || [];
    symbolConfigBySymbol = new Map(items.map((item) => [item.symbol, item]));
    els.symbol.innerHTML = items
      .map((item) => `<option value="${escapeHtml(item.symbol)}">${escapeHtml(item.symbol)} · ${escapeHtml(item.name)}</option>`)
      .join("");
  }

  function setConfiguredTimeframe() {
    if (!els.symbol || !els.timeframe) return;
    const cfg = symbolConfigBySymbol.get(els.symbol.value);
    const available = timeframeOptions.map((item) => item.value);
    if (cfg?.timeframe && available.includes(cfg.timeframe)) {
      els.timeframe.value = cfg.timeframe;
    }
  }

  function initChartPreview(config) {
    bindElements();
    if (!els.form) return;

    timeframeOptions = (config.timeframe_options && config.timeframe_options.length)
      ? config.timeframe_options
      : timeframeOptions;
    if (els.timeframe) {
      els.timeframe.innerHTML = timeframeOptions
        .map((tf) => `<option value="${escapeHtml(tf.value)}">${escapeHtml(tf.label || tf.value)}</option>`)
        .join("");
    }
    populateSymbols(config.symbols || []);
    setConfiguredTimeframe();
    if (config.defaults) {
      if (els.start && config.defaults.backtest_start) {
        els.start.value = isoToLocalInput(config.defaults.backtest_start);
      }
      if (els.end && config.defaults.backtest_end) {
        els.end.value = isoToLocalInput(config.defaults.backtest_end);
      }
    }
    if (config.bot?.strategy && els.strategy) {
      els.strategy.value = config.bot.strategy;
      els.strategy.disabled = true;
      els.strategy.title = "Chart replay uses the same shared bot strategy as live trading.";
    }

    els.form.addEventListener("submit", runChartPreview);
    els.playBtn?.addEventListener("click", startPlayback);
    els.pauseBtn?.addEventListener("click", stopPlayback);
    els.resetBtn?.addEventListener("click", resetPlayback);
    els.speed?.addEventListener("change", () => {
      speed = Number(els.speed.value) || 10;
      if (playing) {
        stopPlayback();
        startPlayback();
      }
    });
    els.scrub?.addEventListener("input", () => {
      stopPlayback();
      cursor = Number(els.scrub.value) || 0;
      lastRenderedCursor = -1;
      shownEvents = new Set();
      activeEventId = null;
      els.eventLog.innerHTML = "";
      clearPriceLines();
      updateFrame(true);
    });

    els.symbol?.addEventListener("change", setConfiguredTimeframe);
    if (els.speed) {
      els.speed.innerHTML = SPEEDS.map((v) => `<option value="${v}">${v}x</option>`).join("");
      els.speed.value = "10";
      speed = 10;
    }
  }

  window.ChartPreview = { initChartPreview, populateSymbols };
})();

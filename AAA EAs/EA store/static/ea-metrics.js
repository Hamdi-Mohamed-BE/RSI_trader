// Rolling Sharpe trend + win/loss streak distribution for an EA detail page.
// Data: /api/evidence/{slug}/risk-series?mode=&period= (same daily Sharpe definition as the headline figure).
(() => {
  const root = document.querySelector('[data-risk-visuals]');
  if (!root) return;
  const NS = 'http://www.w3.org/2000/svg';
  const WIN = '#0ea371';  // win/loss pair validated on #0b1715 (dataviz validator: all checks pass)
  const LOSS = '#f0443c';
  const LINE = '#7ef7c7';
  const INK = '#789089';
  const GRID = 'rgba(255,255,255,.07)';
  const svgEl = (name, attrs = {}, text) => {
    const node = document.createElementNS(NS, name);
    Object.entries(attrs).forEach(([k, v]) => node.setAttribute(k, v));
    if (text != null) node.textContent = text;
    return node;
  };
  const fmt = (v, d = 2) => (v == null || !Number.isFinite(v) ? '—' : v.toFixed(d));
  const monthLabel = (iso) => new Date(`${iso}T00:00:00Z`).toLocaleDateString('en-GB', { month: 'short', year: '2-digit', timeZone: 'UTC' });
  // Draw at the rendered pixel width so text stays 10–11px on phones instead of scaling a fixed canvas down.
  const widthOf = (svg) => Math.max(280, Math.min(720, Math.round(svg.getBoundingClientRect().width || 640)));
  const niceStep = (span) => {
    const raw = span / 4;
    const mag = 10 ** Math.floor(Math.log10(raw || 1));
    return [1, 2, 2.5, 5, 10].map((m) => m * mag).find((s) => s >= raw) || mag * 10;
  };

  // ---- tooltip (one shared element, text only) -----------------------------------------------------------------
  const tip = document.createElement('div');
  tip.className = 'pointer-events-none absolute z-30 hidden rounded-lg border border-white/10 bg-[#0b1715] px-3 py-2 font-mono text-[11px] leading-5 text-white shadow-xl';
  const showTip = (panel, x, y, lines) => {
    if (tip.parentElement !== panel) panel.appendChild(tip);
    tip.replaceChildren(...lines.map(([text, strong]) => {
      const row = document.createElement('div');
      row.textContent = text;
      if (strong) row.className = 'font-bold';
      else row.className = 'text-[#9fb3ad]';
      return row;
    }));
    tip.classList.remove('hidden');
    const box = panel.getBoundingClientRect();
    const left = Math.min(Math.max(x - box.left + 12, 4), box.width - tip.offsetWidth - 4);
    tip.style.left = `${left}px`;
    tip.style.top = `${Math.max(y - box.top - tip.offsetHeight - 10, 4)}px`;
  };
  const hideTip = () => tip.classList.add('hidden');

  // ---- rolling Sharpe line ---------------------------------------------------------------------------------------
  function drawSharpe(svg, data) {
    const W = widthOf(svg), H = 240, L = 40, R = 12, T = 12, B = 26;
    svg.replaceChildren();
    svg.setAttribute('viewBox', `0 0 ${W} ${H}`);
    const pts = data.rolling_sharpe;
    const vals = pts.map((p) => p.sharpe).filter((v) => v != null);
    const panel = svg.closest('[data-risk-panel]');
    if (vals.length < 2) {
      svg.appendChild(svgEl('text', { x: W / 2, y: H / 2, 'text-anchor': 'middle', fill: INK, 'font-size': 13 }, 'Too few trades in any 90-day window to plot a trend.'));
      return;
    }
    const headline = data.sharpe_annualized;
    let lo = Math.min(0, ...vals, headline ?? 0), hi = Math.max(0, ...vals, headline ?? 0);
    const step = niceStep(hi - lo || 1);
    lo = Math.floor(lo / step) * step; hi = Math.ceil(hi / step) * step;
    const x = (i) => L + (i / (pts.length - 1)) * (W - L - R);
    const y = (v) => T + (1 - (v - lo) / (hi - lo)) * (H - T - B);
    for (let v = lo; v <= hi + 1e-9; v += step) {
      svg.appendChild(svgEl('line', { x1: L, x2: W - R, y1: y(v), y2: y(v), stroke: Math.abs(v) < 1e-9 ? 'rgba(255,255,255,.28)' : GRID }));
      svg.appendChild(svgEl('text', { x: L - 6, y: y(v) + 4, 'text-anchor': 'end', fill: INK, 'font-size': 10, 'font-family': 'DM Mono, monospace' }, fmt(v, step < 1 ? 1 : 0)));
    }
    const ticks = W < 420 ? 2 : 4;
    for (let k = 0; k <= ticks; k += 1) {
      const i = Math.round((k / ticks) * (pts.length - 1));
      svg.appendChild(svgEl('text', { x: x(i), y: H - 8, 'text-anchor': k === 0 ? 'start' : k === ticks ? 'end' : 'middle', fill: INK, 'font-size': 10, 'font-family': 'DM Mono, monospace' }, monthLabel(pts[i].date)));
    }
    if (headline != null) {
      svg.appendChild(svgEl('line', { x1: L, x2: W - R, y1: y(headline), y2: y(headline), stroke: '#f2bd5b', 'stroke-dasharray': '4 4', 'stroke-width': 1 }));
      svg.appendChild(svgEl('text', { x: W - R - 2, y: y(headline) - 5, 'text-anchor': 'end', fill: '#f2bd5b', 'font-size': 10, 'font-family': 'DM Mono, monospace' }, `Full period ${fmt(headline)}`));
    }
    let d = '';
    pts.forEach((p, i) => {
      if (p.sharpe == null) return;
      const prev = pts[i - 1];
      d += `${prev && prev.sharpe != null ? 'L' : 'M'}${x(i).toFixed(1)},${y(p.sharpe).toFixed(1)}`;
    });
    svg.appendChild(svgEl('path', { d, fill: 'none', stroke: LINE, 'stroke-width': 2, 'stroke-linejoin': 'round', 'stroke-linecap': 'round' }));
    const cross = svgEl('line', { y1: T, y2: H - B, stroke: 'rgba(255,255,255,.35)', visibility: 'hidden' });
    const dot = svgEl('circle', { r: 4, fill: LINE, stroke: '#0b1715', 'stroke-width': 2, visibility: 'hidden' });
    svg.append(cross, dot);
    const hit = svgEl('rect', { x: L, y: T, width: W - L - R, height: H - T - B, fill: 'transparent', tabindex: 0 });
    svg.appendChild(hit);
    const at = (clientX) => {
      const box = svg.getBoundingClientRect();
      const vx = ((clientX - box.left) / box.width) * W;
      return Math.max(0, Math.min(pts.length - 1, Math.round(((vx - L) / (W - L - R)) * (pts.length - 1))));
    };
    const show = (i, clientX, clientY) => {
      const p = pts[i];
      cross.setAttribute('x1', x(i)); cross.setAttribute('x2', x(i)); cross.setAttribute('visibility', 'visible');
      if (p.sharpe != null) { dot.setAttribute('cx', x(i)); dot.setAttribute('cy', y(p.sharpe)); dot.setAttribute('visibility', 'visible'); } else dot.setAttribute('visibility', 'hidden');
      showTip(panel, clientX, clientY, [[p.sharpe == null ? 'n/a (under 5 trades)' : `Sharpe ${fmt(p.sharpe)}`, true], [`90 days to ${p.date}`], [`${p.trades} trades closed in window`]]);
    };
    hit.addEventListener('pointermove', (e) => show(at(e.clientX), e.clientX, e.clientY));
    hit.addEventListener('pointerleave', () => { hideTip(); cross.setAttribute('visibility', 'hidden'); dot.setAttribute('visibility', 'hidden'); });
    hit.addEventListener('focus', () => { const b = svg.getBoundingClientRect(); show(pts.length - 1, b.right - 40, b.top + 40); });
    hit.addEventListener('blur', hideTip);
  }

  // ---- streak histogram: wins above the axis, losses below (position is the secondary encoding) -----------------
  function drawStreaks(svg, streaks) {
    const W = widthOf(svg), H = 240, L = W < 420 ? 44 : 34, R = 12, T = 16, B = 24;
    svg.replaceChildren();
    svg.setAttribute('viewBox', `0 0 ${W} ${H}`);
    const panel = svg.closest('[data-risk-panel]');
    const wins = streaks.wins || {}, losses = streaks.losses || {};
    const longest = Math.max(streaks.max_win_streak || 0, streaks.max_loss_streak || 0);
    if (!longest) {
      svg.appendChild(svgEl('text', { x: W / 2, y: H / 2, 'text-anchor': 'middle', fill: INK, 'font-size': 13 }, 'No closed trades in this window.'));
      return;
    }
    const cap = Math.min(longest, 12);
    const bucket = (obj, k) => (k < cap ? obj[String(k)] || 0 : Object.entries(obj).filter(([n]) => Number(n) >= cap).reduce((s, [, v]) => s + v, 0));
    const rows = Array.from({ length: cap }, (_, i) => ({ len: i + 1, w: bucket(wins, i + 1), l: bucket(losses, i + 1) }));
    const peak = Math.max(...rows.map((r) => Math.max(r.w, r.l)), 1);
    const scale = (v) => Math.sqrt(v / peak);  // square-root scale keeps rare long streaks visible
    const mid = T + (H - T - B) / 2;
    const half = (H - T - B) / 2 - 12;
    const slot = (W - L - R) / cap;
    const barW = Math.max(6, Math.min(34, slot - 6));
    svg.appendChild(svgEl('text', { x: 4, y: T + 8, fill: INK, 'font-size': 10, 'font-family': 'DM Mono, monospace' }, 'WINS'));
    svg.appendChild(svgEl('text', { x: 4, y: H - B - 2, fill: INK, 'font-size': 10, 'font-family': 'DM Mono, monospace' }, 'LOSSES'));
    rows.forEach((r, i) => {
      const cx = L + slot * i + slot / 2;
      const hw = scale(r.w) * half, hl = scale(r.l) * half;
      const group = svgEl('g', { tabindex: 0, role: 'img', 'aria-label': `${r.len}${r.len === cap && cap < longest ? '+' : ''}-trade streaks: ${r.w} winning, ${r.l} losing` });
      group.appendChild(svgEl('rect', { x: cx - slot / 2, y: T, width: slot, height: H - T - B, fill: 'transparent' }));
      if (r.w) group.appendChild(svgEl('rect', { x: cx - barW / 2, y: mid - 1 - hw, width: barW, height: hw, rx: 3, fill: WIN }));
      if (r.l) group.appendChild(svgEl('rect', { x: cx - barW / 2, y: mid + 1, width: barW, height: hl, rx: 3, fill: LOSS }));
      if (r.w) group.appendChild(svgEl('text', { x: cx, y: mid - 5 - hw, 'text-anchor': 'middle', fill: '#e8f4f0', 'font-size': 10, 'font-family': 'DM Mono, monospace' }, r.w));
      if (r.l) group.appendChild(svgEl('text', { x: cx, y: mid + 13 + hl, 'text-anchor': 'middle', fill: '#e8f4f0', 'font-size': 10, 'font-family': 'DM Mono, monospace' }, r.l));
      group.appendChild(svgEl('text', { x: cx, y: H - 6, 'text-anchor': 'middle', fill: INK, 'font-size': 10, 'font-family': 'DM Mono, monospace' }, `${r.len}${r.len === cap && cap < longest ? '+' : ''}`));
      const show = (e) => {
        const b = group.getBoundingClientRect();
        showTip(panel, e?.clientX ?? b.left + b.width / 2, e?.clientY ?? b.top + 20,
          [[`${r.w} win · ${r.l} loss`, true], [`Streaks of ${r.len}${r.len === cap && cap < longest ? '+' : ''} trades`]]);
      };
      group.addEventListener('pointermove', show);
      group.addEventListener('pointerleave', hideTip);
      group.addEventListener('focus', () => show());
      group.addEventListener('blur', hideTip);
      svg.appendChild(group);
    });
    svg.insertBefore(svgEl('line', { x1: L, x2: W - R, y1: mid, y2: mid, stroke: 'rgba(255,255,255,.28)' }), svg.firstChild);
  }

  // ---- data loading (follows the evidence period selector) -------------------------------------------------------
  const sharpeSvg = root.querySelector('[data-risk-sharpe]');
  const streakSvg = root.querySelector('[data-risk-streaks]');
  const setText = (sel, text) => { const n = root.querySelector(sel); if (n) n.textContent = text; };
  async function load() {
    const period = document.querySelector('[data-chart-period]')?.value || '3y';
    const url = new URL(root.dataset.riskUrl, window.location.origin);
    url.searchParams.set('period', period);
    root.classList.add('opacity-60');
    try {
      const response = await fetch(url);
      if (!response.ok) throw new Error(String(response.status));
      const data = await response.json();
      last = data;
      drawSharpe(sharpeSvg, data);
      drawStreaks(streakSvg, data.streaks);
      const valid = data.rolling_sharpe.filter((p) => p.sharpe != null).map((p) => p.sharpe);
      const share = valid.length ? Math.round((valid.filter((v) => v > 0).length / valid.length) * 100) : null;
      setText('[data-risk-sharpe-latest]', fmt(valid.at(-1)));
      setText('[data-risk-sharpe-note]', valid.length
        ? `${data.window_days}-day trailing window, sampled every ${data.sample_every_days} days, ${data.from} to ${data.to}. Positive in ${share}% of windows; range ${fmt(Math.min(...valid))} to ${fmt(Math.max(...valid))}. Dashed line = full-period Sharpe.`
        : `${data.from} to ${data.to}. Windows with under 5 closed trades are not plotted.`);
      const s = data.streaks;
      setText('[data-risk-streak-max]', `W${s.max_win_streak} · L${s.max_loss_streak}`);
      setText('[data-risk-streak-note]', `Average winning streak ${fmt(s.avg_win_streak, 1)} trades, average losing streak ${fmt(s.avg_loss_streak, 1)}. Counts of streaks by length (square-root bar scale); break-even trades end a streak. ${data.from} to ${data.to}.`);
    } catch (_error) {
      setText('[data-risk-sharpe-note]', 'Risk charts are unavailable for this period.');
      setText('[data-risk-streak-note]', '');
      sharpeSvg.replaceChildren(); streakSvg.replaceChildren();
    } finally {
      root.classList.remove('opacity-60');
    }
  }
  let last = null;
  let resizeTimer = null;
  window.addEventListener('resize', () => {
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(() => { if (last) { drawSharpe(sharpeSvg, last); drawStreaks(streakSvg, last.streaks); } }, 150);
  });
  document.querySelector('[data-chart-period]')?.addEventListener('change', load);
  document.querySelector('[data-chart-apply]')?.addEventListener('click', load);
  load();
})();

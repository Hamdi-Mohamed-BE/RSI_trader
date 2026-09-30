// Prop Challenge Simulator — client. All text is inserted with textContent (no HTML injection).
(() => {
  const root = document.querySelector('[data-prop-sim]');
  if (!root) return;
  const $ = (sel) => root.querySelector(sel);
  const state = { catalog: null, rows: new Map() };

  const el = (tag, attrs = {}, ...children) => {
    const node = document.createElement(tag);
    Object.entries(attrs).forEach(([k, v]) => {
      if (v == null) return;
      if (k === 'class') node.className = v; else if (k === 'text') node.textContent = v; else node.setAttribute(k, v);
    });
    children.flat().forEach((c) => node.append(c instanceof Node ? c : document.createTextNode(String(c))));
    return node;
  };
  const pct = (v, d = 1) => (v == null || !Number.isFinite(Number(v)) ? '—' : `${(Number(v) * 100).toFixed(d)}%`);
  const num = (v, d = 2) => (v == null || !Number.isFinite(Number(v)) ? '—' : Number(v).toLocaleString('en-US', { maximumFractionDigits: d, minimumFractionDigits: d }));
  const usd = (v) => (v == null || !Number.isFinite(Number(v)) ? '—' : `${Number(v) < 0 ? '−' : ''}$${Math.abs(Number(v)).toLocaleString('en-US', { maximumFractionDigits: 0 })}`);
  const range = (a, b, f = pct) => (f(a) === f(b) ? f(a) : `${f(a)} – ${f(b)}`);
  const badgeClass = { ok: 'badge-good', adjusted: 'badge-warn', approval: 'badge-warn', restricted: 'badge-warn', blocked: 'badge-bad' };
  const statusText = { ok: 'Compatible', adjusted: 'Compatible · adjusted', approval: 'Needs firm approval', restricted: 'Restricted EA policy', blocked: 'Blocked' };

  const programme = () => state.catalog.programmes.find((p) => p.id === $('[data-programme]').value);

  function renderProgrammes() {
    const select = $('[data-programme]');
    select.replaceChildren();
    const firms = [...new Set(state.catalog.programmes.map((p) => p.firm))];
    firms.forEach((firm) => {
      const group = el('optgroup', { label: firm });
      state.catalog.programmes.filter((p) => p.firm === firm).forEach((p) => group.append(el('option', { value: p.id, text: p.programme })));
      select.append(group);
    });
    select.value = 'ftmo-2step-swing';
  }

  // Firm logo: the firm's official icon stored locally under /static/prop-firms, else a neutral initials badge.
  function firmLogo(p, size = 'h-10 w-10') {
    const small = /h-[456]\b/.test(size);
    if (p.logo_url) {
      return el('img', { src: p.logo_url, alt: '', class: `${size} shrink-0 ${small ? 'rounded-md p-px' : 'rounded-xl p-1'} bg-white object-contain` });
    }
    const initials = p.firm.split(/[\s-]+/).filter(Boolean).slice(0, 2).map((w) => w[0].toUpperCase()).join('');
    const hue = [...p.firm].reduce((h, ch) => (h * 31 + ch.charCodeAt(0)) % 360, 7);
    return el('span', {
      class: `${size} grid shrink-0 place-items-center rounded-xl border font-mono text-xs font-bold`, 'aria-hidden': 'true',
      style: `color:hsl(${hue} 85% 78%);background:hsl(${hue} 60% 45% / .16);border-color:hsl(${hue} 60% 60% / .35)`, text: initials,
    });
  }

  // ---- programme dropdown with firm logos (styled like the site's native selects) ------------------------------
  const picker = { open: false, active: -1 };
  const optionNodes = () => [...$('[data-programme-list]').querySelectorAll('[role="option"]')];

  function selectProgramme(id) {
    $('[data-programme]').value = id;
    closePicker(true);
    renderProgrammeInfo();
  }

  function programmeLabel(p, small = false) {
    return el('span', { class: 'flex min-w-0 items-center gap-2' }, firmLogo(p, small ? 'h-5 w-5' : 'h-6 w-6'),
      el('span', { class: 'truncate' }, el('span', { class: 'font-semibold text-white', text: p.firm }),
        el('span', { class: 'text-[#9cafaa]', text: ` — ${p.programme}` })));
  }

  function renderProgrammePicker() {
    const current = programme();
    $('[data-programme-current]').replaceChildren(programmeLabel(current));
    const byFirm = new Map();
    state.catalog.programmes.forEach((p) => byFirm.set(p.firm, [...(byFirm.get(p.firm) || []), p]));
    const nodes = [];
    byFirm.forEach((programmesOfFirm, firm) => {
      nodes.push(el('li', { role: 'presentation', class: 'flex items-center gap-2 px-3 pb-1 pt-2 font-mono text-[9px] uppercase tracking-[.13em] text-[#789089]' },
        firmLogo(programmesOfFirm[0], 'h-4 w-4'), el('span', { text: firm })));
      programmesOfFirm.forEach((p) => {
        const selected = p.id === current.id;
        const option = el('li', {
          role: 'option', id: `programme-option-${p.id}`, 'aria-selected': String(selected), 'data-id': p.id,
          class: `mx-1 flex cursor-pointer items-center justify-between gap-3 rounded-lg px-3 py-2 text-sm ${selected ? 'bg-mint/[.10]' : ''} hover:bg-white/[.05]`,
        }, programmeLabel(p, true), p.verification.status === 'official'
          ? el('span', { class: 'shrink-0 font-mono text-[9px] uppercase text-mint', text: 'official rules' }) : '');
        option.addEventListener('click', () => selectProgramme(p.id));
        nodes.push(option);
      });
    });
    $('[data-programme-list]').replaceChildren(...nodes);
  }

  function setActive(index) {
    const options = optionNodes();
    if (!options.length) return;
    picker.active = (index + options.length) % options.length;
    options.forEach((o, i) => { o.classList.toggle('ring-1', i === picker.active); o.classList.toggle('ring-mint/50', i === picker.active); });
    const node = options[picker.active];
    $('[data-programme-list]').setAttribute('aria-activedescendant', node.id);
    node.scrollIntoView({ block: 'nearest' });
  }

  function openPicker() {
    picker.open = true;
    $('[data-programme-list]').classList.remove('hidden');
    $('[data-programme-toggle]').setAttribute('aria-expanded', 'true');
    setActive(Math.max(0, optionNodes().findIndex((o) => o.dataset.id === programme().id)));
    $('[data-programme-list]').focus();
  }

  function closePicker(returnFocus = false) {
    if (!picker.open) return;
    picker.open = false;
    $('[data-programme-list]').classList.add('hidden');
    $('[data-programme-toggle]').setAttribute('aria-expanded', 'false');
    if (returnFocus) $('[data-programme-toggle]').focus();
  }

  function wirePicker() {
    $('[data-programme-toggle]').addEventListener('click', () => (picker.open ? closePicker() : openPicker()));
    $('[data-programme-toggle]').addEventListener('keydown', (e) => {
      if (['ArrowDown', 'ArrowUp', 'Enter', ' '].includes(e.key)) { e.preventDefault(); openPicker(); }
    });
    $('[data-programme-list]').addEventListener('keydown', (e) => {
      if (e.key === 'ArrowDown') { e.preventDefault(); setActive(picker.active + 1); }
      else if (e.key === 'ArrowUp') { e.preventDefault(); setActive(picker.active - 1); }
      else if (e.key === 'Home') { e.preventDefault(); setActive(0); }
      else if (e.key === 'End') { e.preventDefault(); setActive(-1); }
      else if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); const o = optionNodes()[picker.active]; if (o) selectProgramme(o.dataset.id); }
      else if (e.key === 'Escape' || e.key === 'Tab') { closePicker(e.key === 'Escape'); }
    });
    document.addEventListener('click', (e) => { if (!$('[data-programme-picker]').contains(e.target)) closePicker(); });
  }

  function renderProgrammeInfo() {
    const p = programme();
    renderProgrammePicker();
    const sizes = $('[data-size]');
    const previous = Number(sizes.value);
    sizes.replaceChildren(...p.account_sizes.map((s) => el('option', { value: s, text: `$${s.toLocaleString('en-US')}` })));
    sizes.value = p.account_sizes.includes(previous) ? previous : (p.account_sizes.includes(10000) ? 10000 : p.account_sizes[0]);
    updateFeePlaceholder();
    const phases = p.phases.length ? p.phases.map((ph) => `${ph.name}: ${ph.target_pct}% target${ph.min_trading_days ? `, ${ph.min_trading_days} trading days` : ''}${ph.min_profitable_days ? `, ${ph.min_profitable_days} profitable days` : ''}`).join(' · ') : 'No challenge — funded from day one';
    const lines = [
      phases,
      `Daily loss ${p.daily_loss_pct == null ? 'none' : `${p.daily_loss_pct}% of initial`} · Max loss ${p.max_loss_pct}% (${p.max_loss_type.replaceAll('_', ' ')})${p.consistency_best_day_pct ? ` · Best day ≤ ${p.consistency_best_day_pct}% of profit` : ''}`,
      `Payout ${p.payout.split_pct}% split, first after ${p.payout.first_after_days} days then every ${p.payout.every_days}${p.payout.fee_refund ? ', fee refunded with first payout' : ''} · News: challenge ${p.news.challenge}, funded ${p.news.funded} · Weekend holding funded: ${p.weekend_holding.funded ? 'allowed' : 'not allowed'}`,
      `EA policy: ${p.ea_policy.status} — ${p.ea_policy.notes || ''}`,
    ];
    const verified = p.verification.status === 'official';
    const info = $('[data-programme-info]');
    info.replaceChildren(
      el('div', { class: 'mb-3 flex items-center gap-3' }, firmLogo(p, 'h-9 w-9'),
        el('div', {}, el('strong', { class: 'block text-sm text-white', text: p.firm }), el('span', { class: 'text-[11px]', text: p.programme }))),
      el('div', { class: 'mb-2 flex flex-wrap items-center gap-2' },
        el('span', { class: `badge ${verified ? 'badge-good' : 'badge-warn'}`, text: verified ? 'Checked on the firm’s own page' : 'From comparison sources — verify with the firm' }),
        el('span', { class: 'font-mono text-[10px]', text: `Checked ${p.verification.checked}` })),
      ...lines.map((line) => el('p', { text: line })),
      el('p', { class: 'mt-2 text-muted/80', text: p.verification.notes || '' }),
      el('p', { class: 'mt-1' }, ...p.verification.sources.map((url, i) => el('a', { href: url, target: '_blank', rel: 'noopener nofollow', class: 'mr-3 underline decoration-white/20 hover:text-white', text: `Source ${i + 1}` }))),
    );
    renderEaTable();
    renderPresets();
  }

  function updateFeePlaceholder() {
    const p = programme();
    const fee = p.fees[String($('[data-size]').value)];
    $('[data-fee]').placeholder = fee != null ? `List price ≈ ${fee} ${p.fee_currency}` : 'Enter fee for expected value';
  }

  // ---- risk units: fixed $ per trade (converted to % of the initial balance for the engine) or % ------------------
  const sizingUnit = () => ($('[data-sizing]').value === 'fixed_usd' ? 'usd' : 'pct');
  const accountSize = () => Number($('[data-size]').value) || 10000;
  const fallbackRisk = () => (sizingUnit() === 'usd' ? 50 : 0.5);
  const positive = (v) => { const n = Number(v); return Number.isFinite(n) && n > 0 ? n : null; };
  const defaultRiskValue = () => positive($('[data-risk]').value) ?? fallbackRisk();
  function riskAttrs(input) {
    const usdMode = sizingUnit() === 'usd';
    input.min = usdMode ? '1' : '0.05';
    input.step = usdMode ? '1' : '0.05';
    input.max = usdMode ? String(Math.floor(accountSize() * 0.03)) : '3';
  }
  function applyUnitLabels() {
    const usdMode = sizingUnit() === 'usd';
    $('[data-risk-label]').textContent = usdMode ? 'Risk per trade ($)' : 'Risk per trade (% of account)';
    $('[data-risk-head]').textContent = usdMode ? 'Risk $' : 'Risk %';
    riskAttrs($('[data-risk]'));
    state.rows.forEach((row) => riskAttrs(row.risk));
  }
  function convertRisk(from, to) {
    if (from === to) return;
    const convert = (v) => {
      const n = positive(v);
      if (n == null) return to === 'usd' ? 50 : 0.5;
      return to === 'usd' ? Math.max(1, Math.round(n * accountSize() / 100)) : +(n / accountSize() * 100).toFixed(4);
    };
    $('[data-risk]').value = convert($('[data-risk]').value);
    state.rows.forEach((row) => { row.risk.value = convert(row.risk.value); });
  }

  function renderEaTable() {
    const p = programme();
    const body = $('[data-ea-table] tbody');
    const compat = state.catalog.compatibility[p.id];
    const defaultRisk = defaultRiskValue();
    body.replaceChildren(...state.catalog.eas.map((ea) => {
      const c = compat[ea.slug];
      const prev = state.rows.get(ea.slug);
      const box = el('input', { type: 'checkbox', 'data-slug': ea.slug, 'aria-label': `Select ${ea.label}` });
      box.checked = Boolean(prev?.checked) && c.status !== 'blocked';
      box.disabled = c.status === 'blocked';
      const risk = el('input', { type: 'number', class: 'w-20 rounded-lg border border-white/10 bg-[#0b1715] px-2 py-1 text-xs text-white' });
      riskAttrs(risk);
      risk.value = positive(prev?.risk?.value) ?? defaultRisk;  // keep the previous row's value across re-renders
      state.rows.set(ea.slug, { box, risk, checked: box.checked });
      box.addEventListener('change', () => { state.rows.get(ea.slug).checked = box.checked; });
      return el('tr', { class: `border-t border-white/[.06] ${c.status === 'blocked' ? 'opacity-50' : ''}` },
        el('td', { class: 'py-2 pr-3' }, box),
        el('td', { class: 'py-2 pr-3' }, el('a', { href: `/eas/${ea.slug}`, target: '_blank', class: 'font-semibold hover:text-mint', text: ea.label })),
        el('td', { class: 'py-2 pr-3 font-mono text-xs text-muted', text: `${ea.symbol} ${ea.timeframe}` }),
        el('td', { class: 'py-2 pr-3 font-mono text-xs', text: ea.trades }),
        el('td', { class: 'py-2 pr-3' }, el('span', { class: `badge ${badgeClass[c.status]}`, title: c.reasons.join(' ') || 'No conflicts found', text: statusText[c.status] })),
        el('td', { class: 'py-2' }, risk));
    }));
  }

  function applyPreset(preset) {
    if (preset.programme_id && state.catalog.programmes.some((p) => p.id === preset.programme_id)) {
      $('[data-programme]').value = preset.programme_id;
      renderProgrammeInfo();
    }
    if (preset.account_size) { $('[data-size]').value = preset.account_size; updateFeePlaceholder(); }
    if (preset.sizing) { $('[data-sizing]').value = preset.sizing; state.unit = sizingUnit(); applyUnitLabels(); }
    const guards = preset.guards || {};
    $('[data-equity-stop]').value = guards.equity_stop_pct ?? '';
    $('[data-profit-close]').value = guards.profit_close_pct ?? '';
    $('[data-daily-stop]').value = guards.daily_stop_pct ?? '';
    $('[data-profit-lock]').value = guards.profit_lock_pct ?? '';
    $('[data-open-risk]').value = guards.max_open_risk_pct ?? '';
    $('[data-max-entries]').value = guards.max_entries_per_day ?? '';
    const usdMode = sizingUnit() === 'usd';
    const valueOf = (e) => (usdMode ? (e.risk_usd ?? Math.round(e.risk_pct * accountSize() / 100)) : e.risk_pct);
    const picks = new Map(preset.eas.map((e) => [e.slug, valueOf(e)]));
    if (preset.eas.length) $('[data-risk]').value = valueOf(preset.eas[0]);
    state.rows.forEach((row, slug) => {
      const selected = picks.has(slug) && !row.box.disabled;
      row.box.checked = selected; row.checked = selected;
      if (selected) row.risk.value = picks.get(slug);
    });
    setStatus(`Loaded: ${preset.label}. ${preset.note || ''}`);
  }

  function renderPresets() {
    const holder = $('[data-presets]');
    const buttons = state.catalog.presets.map((preset) => {
      const b = el('button', { type: 'button', class: 'button-secondary text-xs', text: preset.label.replace(/ \(.*\)$/, '') });
      b.addEventListener('click', () => applyPreset(preset));
      return b;
    });
    const suggestions = state.catalog.suggestions?.programmes?.[programme().id];
    if (suggestions) {
      Object.entries(suggestions.objectives || {}).forEach(([key, s]) => {
        if (!s) return;
        const b = el('button', { type: 'button', class: 'button-primary text-xs', title: s.summary || '', text: `Suggested · ${s.objective_label}` });
        b.addEventListener('click', () => applyPreset({ ...s, programme_id: programme().id, label: `Suggested (${s.objective_label})`, note: s.summary }));
        buttons.push(b);
      });
    }
    const clear = el('button', { type: 'button', class: 'button-secondary text-xs', text: 'Clear' });
    clear.addEventListener('click', () => state.rows.forEach((row) => { row.box.checked = false; row.checked = false; }));
    holder.replaceChildren(...buttons, clear);
    renderSuggestionTable(suggestions);
  }

  function renderSuggestionTable(suggestions) {
    const box = $('[data-suggestions]');
    const items = Object.values(suggestions?.objectives || {}).filter(Boolean);
    if (!items.length) { box.classList.add('hidden'); box.replaceChildren(); return; }
    const label = (slug) => state.catalog.eas.find((e) => e.slug === slug)?.label || slug;
    const head = ['Suggestion', 'EAs · risk · guard', 'Pass all (dev)', 'Pass all (holdout)', 'Median days (dev → holdout)', 'Trades / month', 'Sharpe (ann.)'];
    const rows = items.map((s) => {
      const d = s.development, h = s.holdout;
      const guard = Object.entries(s.guards || {}).filter(([, v]) => v != null).map(([k, v]) => `${k.replace('_pct', '').replaceAll('_', ' ')} ${v}`).join(', ') || 'no guard';
      return el('tr', { class: 'border-t border-white/[.06] align-top' },
        el('td', { class: 'py-2 pr-3 font-semibold text-mint', text: s.objective_label }),
        el('td', { class: 'py-2 pr-3', title: s.eas.map((e) => label(e.slug)).join(', '), text: `${s.eas.length} EAs · ${s.eas[0]?.risk_pct}% · ${guard}` }),
        el('td', { class: 'py-2 pr-3 font-mono', text: range(d.pass_all[0], d.pass_all[1]) }),
        el('td', { class: 'py-2 pr-3 font-mono', text: range(h.pass_all[0], h.pass_all[1]) }),
        el('td', { class: 'py-2 pr-3 font-mono', text: `${num(d.median_days_to_funded, 0)} → ${num(h.median_days_to_funded, 0)}` }),
        el('td', { class: 'py-2 pr-3 font-mono', text: num(h.trades_per_month, 1) }),
        el('td', { class: 'py-2 font-mono', text: num(h.sharpe_annualized, 2) }));
    });
    box.replaceChildren(
      el('p', { class: 'font-mono text-[10px] uppercase tracking-[.14em] text-muted', text: 'Suggested combinations for this programme' }),
      el('table', { class: 'mt-2 w-full min-w-[720px] text-left text-xs' },
        el('thead', { class: 'text-[10px] uppercase text-muted' }, el('tr', {}, ...head.map((h) => el('th', { class: 'py-1 pr-3', text: h })))),
        el('tbody', {}, ...rows)),
      el('p', { class: 'mt-2 text-[11px] leading-5 text-muted', text: `${state.catalog.suggestions.method} Generated ${state.catalog.suggestions.generated_at}.` }));
    box.classList.remove('hidden');
  }

  const setStatus = (text, bad = false) => { const s = $('[data-status]'); s.textContent = text; s.classList.toggle('text-red-300', bad); };
  const optionalNumber = (sel) => { const v = $(sel).value.trim(); return v === '' ? null : Number(v); };

  function request() {
    const usdMode = sizingUnit() === 'usd';
    const toPct = (v) => (usdMode ? +(Number(v) / accountSize() * 100).toFixed(6) : Number(v));
    const fallback = defaultRiskValue();
    const eas = [...state.rows.entries()].filter(([, r]) => r.box.checked).map(([slug, r]) => {
      const value = positive(r.risk.value);
      if (value == null) r.risk.value = fallback;  // empty/zero row risk falls back to the default risk per trade
      return { slug, risk_pct: toPct(value ?? fallback) };
    });
    return {
      programme_id: programme().id, account_size: accountSize(), fee: optionalNumber('[data-fee]'), eas,
      sizing: usdMode ? 'pct_initial' : $('[data-sizing]').value,
      equity_stop_pct: optionalNumber('[data-equity-stop]'), profit_close_pct: optionalNumber('[data-profit-close]'), daily_stop_pct: optionalNumber('[data-daily-stop]'), profit_lock_pct: optionalNumber('[data-profit-lock]'),
      max_open_risk_pct: optionalNumber('[data-open-risk]'), max_entries_per_day: optionalNumber('[data-max-entries]'),
      period: $('[data-period]').value, method: $('[data-method]').value, paths: Number($('[data-paths]').value),
      horizon_days: Number($('[data-horizon]').value), block_days: Number($('[data-block]').value),
    };
  }

  async function run() {
    const body = request();
    if (!body.eas.length) { setStatus('Select at least one compatible EA.', true); return; }
    const button = $('[data-run]');
    button.disabled = true; setStatus(`Simulating ${body.paths.toLocaleString('en-US')} paths…`);
    try {
      const response = await fetch('/api/prop-sim/run', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
      const payload = await response.json();
      if (!response.ok) { setStatus([payload.detail, ...(payload.errors || [])].join(' '), true); return; }
      renderResults(payload); setStatus(`Done · ${payload.generated_at}`);
    } catch (error) {
      setStatus('The simulation could not be completed. Please try again.', true);
    } finally { button.disabled = false; }
  }

  const tile = (label, value, title) => el('div', { title }, el('span', { text: label }), el('strong', { text: value }));

  function renderResults(data) {
    const c = data.results.conservative, o = data.results.optimistic;
    const p = data.programme;
    $('[data-results]').classList.remove('hidden');
    $('[data-result-title]').textContent = `${p.label} · $${data.request.account_size.toLocaleString('en-US')} · ${Object.keys(data.eas).length} EA${Object.keys(data.eas).length > 1 ? 's' : ''}`;
    const kpis = [];
    c.phases.forEach((ph, i) => kpis.push(tile(`Pass phase ${ph.phase}${i ? ' (cumulative)' : ''}`, range(ph.pass_rate, o.phases[i].pass_rate))));
    if (c.phase2_given_phase1 != null) kpis.push(tile('Phase 2 | passed phase 1', range(c.phase2_given_phase1, o.phase2_given_phase1)));
    kpis.push(tile(p.phases.length ? 'Pass all phases' : 'Funded from start', range(c.pass_all_rate, o.pass_all_rate)));
    kpis.push(tile('Daily-loss breach', range(c.breaches.daily_loss.rate, o.breaches.daily_loss.rate)));
    kpis.push(tile('Max-loss breach', range(c.breaches.max_loss.rate, o.breaches.max_loss.rate)));
    if (c.days_to_funded) kpis.push(tile('Median days to funded', num(c.days_to_funded.median, 0), `25th–75th percentile: ${num(c.days_to_funded.p25, 0)}–${num(c.days_to_funded.p75, 0)} days`));
    const by = c.payout.probability_any_by;
    Object.keys(by).forEach((h) => kpis.push(tile(`≥1 payout within ${h} days`, range(by[h], o.payout.probability_any_by[h]))));
    kpis.push(tile('Expected payouts (count)', num(c.payout.expected_payouts, 2)));
    kpis.push(tile('Expected payout after split', usd(c.payout.expected_payout_usd), `5th / 50th / 95th percentile: ${c.payout.payout_usd_p5_p50_p95.map(usd).join(' / ')}`));
    kpis.push(tile('Expected value after fee', c.payout.expected_value_usd == null ? 'Enter fee' : usd(c.payout.expected_value_usd), data.fee_currency_note || `Fee used: ${data.fee_used}`));
    $('[data-kpis]').replaceChildren(...kpis);

    const outcomes = [
      ['Passed every phase', c.pass_all_rate, 'bg-mint'], ['Daily-loss breach', c.breaches.daily_loss.rate, 'bg-red-400'],
      ['Max-loss breach', c.breaches.max_loss.rate, 'bg-red-300'], ['Time limit', c.breaches.time_limit.rate, 'bg-amber-300'],
      ['Still in challenge at horizon', c.unresolved_rate, 'bg-white/40'], ['Funded & alive at horizon', c.funded_alive_at_end, 'bg-sky-300'],
    ];
    $('[data-outcomes]').replaceChildren(...outcomes.map(([label, value, color]) => el('div', {},
      el('div', { class: 'flex justify-between text-xs' }, el('span', { text: label }), el('strong', { text: pct(value) })),
      el('div', { class: 'mt-1 h-2 rounded-full bg-white/[.06]' }, el('div', { class: `h-2 rounded-full ${color}`, style: `width:${Math.max(0, Math.min(100, value * 100)).toFixed(1)}%` })))));

    const s = data.stats;
    $('[data-stats]').replaceChildren(
      tile('Trades', s.trades), tile('Trades / month', num(s.trades_per_month, 1)), tile('Trades / day', num(s.trades_per_day, 2)),
      tile('Return', `${num(s.return_pct, 2)}%`), tile('Profit factor', num(s.profit_factor, 2)), tile('Win rate', `${num(s.win_rate_pct, 1)}%`),
      tile('Consistency', s.consistency_pct == null ? '—' : `${num(s.consistency_pct, 1)}%`, 'Share of trading days that closed positive'),
      tile('Avg win / loss streak', `${num(s.avg_win_streak, 1)} / ${num(s.avg_loss_streak, 1)}`), tile('Max win / loss streak', `${s.max_win_streak} / ${s.max_loss_streak}`),
      tile('Sharpe (ann.)', num(s.sharpe_annualized, 2), 'Daily closed-trade returns, √365, same definition as every EA page'),
      tile('Max balance DD', `${num(s.max_balance_dd_pct, 2)}%`), tile('Max equity DD', 'n/a', 'Intratrade equity is not recorded in the cached evidence'),
      tile('Worst day', `${num(s.worst_day_pct, 2)}%`), tile('Worst day, open risk at stop', `${num(s.worst_intraday_envelope_pct, 2)}%`),
    );

    const perEa = $('[data-per-ea]');
    perEa.replaceChildren(el('thead', { class: 'font-mono text-[10px] uppercase text-muted' }, el('tr', {}, ...['EA', 'Trades', 'Net %', 'PF', 'Win %'].map((h) => el('th', { class: 'py-1 pr-3', text: h })))),
      el('tbody', {}, ...s.per_ea.map((r) => el('tr', { class: 'border-t border-white/[.06]' },
        el('td', { class: 'py-1 pr-3', text: data.eas[r.slug]?.label || r.slug }), el('td', { class: 'py-1 pr-3', text: r.trades }),
        el('td', { class: 'py-1 pr-3', text: num(r.net_pct, 2) }), el('td', { class: 'py-1 pr-3', text: num(r.profit_factor, 2) }), el('td', { class: 'py-1', text: num(r.win_rate, 1) })))));

    const corr = s.correlation;
    const holder = $('[data-corr]');
    if (corr.matrix.length) {
      const label = (i) => data.eas[corr.slugs[i]]?.label || corr.slugs[i];
      const cell = (v) => {
        const shade = v == null ? '' : `background:rgba(${v > 0 ? '248,113,113' : '126,247,199'},${Math.min(0.6, Math.abs(v) * 0.8)})`;
        return el('td', { class: 'px-1 text-center', style: shade, text: v == null ? '·' : v.toFixed(2) });
      };
      const header = el('tr', {}, el('th', {}), ...corr.slugs.map((_, i) => el('th', { class: 'px-1', title: label(i), text: `${i + 1}` })));
      const rows = corr.matrix.map((row, i) => el('tr', {},
        el('th', { class: 'pr-2 text-left', title: label(i), text: `${i + 1} ${label(i).slice(0, 18)}` }),
        ...row.map(cell)));
      holder.replaceChildren(el('table', { class: 'text-[10px] font-mono' }, header, ...rows));
    } else {
      holder.replaceChildren(el('p', { class: 'text-xs text-muted', text: 'Select two or more EAs to see correlation.' }));
    }

    $('[data-months]').replaceChildren(...Object.entries(s.monthly_returns_pct).map(([m, v]) => el('span', { class: `rounded-lg px-2 py-1 font-mono text-[10px] ${v >= 0 ? 'bg-mint/10 text-mint' : 'bg-red-400/10 text-red-300'}`, text: `${m} ${v >= 0 ? '+' : ''}${v.toFixed(2)}%` })));

    const compatNotes = Object.entries(data.compatibility).filter(([, v]) => v.reasons.length).map(([slug, v]) => el('p', { text: `${data.eas[slug].label}: ${v.reasons.join(' ')}` }));
    const skipped = Object.entries(s.skipped).map(([k, v]) => `${v} × ${k}`).join(', ');
    $('[data-rules-used]').replaceChildren(
      el('p', { text: `${p.label} — ${p.verification.status === 'official' ? 'checked on the firm’s page' : 'from comparison sources'} on ${p.verification.checked}.` }),
      el('p', { text: `Evidence window ${s.window.from} to ${s.window.to} (${s.window.days} days, common to all selected EAs).` }),
      el('p', { text: skipped ? `Trades not taken: ${skipped}.` : 'No trades were skipped by sizing or guards.' }),
      ...compatNotes);
    $('[data-assumptions]').replaceChildren(...data.assumptions.map((a) => el('li', { text: a })));
    drawFan(data.fan);
    $('[data-results]').scrollIntoView({ behavior: 'smooth', block: 'start' });
  }

  function drawFan(fan) {
    const canvas = $('[data-fan]');
    const ratio = window.devicePixelRatio || 1;
    const width = canvas.clientWidth, height = 260;
    canvas.width = width * ratio; canvas.height = height * ratio;
    const ctx = canvas.getContext('2d'); ctx.scale(ratio, ratio); ctx.clearRect(0, 0, width, height);
    const pad = { l: 46, r: 10, t: 10, b: 24 };
    const all = [...fan.p5, ...fan.p95, 0];
    const lo = Math.min(...all), hi = Math.max(...all);
    const x = (i) => pad.l + (i / (fan.day.length - 1 || 1)) * (width - pad.l - pad.r);
    const y = (v) => pad.t + (1 - (v - lo) / ((hi - lo) || 1)) * (height - pad.t - pad.b);
    ctx.font = '10px "DM Mono", monospace'; ctx.fillStyle = '#789089'; ctx.strokeStyle = 'rgba(255,255,255,.07)';
    [lo, (lo + hi) / 2, hi, 0].forEach((v) => { ctx.beginPath(); ctx.moveTo(pad.l, y(v)); ctx.lineTo(width - pad.r, y(v)); ctx.stroke(); ctx.fillText(`${v.toFixed(1)}%`, 2, y(v) + 3); });
    const band = (a, b, color) => { ctx.beginPath(); a.forEach((v, i) => (i ? ctx.lineTo(x(i), y(v)) : ctx.moveTo(x(i), y(v)))); [...b].reverse().forEach((v, j) => ctx.lineTo(x(b.length - 1 - j), y(v))); ctx.closePath(); ctx.fillStyle = color; ctx.fill(); };
    band(fan.p5, fan.p95, 'rgba(126,247,199,.10)'); band(fan.p25, fan.p75, 'rgba(126,247,199,.22)');
    ctx.beginPath(); fan.p50.forEach((v, i) => (i ? ctx.lineTo(x(i), y(v)) : ctx.moveTo(x(i), y(v)))); ctx.strokeStyle = '#7ef7c7'; ctx.lineWidth = 2; ctx.stroke();
    ctx.fillStyle = '#789089'; ctx.fillText('day 1', pad.l, height - 6); ctx.fillText(`day ${fan.day[fan.day.length - 1]}`, width - pad.r - 50, height - 6);
  }

  async function init() {
    try {
      const response = await fetch('/api/prop-sim/catalog?v=20260930-5');
      state.catalog = await response.json();
    } catch (error) { setStatus('Could not load the simulator catalogue.', true); return; }
    renderProgrammes(); wirePicker(); renderProgrammeInfo();
    $('[data-size]').addEventListener('change', updateFeePlaceholder);
    $('[data-run]').addEventListener('click', run);
    $('[data-select-all]').addEventListener('change', (e) => state.rows.forEach((row) => { if (!row.box.disabled) { row.box.checked = e.target.checked; row.checked = e.target.checked; } }));
    $('[data-risk]').addEventListener('change', () => state.rows.forEach((row) => { row.risk.value = $('[data-risk]').value; }));
    state.unit = sizingUnit();
    applyUnitLabels();
    $('[data-sizing]').addEventListener('change', () => { convertRisk(state.unit, sizingUnit()); state.unit = sizingUnit(); applyUnitLabels(); });
    $('[data-size]').addEventListener('change', applyUnitLabels);
    // Default: the saved FTMO 13 package with the tested -2% / +4% daily controls (owner's choice), else a suggestion.
    const ftmo = state.catalog.presets.find((p) => p.id === 'ftmo13-controls') || state.catalog.presets.find((p) => p.id === 'ftmo13');
    const suggestion = state.catalog.suggestions?.programmes?.[programme().id]?.objectives?.expected_value;
    if (ftmo) applyPreset(ftmo);
    else if (suggestion) applyPreset({ ...suggestion, programme_id: programme().id, label: `Suggested (${suggestion.objective_label})`, note: suggestion.summary });
  }
  init();
})();

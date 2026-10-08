/* Period-matched server-rendered fragments; no client-side financial calculations. */
(() => {
  const sequences = new WeakMap();
  const requests = new Map();
  const timers = new WeakMap();
  function riskQuery(view) {
    const form = view.querySelector('[data-risk-form]');
    if (!form || form.elements.risk_mode.value === 'recorded') return '';
    const params = new URLSearchParams(new FormData(form));
    params.delete('period'); // The view's requested period is authoritative.
    return '&' + params.toString();
  }
  function shareURL(view, period) {
    return `/portfolios/${encodeURIComponent(view.dataset.portfolioView)}?period=${period}${riskQuery(view)}`;
  }
  function select(nav, period) {
    nav.querySelectorAll('[data-period]').forEach(link => {
      const active = link.dataset.period === period;
      link.classList.toggle('selected', active);
      if (active) link.setAttribute('aria-current', 'true');
      else link.removeAttribute('aria-current');
    });
  }
  async function update(view, period) {
    view.dataset.requestedPeriod = period;
    const periodField=view.querySelector('input[name="period"]');
    if(periodField) periodField.value=period;
    const sequence = (sequences.get(view) || 0) + 1;
    sequences.set(view, sequence);
    const panel = view.querySelector('[data-history-panel]');
    const status = view.querySelector('.pf-load-status');
    view.setAttribute('aria-busy', 'true');
    panel.style.opacity = '0.4';
    status.textContent = 'Loading selected period…';
    const url = `/portfolios/${encodeURIComponent(view.dataset.portfolioView)}/history?period=${encodeURIComponent(period)}&compact=${view.dataset.compact}${riskQuery(view)}`;
    try {
      // A new evidence publication must not leave an old "unavailable" period
      // cached for the rest of this browser session.
      if (requests.has(url) && Date.now()-requests.get(url).at>30000) requests.delete(url);
      if (!requests.has(url)) {
        if(requests.size>=32)requests.delete(requests.keys().next().value);
        requests.set(url, {at:Date.now(),promise:fetch(url, {headers: {'Accept': 'text/html'},cache:'no-store'}).then(async response => {
        if (!response.ok) {
          const data=await response.json().catch(() => ({}));
          throw new Error(typeof data.detail==='string' ? data.detail : 'Unable to load the selected period and risk.');
        }
        return response.text();
        }).catch(error => { requests.delete(url); throw error; })});
      }
      const html = await requests.get(url).promise;
      if (sequences.get(view) !== sequence) return;
      panel.innerHTML = html;
      select(view.querySelector('.pf-period-pills'), period);
      const detail = view.querySelector('[data-detail-link]');
      if (detail) detail.href = shareURL(view, period);
      if (view.dataset.compact==='false') window.history.replaceState(null,'',shareURL(view,period));
      status.textContent = '';
    } catch (error) {
      if (sequences.get(view) !== sequence) return;
      select(view.querySelector('.pf-period-pills'), period);
      panel.replaceChildren();
      const message = document.createElement('p');
      message.className = 'pf-warning';
      message.textContent = error.message+' Previous results are hidden. Correct the inputs or retry.';
      panel.append(message);
      status.textContent = 'Period could not be loaded.';
    } finally {
      if (sequences.get(view) === sequence) {
        view.removeAttribute('aria-busy');
        panel.style.opacity = '';
      }
    }
  }
  document.addEventListener('click', event => {
    const link = event.target.closest('[data-period]');
    if (!link || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey || event.button) return;
    const nav = link.closest('.pf-period-pills');
    if (!nav) return;
    event.preventDefault();
    const period = link.dataset.period;
    if (nav.hasAttribute('data-global-periods')) {
      select(nav, period);
      document.querySelectorAll('[data-portfolio-view]').forEach(view => update(view, period));
      window.history.replaceState(null, '', link.href);
      document.querySelectorAll('nav[aria-label="Portfolio status"] a').forEach(item => {
        const url = new URL(item.href); url.searchParams.set('period', period); item.href = url;
      });
    } else {
      const view = nav.closest('[data-portfolio-view]');
      update(view, period);
      if (view.dataset.compact !== 'false') {
        const global = document.querySelector('[data-global-periods]');
        if (global) global.querySelectorAll('a').forEach(item => {item.classList.remove('selected'); item.removeAttribute('aria-current');});
      }
    }
  });
  function calculate(form) {
    const view=form.closest('[data-portfolio-view]');
    const period=view.dataset.requestedPeriod || form.elements.period.value || '1y';
    if (!form.reportValidity()) return;
    update(view,period);
  }
  function syncControls(form) {
    const recorded=form.elements.risk_mode.value==='recorded';
    form.elements.risk_value.readOnly=recorded;
    form.elements.risk_value.max=form.elements.risk_mode.value==='percent'?'10':'100000';
    form.elements.initial_balance.readOnly=recorded || form.closest('[data-portfolio-view]').dataset.portfolioView==='ftmo';
    form.elements.daily_limit_value.readOnly=form.elements.daily_limit_mode.value==='off';
    form.elements.daily_limit_value.max=form.elements.daily_limit_mode.value==='percent'?'100':'100000';
    if(form.elements.news_risk_percent)form.elements.news_risk_percent.readOnly=recorded;
  }
  document.querySelectorAll('[data-risk-form]').forEach(syncControls);
  document.addEventListener('submit',event=>{
    const form=event.target.closest('[data-risk-form]');
    if(!form) return;
    event.preventDefault();clearTimeout(timers.get(form));calculate(form);
  });
  document.addEventListener('change',event=>{
    const form=event.target.closest('[data-risk-form]');
    if(!form) return;
    if(event.target.name==='risk_mode') {
      const mode=form.elements.risk_mode.value;
      form.elements.risk_value.value=mode==='percent'?form.dataset.defaultPercent:form.dataset.defaultFixed;
      if(mode==='recorded') {form.elements.daily_limit_mode.value='off';form.elements.daily_limit_value.value='0';}
    }
    if(event.target.name==='daily_limit_mode') {
      const mode=form.elements.daily_limit_mode.value;
      form.elements.daily_limit_value.value=mode==='fixed'?'200':mode==='percent'?'2':'0';
      if(mode!=='off' && form.elements.risk_mode.value==='recorded') {
        form.elements.risk_mode.value='percent';form.elements.risk_value.value=form.dataset.defaultPercent;
      }
    }
    syncControls(form);clearTimeout(timers.get(form));calculate(form);
  });
  document.addEventListener('input',event=>{
    const form=event.target.closest('[data-risk-form]');
    if(!form || form.elements.risk_mode.value==='recorded') return;
    clearTimeout(timers.get(form));timers.set(form,setTimeout(()=>calculate(form),400));
  });
  document.addEventListener('click',event=>{
    const reset=event.target.closest('[data-reset-risk]');
    if(!reset) return;
    const form=reset.closest('[data-risk-form]');
    clearTimeout(timers.get(form));form.elements.risk_mode.value='recorded';
    form.elements.risk_value.value=form.dataset.defaultFixed;form.elements.initial_balance.value='10000';
    form.elements.daily_limit_mode.value='off';form.elements.daily_limit_value.value='0';
    if(form.elements.news_risk_percent)form.elements.news_risk_percent.value='.10';
    syncControls(form);calculate(form);
  });
})();

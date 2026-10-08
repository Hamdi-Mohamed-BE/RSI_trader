// Headless UI regression check: own test browser, no MT5/account actions.
const { chromium } = require('C:/Users/hama101/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const fs = require('fs');
const path = require('path');
(async () => {
  const origin = process.argv[2] || 'http://127.0.0.1:8080';
  const out = process.argv[3];
  if (!out) throw Error('Pass a QA output directory.');
  fs.mkdirSync(out, { recursive: true });
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1600, height: 1250 } });
  const errors = [];
  page.on('pageerror', e => errors.push(e.message));
  async function checkClosedDD(stats) {
    const cash=stats.max_daily_closed_drawdown_cash;
    const decimals=Number.isInteger(cash)?0:2;
    const expectedCash=`$${cash.toLocaleString('en-US',{minimumFractionDigits:decimals,maximumFractionDigits:decimals})}`;
    if(await page.locator('#history [data-metric="max_daily_closed_drawdown_pct"]').innerText()!==`${stats.max_daily_closed_drawdown_pct.toFixed(2)}%`)throw Error('Daily closed DD percent mismatch');
    if(await page.locator('#history [data-metric="max_daily_closed_drawdown_cash"]').innerText()!==expectedCash)throw Error('Daily closed DD USD mismatch');
    if(await page.locator('#history [data-metric="max_daily_equity_drawdown_pct"]').count())throw Error('Unavailable floating DD tile retained');
  }
  for (const [status, n] of [['all', 4], ['active', 3], ['disabled', 1]]) {
    await page.goto(origin + '/portfolios?status=' + status, { waitUntil: 'networkidle' });
    if (await page.locator('[data-portfolio]').count() !== n) throw Error('Portfolio filter: ' + status);
  }
  await page.goto(origin + '/portfolios', { waitUntil: 'networkidle' });
  await page.screenshot({ path: path.join(out, 'Portfolios desktop.png') });
  await page.setViewportSize({ width: 390, height: 844 });
  await page.screenshot({ path: path.join(out, 'Portfolios mobile.png') });
  if (await page.evaluate(() => document.documentElement.scrollWidth > innerWidth + 1)) throw Error('Index mobile overflow');
  for (const [slug, n] of [['ftmo', 14], ['current14-orb05', 15], ['orbs-only', 5], ['full-eas', 37]]) {
    await page.goto(origin + '/portfolios/' + slug, { waitUntil: 'networkidle' });
    if (await page.locator('[data-member]').count() !== n) throw Error('Member count ' + slug);
    if (await page.locator('#history .pf-chart svg path').count() !== 1) throw Error('Chart absent ' + slug);
    if (await page.locator('#rules .pf-rule').count() < 4) throw Error('Risk rules absent ' + slug);
    await page.locator('[data-member]').first().locator('details').evaluate(e => e.open = true);
    if (await page.evaluate(() => document.documentElement.scrollWidth > innerWidth + 1)) throw Error('Detail mobile overflow ' + slug);
  }
  await page.goto(origin + '/portfolios/current14-orb05', { waitUntil: 'networkidle' });
  await page.locator('#rules').screenshot({ path: path.join(out, 'Portfolio risk mobile.png') });
  await page.setViewportSize({ width: 1600, height: 1100 });
  await page.locator('#rules').screenshot({ path: path.join(out, 'Portfolio risk desktop.png') });
  for (const slug of ['ftmo', 'current14-orb05', 'orbs-only', 'full-eas']) {
    await page.goto(origin + '/portfolios/' + slug, { waitUntil: 'networkidle' });
    await page.evaluate(() => window.portfolioNoReloadMarker = 123);
    for (const period of ['3m','6m', '3y', '5y', '1y']) {
      await page.locator(`#history a[data-period="${period}"]`).click();
      await page.locator(`#history [data-loaded-period="${period}"]`).waitFor();
      const data = await (await page.request.get(origin + `/api/portfolios/${slug}?period=${period}`)).json();
      if (!data.available) throw Error('Missing requested portfolio history ' + slug + period);
      await checkClosedDD(data.stats);
      const count = await page.locator('#history [data-metric="trades"]').innerText();
      if (count !== (data.available ? String(data.stats.trades) : '—')) throw Error('Period trade count mismatch ' + slug + period);
      if (await page.evaluate(() => window.portfolioNoReloadMarker) !== 123) throw Error('Unexpected period page reload');
      if (!data.available && await page.locator('#history .pf-chart').count()) throw Error('Unavailable period retained old curve');
      if (slug==='full-eas') {
        if(data.member_coverage.tested!==36 || data.member_coverage.total!==37 || data.missing_members.join(',')!=='gold-news-v9-direction')throw Error('Full basket missing coverage disclosure');
        const scope=(await page.locator('#history').innerText()).toLowerCase();
        if(!scope.includes('not a native simultaneous shared-margin portfolio'))throw Error('Native/partial evidence disclosure missing');
      }
    }
  }
  await page.goto(origin + '/portfolios', {waitUntil:'networkidle'});
  await page.locator('[data-global-periods] [data-period="3m"]').click();
  await page.waitForFunction(() => document.querySelectorAll('[data-loaded-period="3m"]').length===4);
  await page.locator('[data-portfolio="ftmo"] [data-period="6m"]').click();
  await page.locator('[data-portfolio="ftmo"] [data-loaded-period="6m"]').waitFor();
  if (await page.locator('[data-loaded-period="3m"]').count() !== 3) throw Error('Independent card filter changed other cards');
  // Rapid requests must not let a late response replace a newer selected range.
  await page.evaluate(() => { const card=document.querySelector('[data-portfolio="ftmo"]'); card.querySelector('[data-period="5y"]').click(); card.querySelector('[data-period="1y"]').click(); });
  await page.locator('[data-portfolio="ftmo"] [data-loaded-period="1y"]').waitFor();
  await page.waitForLoadState('networkidle');
  if (!(await page.locator('[data-portfolio="ftmo"] [data-loaded-period]').getAttribute('data-loaded-period')==='1y')) throw Error('Late response race');
  await page.goto(origin + '/portfolios/orbs-only', {waitUntil:'networkidle'});
  await page.locator('#history select[name="risk_mode"]').selectOption('fixed');
  await page.locator('#history [data-risk-mode="fixed"]').waitFor();
  await page.locator('#history input[name="risk_value"]').fill('100');
  await page.locator('#history button[type="submit"]').click();
  await page.locator('#history [data-risk-value="100.0"]').waitFor();
  let data=await (await page.request.get(origin+'/api/portfolios/orbs-only?period=1y&risk_mode=fixed&risk_value=100')).json();
  if((await page.locator('#history [data-metric="return_pct"]').innerText())!==`+${data.stats.return_pct.toFixed(2)}%`)throw Error('Fixed risk UI mismatch');
  await page.locator('#history [data-period="3m"]').click();
  await page.locator('#history [data-loaded-period="3m"][data-risk-value="100.0"]').waitFor();
  if(new URL(page.url()).searchParams.getAll('period').length!==1)throw Error('Duplicate period with risk query');
  data=await (await page.request.get(origin+'/api/portfolios/orbs-only?period=3m&risk_mode=fixed&risk_value=100')).json();
  if(await page.locator('#history [data-metric="trades"]').innerText()!==String(data.stats.trades))throw Error('Risk period not matched');
  await page.locator('#history select[name="risk_mode"]').selectOption('percent');
  await page.locator('#history [data-risk-mode="percent"]').waitFor();
  await page.locator('#history select[name="daily_limit_mode"]').selectOption('fixed');
  await page.locator('#history [data-daily-limit-mode="fixed"]').waitFor();
  if(await page.locator('#history [data-metric="max_daily_equity_drawdown_pct"]').count())throw Error('Unavailable floating DD tile retained');
  await page.locator('#history input[name="daily_limit_value"]').fill('50');
  await page.locator('#history button[type="submit"]').click();
  await page.waitForFunction(()=>!document.querySelector('#history').hasAttribute('aria-busy'));
  data=await (await page.request.get(origin+'/api/portfolios/orbs-only?period=3m&risk_mode=percent&risk_value=.5&daily_limit_mode=fixed&daily_limit_value=50')).json();
  if(await page.locator('#history [data-metric="trades"]').innerText()!==String(data.stats.trades))throw Error('Daily guard UI mismatch');
  await checkClosedDD(data.stats);
  await page.setViewportSize({width:1600,height:1250});
  await page.locator('#history').screenshot({path:path.join(out,'Calculator desktop.png')});
  await page.setViewportSize({width:390,height:844});
  await page.locator('#history').screenshot({path:path.join(out,'Calculator mobile.png')});
  if(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth+1))throw Error('Calculator mobile overflow');
  await page.locator('#history [data-reset-risk]').click();
  await page.locator('#history [data-risk-mode="recorded"]').waitFor();
  if(new URL(page.url()).searchParams.has('risk_mode'))throw Error('Risk reset left stale URL');
  // Inline calculator is also available independently on catalogue cards.
  await page.goto(origin+'/portfolios?period=6m',{waitUntil:'networkidle'});
  const card=page.locator('[data-portfolio="current14-orb05"]');
  await card.locator('.pf-calculator').evaluate(e=>e.open=true);
  await card.locator('select[name="risk_mode"]').selectOption('percent');
  await card.locator('[data-loaded-period="6m"][data-risk-mode="percent"]').waitFor();
  const unchanged=await page.locator('[data-risk-mode="recorded"]').count();
  if(unchanged!==3)throw Error('Card calculator changed another portfolio');
  // Exact owner-requested scenario, then a dynamic-% comparison with no reload.
  const requested='period=3m&risk_mode=fixed&risk_value=200&initial_balance=10000&daily_limit_mode=fixed&daily_limit_value=450';
  await page.goto(origin+'/portfolios/current14-orb05?'+requested,{waitUntil:'networkidle'});
  data=await (await page.request.get(origin+'/api/portfolios/current14-orb05?'+requested)).json();
  await checkClosedDD(data.stats);
  await page.setViewportSize({width:1200,height:900});
  await page.locator('#history .pf-daily-dd').screenshot({path:path.join(out,'Requested daily closed DD.png')});
  await page.locator('#history select[name="risk_mode"]').selectOption('percent');
  await page.locator('#history [data-risk-mode="percent"]').waitFor();
  await page.locator('#history input[name="risk_value"]').fill('2');
  await page.locator('#history button[type="submit"]').click();
  await page.locator('#history [data-risk-mode="percent"][data-risk-value="2.0"]').waitFor();
  data=await (await page.request.get(origin+'/api/portfolios/current14-orb05?period=3m&risk_mode=percent&risk_value=2&initial_balance=10000&daily_limit_mode=fixed&daily_limit_value=450')).json();
  await checkClosedDD(data.stats);
  await page.goto(origin + '/eas?period=1y', { waitUntil: 'networkidle' });
  if (await page.locator('.product-card').count() !== 37) throw Error('Global EA catalogue changed');
  if (errors.length) throw Error(errors.join('\n'));
  fs.writeFileSync(path.join(out, 'UI QA.json'), JSON.stringify({ profiles: 4, counts: [14, 15, 5, 37], global_eas: 37, status_filters: true, history_periods: true, risk_calculator: true, daily_loss_limit:true, dynamic_closed_dd:true, floating_dd_tile_removed:true, mobile_overflow: false, page_errors: errors }, null, 2));
  await browser.close();
  console.log('Portfolio desktop/mobile, status filters, evidence periods and unchanged EA catalogue verified.');
})().catch(e => { console.error(e); process.exit(1); });

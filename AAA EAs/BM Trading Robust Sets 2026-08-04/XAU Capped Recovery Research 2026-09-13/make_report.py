from pathlib import Path
from collections import Counter
import csv,json
ROOT=Path(__file__).resolve().parent
def load(p):return json.loads(p.read_text())
def usd(x):return ('-' if x<0 else '')+f'${abs(x):,.2f}'
def pf(x):return 'n/a' if x is None else f'{x:.3f}'
def percent(x):return f'{x:.2f}%'
def table(headers,rows):
    return '\n'.join(['| '+' | '.join(headers)+' |','|'+'|'.join(['---']*len(headers))+'|']+['| '+' | '.join(str(x) for x in r)+' |' for r in rows])
def params(r):
    p=r['parameters'];gap='1x completed H1 ATR(14)' if p['InpATRStep'] else f"${p['InpStep']}"
    return f"gap {gap}; net basket target ${p['InpBasketProfit']}; basket loss ${p['InpBasketLoss']}; daily loss ${p['InpDailyLoss']}; daily profit cap ${p['InpDailyProfit']}; lot {p['InpLot']}; multiplier {p['InpMultiplier']}; maximum {p['InpMaxLegs']} legs"

def main():
    baseline=load(ROOT/'baseline.json');selection=load(ROOT/'selection.json');final=load(ROOT/'final.json');diagnostics=load(ROOT/'diagnostics.json')
    verification=load(ROOT/'verification.json');checks={r['tag']:r for r in verification['results']}
    by_base={r['tag'].split('-')[1]:r for r in baseline};by_selected={r['tag'].split('-')[1]:r for r in final if r['tag'].startswith('selected-') and not ('slow' in r['tag'] or 'margin' in r['tag'])}
    chosen=selection['selected'];later=by_selected['later'];recent=by_selected['6m']
    dev_chosen=next(r for r in selection['development'] if r['parameters']==chosen['parameters'])
    robust=all(r['net_profit']>0 and (r['net_pf'] or 0)>1.1 and r['max_equity_dd_pct']<20 and not r['insolvent_at'] for r in (dev_chosen,chosen,later,recent))
    # This conservative research gate is not a guarantee of live profitability.
    verdict='RESEARCH CANDIDATE ONLY — forward demo still required' if robust else 'NOT APPROVED FOR DEPLOYMENT'
    out=['# Gold capped recovery — optimization and validation results','',f'## Verdict: {verdict}','',
         'Four raw starts previously reached insolvency. The capped alternative limits exposure and introduces protective exits, but survival alone does not establish a profitable strategy. No live trades, deployment, website/BAT changes or Git push were made.',
         '', '## Tested settings','', '**Initial candidate:** '+params(baseline[0])+'.', '', '**Selected by the declared development/validation ranking:** '+params(chosen)+'.',
         '', 'Dollar risk limits are fixed, not compounded percentages. $60/$90 are initially 2%/3% of $3,000; those percentages rise if the balance falls. Additions tighten a common protective stop and are rejected if risk distance or margin is insufficient. Targets and losses include loaded commission/swap; stop fills can overshoot.',
         '', '## Side-by-side standard windows','', 'Each row starts with a fresh $3,000, ends 2026-09-05 exclusive unless it fails earlier, and uses native MT5 model 4. These windows overlap; do not add their profits together or call every window out-of-sample.', '']
    comparison=[]
    for period in ('6m','1y','3y','5y'):
        a,b=by_base[period],by_selected[period]
        comparison.append([period,usd(a['net_profit']),percent(a['return_pct']),percent(a['max_equity_dd_pct']),usd(b['net_profit']),percent(b['return_pct']),percent(b['max_equity_dd_pct'])])
    out+=[table(['Window','Initial capped net','Return','Equity DD','Selected capped net','Return','Equity DD'],comparison),'','### Selected version: full statistics','']
    rows=[]
    for period in ('6m','1y','3y','5y'):
        r=by_selected[period]
        rows.append([period,usd(r['final_balance']),r['trades'],percent(r['net_win_rate']),pf(r['net_pf']),r['basket_count'],percent(r['basket_win_rate']),usd(r['worst_basket']),r['first_flat_6000'] or 'Not reached',r['insolvent_at'] or ('Native SO' if r['native_stopout'] else 'No')])
    out += [table(['Window','Final balance','Positions','Net position WR','Net PF','Baskets','Basket WR','Worst basket','$6,000 first reached','Insolvency'],rows),'',
            'Individual position win rates can be lower than basket win rates because an averaged basket may close one losing position together with profitable additions. All displayed win rates/PF are recomputed after recorded fees. Positions closed at the testing boundary are included, and boundary closure is not an ordinary strategy signal.',
            '', '### Costs and actual loss-limit overshoot','']
    rows=[]
    for period in ('6m','1y','3y','5y'):
        r=by_selected[period];v=checks[r['tag']]
        rows.append([period,usd(r['commission']),usd(r['swap']),r['max_lots'],r['daily_loss_locks'],r['daily_profit_locks'],v['observed_stop_overshoots'],usd(v['largest_stop_overshoot']),usd(v['fixed_path_cost_stress_net'])])
    out += [table(['Window','Commission','Swap','Max lots','Daily loss locks','Daily profit locks','Basket overshoots','Largest overshoot','Fixed-path cost stress net'],rows),'',
            'Fixed-path stress subtracts one additional observed entry spread, another copy of commission and negative swap, and $0.50 per ounce adverse execution at BOTH entry and exit. It preserves the recorded trades: it is a cost sensitivity calculation, not a native strategy rerun, and it does not reproduce earlier risk limits or a changed trading path.',
            '', '## Chronological selection and later validation','',
            'Development: 2021-09-05 to 2023-09-05 (12 cases). Validation: 2023-09-05 to 2024-09-05 (top 3). The final choice was frozen before the later 2024-09-05 to 2026-09-05 check. Ranking prefers non-insolvent, profitable, sufficiently active cases, then net profit / (1 + maximum equity drawdown dollars). Repeated prior inspection means historical validation is not equivalent to unseen forward-demo evidence.', '']
    out += [table(['Segment','Net','Net PF','Equity DD','Baskets'],[[name,usd(r['net_profit']),pf(r['net_pf']),percent(r['max_equity_dd_pct']),r['basket_count']] for name,r in [('Selected: development',dev_chosen),('Selected: validation',chosen),('Selected: later check',later),('Selected: latest 6m',recent)]]),'',
            '### All development cases','',table(['Case','Net','Net PF','Equity DD','Baskets'],[[r['tag'],usd(r['net_profit']),pf(r['net_pf']),percent(r['max_equity_dd_pct']),r['basket_count']] for r in sorted(selection['development'],key=lambda x:x['net_profit'],reverse=True)]),'',
            '### Top-three validation','',table(['Case','Net','Net PF','Equity DD','Baskets'],[[r['tag'],usd(r['net_profit']),pf(r['net_pf']),percent(r['max_equity_dd_pct']),r['basket_count']] for r in selection['validation']]),'',
            '## One-at-a-time diagnostics','', 'These change one setting relative to the frozen selected case. They were not used to replace that case after seeing the later check.', '',
            table(['Variant / segment','Net','Net PF','Equity DD','Worst basket'],[[r['tag'],usd(r['net_profit']),pf(r['net_pf']),percent(r['max_equity_dd_pct']),usd(r['worst_basket'])] for r in diagnostics]),'',
            '## Native execution and margin stress','',table(['Run','Net','Net PF','Equity DD','Worst basket'],[[r['tag'],usd(r['net_profit']),pf(r['net_pf']),percent(r['max_equity_dd_pct']),usd(r['worst_basket'])] for r in final if 'slow' in r['tag'] or 'margin' in r['tag']]),'',
            'The slow run uses 1,000 ms fixed delay on EA trade requests and stop modifications, not an artificial delay on broker-side SL/TP triggering. It recorded 12 failed stop updates (price moved or the position had already closed); the verified fail-safe flattened those baskets and did not add more exposure. The ordinary 1 ms runs had no such failures. The margin stress uses a conservative pre-entry 1:200 leverage cap; native account leverage remains 1:2000. It is not a reconstruction of historical news-margin schedules. [MetaQuotes execution-delay rules](https://www.metatrader5.com/en/terminal/help/algotrading/strategy_optimization).','',
            '## Reliability and scope','',
            '- Real ticks start on 2026-01-01 in the connected broker history. Earlier periods use generated ticks. The latest six-month run is the most directly supported real-tick comparison, not a five-year real-tick guarantee.',
            '- Current native fees and virtual equity-dependent leverage tiers are used; historical fee, swap, liquidity and high-margin changes are not fully reconstructed. [Exness leverage rules](https://get.exness.help/hc/en-us/articles/360014529380-Leverage).',
            '- Every-tick equity is monitored; a nonpositive reading ends the test. Native protective SLs are also attached. We do not allow the post-insolvency recoveries found in the original raw test to count as survival.',
            '- Neither win rate nor the daily profit cap guarantees income. The account can suffer a large cumulative drawdown through repeated limited losses.',
            '- No rolling-start probability or cash-withdrawal result is claimed unless a separate result file documents that exact simulation.',
            f"- {verification['unit_tests']} risk-arithmetic tests passed; {sum(not r.get('reused_from') for r in verification['results'])} unique native runs were independently reconciled against their position/deal ledgers. The batch core was mechanically verified against the single-run source. When the selected preset exactly matches the initial candidate, its four standard-window results are reused, not counted as new tests.",
            '', '## Files','', '[Frozen rules and protocol](RULES.md) · [Selection](selection.json) · [Full result data](final.json) · [Verification](verification.json)', '']
    for period in ('6m','1y','3y','5y'):
        r=by_selected[period];out.append(f"- [{period} native report, including every deal](Backtest%20Reports/{r['tag']}.htm)")
    (ROOT/'CAPPED GOLD RESULTS.md').write_text('\n'.join(out)+'\n',encoding='utf-8')
    (ROOT/'verdict.json').write_text(json.dumps({'verdict':verdict,'selected_parameters':chosen['parameters'],'baseline':baseline,'selected':final,'development_and_validation_positive':dev_chosen['net_profit']>0 and chosen['net_profit']>0},indent=2),encoding='utf-8')
    print(json.dumps({'verdict':verdict,'selected':params(chosen),'standard_results':comparison},indent=2))

if __name__=='__main__':main()

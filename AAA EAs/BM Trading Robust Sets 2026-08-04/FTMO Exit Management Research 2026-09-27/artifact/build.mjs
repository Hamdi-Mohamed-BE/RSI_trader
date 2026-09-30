import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {Workbook,SpreadsheetFile} from '@oai/artifact-tool';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const out=path.join(root,'outputs','exit-management-20260927');
await fs.mkdir(out,{recursive:true});
const data=JSON.parse(await fs.readFile(path.join(root,'RESULTS.json'),'utf8'));
const tab=JSON.parse(await fs.readFile(path.join(root,'TABLES.json'),'utf8'));
const wb=Workbook.create();
const native=wb.worksheets.add('Native'),portfolio=wb.worksheets.add('Portfolio'),funding=wb.worksheets.add('Funding'),notes=wb.worksheets.add('Notes');
const usd='"$"#,##0.00;[Red]("$"#,##0.00);"$"0.00';
function table(sh,title,subtitle,headers,rows,widths){
 const end=String.fromCharCode(64+headers.length),last=rows.length+4;
 sh.showGridLines=false;
 sh.getRange(`A1:${end}${last}`).format.font={name:'Arial',size:11,color:'#172033'};
 sh.getRange('A1').values=[[title]];sh.getRange('A1').format.font={name:'Arial',size:15,bold:true};
 sh.getRange('A2').values=[[subtitle]];sh.getRange('A2').format.font={italic:true,color:'#536174'};
 sh.getRange(`A4:${end}4`).values=[headers];sh.getRange(`A5:${end}${last}`).values=rows;
 sh.getRange(`A4:${end}4`).format={fill:'#25334B',font:{name:'Arial',bold:true,color:'#FFFFFF'},wrapText:true,rowHeight:42};
 sh.getRange(`A5:${end}${last}`).format.rowHeight=32;
 widths.forEach((w,i)=>{const col=String.fromCharCode(65+i);sh.getRange(`${col}1:${col}${last}`).format.columnWidth=w;});
 sh.getRange(`A5:B${last}`).format.wrapText=true;
 sh.getRange(`C5:${end}${last}`).format.horizontalAlignment='right';
 sh.freezePanes.freezeRows(4);
 return last;
}
const nativeRows=tab.native.map(r=>[r.ea,r.exit,r.trades,r.trades_per_week,r.net_usd,null,r.win_rate_pct/100,r.profit_factor,r.native_equity_dd_pct/100,r.max_win_streak,r.max_loss_streak]);
const nr=table(native,'Native MT5 exit tests','2 March–30 August 2026. Independent source sizing; equity DD from MT5.',
 ['EA','Exit','Trades','Trades / week','Net USD','Return','Win rate','Profit factor','Equity DD','Max wins','Max losses'],nativeRows,[35,29,10,13,16,12,12,12,12,11,11]);
native.getRange(`E5:E${nr}`).setNumberFormat(usd);native.getRange(`F5:G${nr}`).setNumberFormat('0.00%');native.getRange(`I5:I${nr}`).setNumberFormat('0.00%');native.getRange(`D5:D${nr}`).setNumberFormat('0.0');native.getRange(`H5:H${nr}`).setNumberFormat('0.00');
native.getRange(`F5:F${nr}`).formulas=nativeRows.map((_,i)=>[`=E${i+5}/'Notes'!$B$6`]);
const pr=table(portfolio,'Shared-account historical results','4 March–30 August 2026. DD reserve is modeled, not actual combined tick equity.',
 ['Portfolio','Costs','Trades','Net USD','Return','Win rate','Profit factor','Closed DD','Reserve DD','Worst day USD','Max wins','Max losses'],
 tab.portfolio.map(r=>[r.portfolio,r.stress?'Stress':'Reference',r.trades,r.net_usd,null,r.win_rate_pct/100,r.profit_factor,r.closed_dd_pct/100,r.stop_reserve_dd_pct/100,r.worst_modeled_day_usd,r.max_win_streak,r.max_loss_streak]),[44,13,10,16,12,12,12,12,12,16,11,11]);
portfolio.getRange(`D5:D${pr}`).setNumberFormat(usd);portfolio.getRange(`J5:J${pr}`).setNumberFormat(usd);portfolio.getRange(`E5:F${pr}`).setNumberFormat('0.00%');portfolio.getRange(`G5:G${pr}`).setNumberFormat('0.00');portfolio.getRange(`H5:I${pr}`).setNumberFormat('0.00%');
portfolio.getRange(`E5:E${pr}`).formulas=tab.portfolio.map((_,i)=>[`=D${i+5}/'Notes'!$B$6`]);
const ordered=[...data.cases].sort((a,b)=>(a.stress-b.stress)||a.name.localeCompare(b.name));
const fr=table(funding,'Conditional FTMO outcomes','1,000 joint-week paths per row. Fitted-history scenarios, not validated forecasts.',
 ['Portfolio','Costs','Paid 60d','Paid 120d','Paid 180d','Funded 180d','Breach 180d','Funded median days','Paid median days'],
 ordered.map(r=>{const h=Object.fromEntries(r.summary.horizons.map(v=>[v.days,v]));const t=r.summary.timing;return [r.name,r.stress?'Stress':'Reference',h[60].payout_pct/100,h[120].payout_pct/100,h[180].payout_pct/100,h[180].funded_pct/100,h[180].breach_before_first_reward_pct/100,t.funded_days_from_purchase.median,t.payout_days_from_purchase.median];}),[44,13,13,13,13,14,14,18,18]);
funding.getRange(`C5:G${fr}`).setNumberFormat('0.0%');funding.getRange(`H5:I${fr}`).setNumberFormat('0.0');
notes.showGridLines=false;notes.getRange('A1:B23').format.font={name:'Arial',size:11,color:'#172033'};notes.getRange('A1').values=[['Scope and assumptions']];notes.getRange('A1').format.font={name:'Arial',size:15,bold:true};
const nrows=[
 ['Study','FTMO exit-management research, 27 September 2026. No deployment.'],
 ['Basket','Gold Value Area, XAU news, XAG news, Nasdaq Overnight, EMA3 Full Safe, ORB Volume Profile 0.75R.'],
 ['Initial capital USD',10000],
 ['Ordinary risk USD',500/7],['News risk per side USD',10],
 ['Native source','24 MT5 real-tick runs, isolated Exness tester, 150 ms delay; original per-EA sizing.'],
 ['Portfolio model','Strict down-rounded lots; $300 daily admission budget; $225 aggregate risk; $150 metals/symbol risk; $9,200 buffer.'],
 ['FTMO model','2-Step Swing: +10%, +5%, four entry days/phase, 5% daily limit, 10% static loss limit, Prague reset.'],
 ['Margin assumption','1:15 for metals and Nasdaq; 80% maximum reserved margin; not verified against a current FTMO server.'],
 ['Stress','Native fills plus commission floors, 10% gross profit haircut/loss expansion, extra price costs and adverse swap reserve.'],
 ['Monte Carlo','26 joint source weeks, 1,000 matched paths per portfolio/cost case, seed 20260926.'],
 ['Time assumptions','2 business days between phases, 5 until funded; reward after 14 calendar days while flat; 4 business days for payment; 80% share.'],
 ['Drawdown limitation','Reserve DD is not native combined floating equity. Stop gaps and disqualification risk are not bounded by the model.'],
 ['Probability limitation','Previously examined history and fitted news presets; no independent forecast claim. Zero modeled breaches does not mean no real risk.'],
 ['Sources','RESULTS.json, TABLES.json, REPORT.md and retained native reports/journals in this study.'],
 ['FTMO comparison','https://ftmo.com/en/comparison-table/'],
 ['Swing rules','https://ftmo.com/en/faq/ftmo-swing-account-type/'],
 ['Forbidden practices','https://ftmo.com/en/forbidden-trading-practices/'],
 ['News eligibility','Swing permits news generally, but this pre-news gap/straddle implementation needs FTMO clarification before deployment.'],
 ['Exit definitions','A current; B all .75R; C all .5R; D non-news .75R; E Gold/ORB profile, others ATR; F E + protection; G non-news ATR; H A + protection.']
];
notes.getRange('A4:B23').values=nrows;notes.getRange('A1:A23').format.columnWidth=26;notes.getRange('B1:B23').format.columnWidth=112;notes.getRange('A4:B23').format.wrapText=true;notes.getRange('A4:B23').format.rowHeight=44;notes.getRange('B6:B8').setNumberFormat(usd);
for(let i=0;i<tab.native.length;i++){const got=native.getRange(`E${i+5}`).values[0][0];if(Math.abs(got-tab.native[i].net_usd)>1e-9)throw Error('Native export mismatch');}
for(let i=0;i<tab.portfolio.length;i++){const got=portfolio.getRange(`D${i+5}`).values[0][0];if(Math.abs(got-tab.portfolio[i].net_usd)>1e-9)throw Error('Portfolio export mismatch');}
console.log((await wb.inspect({kind:'table',range:'Portfolio!A4:L8',include:'values,formulas',tableMaxRows:5,tableMaxCols:12,maxChars:3500})).ndjson);
console.log((await wb.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|#NUM!|#NULL!|#SPILL!|#CALC!',options:{useRegex:true,maxResults:20},summary:'Formula error scan'})).ndjson);
for(const [name,end] of [['Native',`K${nr}`],['Portfolio',`L${pr}`],['Funding',`I${fr}`],['Notes','B23']]){const blob=await wb.render({sheetName:name,range:`A1:${end}`,scale:1,format:'png'});await fs.writeFile(path.join(out,name+'.png'),new Uint8Array(await blob.arrayBuffer()));}
const result=await SpreadsheetFile.exportXlsx(wb);await result.save(path.join(out,'FTMO Exit Comparison.xlsx'));
console.log('Created FTMO Exit Comparison.xlsx with reconciled values and four rendered sheets.');

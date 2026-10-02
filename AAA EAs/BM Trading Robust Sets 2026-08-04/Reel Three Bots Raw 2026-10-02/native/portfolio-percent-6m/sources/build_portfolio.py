"""Mechanical class adapter: preserve frozen single-bot rules and their source hashes."""
from pathlib import Path
import hashlib,re
ROOT=Path(__file__).resolve().parent
source=(ROOT/'EA/ReelRules.mqh').read_text()
expected='0a93ec07e40adf8deac1e20ee22e64e24a2bccf508e53ef0e8466baa406d0c4e'
assert hashlib.sha256((ROOT/'EA/ReelRules.mqh').read_bytes()).hexdigest()==expected
inputs=source[source.index('input double'):source.index('CTrade trade;')].replace('input ','')
body=source[source.index('CTrade trade;'):source.index('struct Row')]
deinit=source[source.index('void OnDeinit'):]
body=body.replace('_Symbol','m_symbol').replace('_Digits','m_digits')
trace='FolderCreate("ReelThree20261002",FILE_COMMON);traceFile=FileOpen("ReelThree20261002\\\\"+InpTag+"-equity.csv",FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON,\',\');if(traceFile==INVALID_HANDLE)return INIT_FAILED;'
assert trace in body
body=body.replace(trace,'')
record='datetime bar=now-now%300;if(bar!=traceBar&&now>=InpTradeFrom){traceBar=bar;FileWrite(traceFile,(long)now,AccountInfoDouble(ACCOUNT_BALANCE),AccountInfoDouble(ACCOUNT_EQUITY));}'
assert record in body
body=body.replace(record,'').replace('int OnInit()','int Init()')
initializers=[]
def member(match):
    initializers.append(match.group(1)+'='+match.group(2)+';')
    return match.group(1)
pattern=r"(\w+)=(D'[^']*'|\"[^\"]*\"|true|false|INVALID_HANDLE|[0-9.]+)"
inputs=re.sub(pattern,member,inputs)
pos=body.index('double Price(')
body=re.sub(pattern,member,body[:pos])+body[pos:]
constructor='RRModule(){'+''.join(initializers)+'}\n'
config='''void Configure(int kind,string symbol,double risk,long magic,datetime start,int offset,bool seasonal,bool atrIncludes,int deviation){
 BOT=kind;m_symbol=symbol;m_digits=(int)SymbolInfoInteger(symbol,SYMBOL_DIGITS);
 InpFixedRiskUSD=risk;InpMagic=magic;InpTradeFrom=start;InpBrokerUtcOffsetHours=offset;
 InpSeasonalReferenceClock=seasonal;InpATRIncludesSignal=atrIncludes;InpMaximumDeviationPoints=deviation;
}
int PositionCount(){return CountPositions();}
'''
generated='#include <Trade/Trade.mqh>\n// Generated from frozen ReelRules.mqh; build_portfolio.py documents mechanical changes.\nclass RRModule {\npublic:\nstring m_symbol;int m_digits;int BOT;\n'+inputs+constructor+config+body+deinit+'\n};\n'
(ROOT/'EA/PortfolioModules.mqh').write_text(generated,encoding='utf-8')
print('Generated class adapter; original single-bot files unchanged.')

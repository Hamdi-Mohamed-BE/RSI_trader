"""Recover merge-damaged generated website JSON; preserve backup and regenerate news from approved native reports."""
import json,re,sys,zipfile
from pathlib import Path
from datetime import date
ROOT=Path(__file__).resolve().parent;P=ROOT.parent;STORE=P.parent/'EA store'
sys.path.insert(0,str(STORE))
from app.evidence_cache import write_json,CACHE_ROOT
from app.catalog import get_catalog,get_product
from app.news_evidence import news_payload_from_result
from tools.precompute_evidence_cache import independent_news_result,source_fingerprint,product_cache_path,product_trades_path,source_paths

def main():
    damaged=[]
    for f in (STORE/'data').rglob('*.json'):
        text=f.read_text(encoding='utf-8-sig')
        if not re.search(r'^<<<<<<< ',text,re.M):continue
        fixed=re.sub(r'^<<<<<<< [^\n]+\n(.*?)^=======\n.*?^>>>>>>> [^\n]+\n?',lambda m:m[1],text,flags=re.M|re.S)
        value=json.loads(fixed) # verify every candidate BEFORE replacing any file
        damaged.append((f,value))
    backup=ROOT/'verification/website-merge-backup.zip';backup.parent.mkdir(exist_ok=True)
    if damaged:
        assert not backup.exists(),'Backup already exists; investigate instead of overwriting'
        with zipfile.ZipFile(backup,'w',compression=zipfile.ZIP_DEFLATED) as z:
            for f,_ in damaged:z.write(f,str(f.relative_to(STORE)))
        for f,value in damaged:write_json(f,value)
    published=[]
    for slug in ('news-pulse-xau','news-pulse-xag','news-pulse-btc','news-pulse-eurusd'):
        product=get_product(slug);assert product
        for period in ('6m','1y','3y','5y'):
            start={'6m':date(2026,3,5),'1y':date(2025,9,5),'3y':date(2023,9,5),'5y':date(2021,9,5)}[period]
            result,report=independent_news_result(product,'standard',period,start,date(2026,9,5))
            payload=news_payload_from_result(result)
            write_json(product_cache_path(slug,'standard',period),payload)
            write_json(product_trades_path(slug,'standard',period),result['trades'])
            _,meta=source_paths(product,'standard',period)
            write_json(meta,source_fingerprint(product,'standard',start,date(2026,9,5)))
            published.append(dict(slug=slug,period=period,report_sha256=result['source_report_sha256'],trades=len(result['trades'])))
    write_json(ROOT/'website-repair.json',dict(damaged_files=[str(f.relative_to(STORE)) for f,_ in damaged],backup=str(backup),regenerated=published))
    get_catalog.cache_clear()
    print('Repaired',len(damaged),'generated JSON files; independently verified',len(published),'news windows.',flush=True)
if __name__=='__main__':main()

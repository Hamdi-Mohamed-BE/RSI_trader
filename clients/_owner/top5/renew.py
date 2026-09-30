"""OWNER ONLY. Explicitly renew expiry/account binding, without changing strategy logic."""
import argparse,json,re,hashlib,shutil,subprocess
from datetime import datetime,timezone,timedelta
from build import ROOT,CLIENT,TESTER,build,read,sha
from make_installer import main as make_installer

def logic_fingerprints(manifest):
    result={}
    for row in manifest['entries']:
        start=ROOT/'build'/row['expert'].replace('.ex5','.mq5');seen={}
        def walk(path):
            if path.name in seen:return
            text=read(path)
            if path==start:
                text=re.sub(r'^#define CLIENT_(?:ID|ISSUED|EXPIRES|BOUND_LOGIN|BOUND_SERVER) .*$', '',text,flags=re.M)
            seen[path.name]=hashlib.sha256(text.encode()).hexdigest()
            for name in re.findall(r'#include\s+"([^"]+)"',text):walk(path.parent/name)
        walk(start)
        seen['compiler']=sha(TESTER/'metaeditor64.exe')
        result[row['slug']]=hashlib.sha256(json.dumps(seen,sort_keys=True).encode()).hexdigest()
    return result

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--days',type=int,required=True);ap.add_argument('--login',type=int,default=0);ap.add_argument('--server',default='')
    a=ap.parse_args();assert 1<=a.days<=3660
    assert (not a.login and not a.server) or (a.login>0 and a.server)
    old=json.loads((ROOT/'manifest.json').read_text());before=logic_fingerprints(old)
    payload=json.loads((ROOT/'report-data.json').read_text())
    archive=ROOT/'renewal-archive'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');archive.mkdir(parents=True)
    for p in CLIENT.iterdir():
        assert p.is_file() and p.suffix.lower() in ('.bat','.ex5','.html');shutil.copy2(p,archive/p.name)
    for name in ('manifest.json','licence.json','report-data.json'):shutil.copy2(ROOT/name,archive/name)
    try:
        terms=old['licence'].copy();terms['expires_utc']=(datetime.now(timezone.utc)+timedelta(days=a.days)).replace(microsecond=0).isoformat()
        if a.login:terms.update(bound_login=a.login,bound_server=a.server)
        (ROOT/'licence.json').write_text(json.dumps(terms,indent=2))
        new=build()
        assert before==logic_fingerprints(new),'Trading logic changed; fresh native benchmarks required before delivery'
        assert [r['inputs'] for r in old['entries']]==[r['inputs'] for r in new['entries']]
        make_installer()
        payload['licence']=new['licence']
        for item,row in zip(payload['bots'],new['entries']):item['ex5_sha256']=row['ex5_sha256']
        payload['licenceEditionNote']='Licence-only renewal: charts retain the original dated backtests. Trading-logic fingerprints were verified unchanged; EX5 licence metadata/account binding changed. See evidence hashes in the embedded report data for the originally tested binaries.'
        template=(ROOT/'report.template.html').read_text(encoding='utf-8')
        (CLIENT/'Performance and Setup.html').write_text(template.replace('__DATA__',json.dumps(payload,separators=(',',':')).replace('<','\\u003c')),encoding='utf-8')
        (ROOT/'report-data.json').write_text(json.dumps(payload,indent=2))
        print('Renewed through '+terms['expires_utc']+'. Send ONLY the seven files in clients/top 5.')
    except Exception:
        for p in archive.iterdir():
            shutil.copy2(p,(ROOT if p.suffix=='.json' else CLIENT)/p.name)
        raise

if __name__=='__main__':main()

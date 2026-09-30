"""Copy existing website descriptions and client inputs; no imports of the site or tests."""
import ast,json,hashlib
from datetime import datetime,timezone
from build import ROOT,REPO,CLIENT

def main():
    source=REPO/'AAA EAs/EA store/app/catalog.py'
    raw=source.read_text(encoding='utf-8-sig')
    tree=ast.parse(raw)
    catalog=next(n.value for n in tree.body if isinstance(n,ast.AnnAssign) and isinstance(n.target,ast.Name) and n.target.id=='CORE_META')
    manifest=json.loads((ROOT/'manifest.json').read_text())
    wanted={r['label']:r for r in manifest['entries']}
    details={}
    keys=('strategy','tagline','description','session','logic_audit','logic_audit_note','logic','risk_note','limitations')
    for key,value in zip(catalog.keys,catalog.values):
        label=ast.literal_eval(key)
        if label not in wanted:continue
        meta=ast.literal_eval(value);row=wanted[label]
        details[row['slug']]={k:meta[k] for k in keys if k in meta}
        details[row['slug']]['inputs']=row['inputs']
    assert len(details)==5
    snapshot={'copied_utc':datetime.now(timezone.utc).isoformat(timespec='seconds'),'source':'Existing Calyx website catalogue','source_sha256':hashlib.sha256(raw.encode()).hexdigest(),'entries':details}
    (ROOT/'ea-details-cache.json').write_text(json.dumps(snapshot,indent=2),encoding='utf-8')
    payload=json.loads((ROOT/'report-data.json').read_text());payload['ea_details']=snapshot
    (ROOT/'report-data.json').write_text(json.dumps(payload,indent=2),encoding='utf-8')
    template=(ROOT/'report.template.html').read_text(encoding='utf-8')
    (CLIENT/'Performance and Setup.html').write_text(template.replace('__DATA__',json.dumps(payload,separators=(',',':')).replace('<','\\u003c')),encoding='utf-8')
    print('Copied five existing website breakdowns; cached performance datasets unchanged. No backtests run.')
if __name__=='__main__':main()

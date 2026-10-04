"""Read-only metadata/cost requests; NEVER downloads paid market data."""
from pathlib import Path
import json
import databento as db
root=Path(__file__).resolve().parent
env=root.parents[2]/'naw LTA/.env'
key=''
for line in env.read_text().splitlines():
 if line.strip().startswith('DATABENTO_API_KEY='):key=line.split('=',1)[1].strip().strip('"').strip("'")
result={'download_started':False,'credential_present':bool(key),'schema':'trades','symbol':'NQ.v.0','requested_start':'2021-10-02','requested_end':'2026-10-02'}
try:
 client=db.Historical(key)
 coverage=client.metadata.get_dataset_range(dataset='GLBX.MDP3')
 result['dataset_range']=coverage
 end=min('2026-10-02T00:00:00+00:00',coverage['schema']['trades']['end'])
 result['estimated_full_trade_history_cost_usd']=float(client.metadata.get_cost(dataset='GLBX.MDP3',symbols=['NQ.v.0'],stype_in='continuous',schema='trades',start='2021-10-02T00:00:00+00:00',end=end))
 result['status']='COST_CHECK_ONLY'
except Exception as e:
 # Do not export exception text, request URLs, headers or credentials.
 result['status']='METADATA_ACCESS_FAILED';result['exception_type']=type(e).__name__
(root/'NQ DATA ACCESS.json').write_text(json.dumps(result,indent=2,default=str),encoding='utf-8')
print(json.dumps(result,indent=2,default=str))

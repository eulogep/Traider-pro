import sys,os,json,tempfile,copy,gzip,hashlib,asyncio,sqlite3
from pathlib import Path
P=Path(__file__).parent;sys.path.insert(0,str(P/'repo/quant/tests'))
import pandas as pd
from fastapi.testclient import TestClient
from ai_trader_optimizer.api.app import create_app
from ai_trader_optimizer.backtest import BacktestConfig,run_backtest
from ai_trader_optimizer.storage import LabCatalog,CorruptRunError,ReproducibilityError
from ai_trader_optimizer.storage.integrity import result_fingerprint,check_consistency,canonical_json
from ai_trader_optimizer.services import run_and_store,default_config,reproduce,save_defaults,save_risk,resolve_risk_policy
from ai_trader_optimizer.strategies import load_catalog
from ai_trader_optimizer.data import import_csv,dataset_from_frame,synthetic_dataset
from ai_trader_optimizer.safety import DataKind
from conftest import scripted,make_dataset,flat_bar,base_config,make_bars
BASE='baseline.ema_trend_3bars@1.0.0'; spec=load_catalog().specs[BASE]
records=[]
def record(name,**values):
 records.append({'name':name,**values});print(json.dumps(records[-1],default=str),flush=True)
def lab():return LabCatalog(Path(tempfile.mkdtemp(prefix='lab-',dir=P)))
def client(cat):return TestClient(create_app(cat),base_url='http://localhost',headers={'X-ATO-Request':'1'},raise_server_exceptions=False)
def fixture():
 cat=lab();ds=synthetic_dataset(days=3);cat.save_dataset(ds);r=run_and_store(cat,ds.meta.dataset_id,spec,BacktestConfig());return cat,ds,r
# Original artefact mutation probes, with new required request headers only
cat,ds,res=fixture();cl=client(cat);d=cat.run_dir(res.run_id)
for name in ['trades.csv','decisions.csv','equity.csv.gz','metrics.json','manifest.json','integrity.json']:
 p=d/name;old=p.read_bytes();p.write_bytes(old+b'CORRUPTION')
 response=cl.get(f'/api/v1/backtests/{res.run_id}');rep=cl.post(f'/api/v1/backtests/{res.run_id}/reproduce')
 record('artifact_corruption',artifact=name,get=response.status_code,reproduce=rep.status_code,corrected=response.status_code==rep.status_code==409)
 p.write_bytes(old)
bad=copy.deepcopy(res);bad.metrics['net_pnl']=123456
try:cat.save_run(bad);record('original_overwrite',corrected=False)
except (ReproducibilityError,CorruptRunError):record('original_overwrite',corrected=True)
# Even when run detail refuses corrupted disk files, collection endpoint still responds with figures
p=d/'trades.csv';old=p.read_bytes();p.write_bytes(old+b'CORRUPTION')
record('corrupted_run_in_collection',detail=cl.get(f'/api/v1/backtests/{res.run_id}').status_code,collection=cl.get('/api/v1/backtests').status_code,summary=cl.get('/api/v1/backtests').json()[0])
p.write_bytes(old)
# SQLite cached metric corruption is not checked against run_digest
with cat._conn() as con:
 m=copy.deepcopy(res.metrics);m['net_pnl']=987654321
 con.execute('UPDATE runs SET metrics_json=? WHERE run_id=?',(json.dumps(m),res.run_id))
record('sqlite_metric_corruption',collection_pnl=cl.get('/api/v1/backtests').json()[0]['net_pnl'],detail_pnl=cl.get(f'/api/v1/backtests/{res.run_id}').json()['metrics']['net_pnl'],reproduction=cl.post(f'/api/v1/backtests/{res.run_id}/reproduce').json())
# An internally rehashed wrong fill is accepted by semantic validation on first publication.
cat2=lab();bad=copy.deepcopy(res);actual=float(bad.trades.iloc[0].exit_price);bad.trades.loc[0,'exit_price']=actual+100
bad.manifest['result_hash']=result_fingerprint(bad.trades,bad.decisions,bad.equity,bad.metrics)
try:
 cat2.save_run(bad);stored=cat2.load_run(bad.run_id)
 t=stored.trades.iloc[0];sign=1 if t.direction=='BUY' else -1
 independent=sign*(t.exit_price-t.entry_price)*t.lots*bad.manifest['config']['contract']['contract_size']-t.commission
 record('semantic_wrong_fill',accepted=True,declared_pnl=t.net_pnl,pnl_from_prices=independent,problems=check_consistency(bad.trades,bad.decisions,bad.equity,bad.metrics,bad.manifest))
except Exception as exc:record('semantic_wrong_fill',accepted=False,error=str(exc))
# Same engine/config id reused across server policy modes
cat,ds,r=fixture();os.environ['ATO_RISK_POLICY']='supervised';cl=client(cat)
resp=cl.post('/api/v1/backtests',json={'dataset_id':ds.meta.dataset_id,'strategy_key':BASE})
record('policy_id_reuse',status=resp.status_code,current_policy=cl.get('/api/v1/settings/risk-policy').json(),returned_policy=resp.json().get('manifest',{}).get('risk_policy'))
# Costs and schedules can be loosened even when server policy says enforced
cfg=BacktestConfig().model_dump(mode='json');cfg['costs']={'spread':0,'slippage':0,'commission_per_lot_per_side':0};cfg['trading_hours']={'timezone':'UTC','sessions':['00:00-23:59'],'weekdays':list(range(7))};cfg['initial_equity']=1e9
resp=cl.post('/api/v1/backtests',json={'dataset_id':ds.meta.dataset_id,'strategy_key':BASE,'config':cfg})
record('supervised_hypothesis_override',status=resp.status_code,costs=resp.json().get('manifest',{}).get('config',{}).get('costs'),enforced=resp.json().get('manifest',{}).get('risk_policy',{}).get('enforced'))
os.environ.pop('ATO_RISK_POLICY')
# exact original boundary, then several TFs with unaligned cut and long exit horizon
for tf,freq,secs in [('M1','min',60),('M5','5min',300),('M15','15min',900),('H1','h',3600)]:
 for offset in [0,secs/2]:
  bars=make_bars([flat_bar()]*12,times=pd.date_range('2026-09-07T12:00Z',periods=12,freq=freq));ds0=dataset_from_frame(bars,name='tf',symbol='XAUUSD',source_label='probe',kind=DataKind.SYNTHETIC)
  sp,st=scripted({1:(1,2,30),4:(-1,2,30),5:(1,2,30)})
  sp=sp.model_copy(update={'timeframes':sp.timeframes.model_copy(update={'execution':tf})});st.spec=sp
  cut=bars.timestamp.iloc[5]+pd.Timedelta(seconds=offset)
  isr=run_backtest(ds0,sp,base_config(trade_end=cut.isoformat()),strategy=st);oor=run_backtest(ds0,sp,base_config(trade_start=cut.isoformat()),strategy=st)
  end=pd.Timestamp(isr.manifest['evaluation_window']['last_evaluated_bar_close']);start=pd.Timestamp(oor.manifest['evaluation_window']['first_evaluated_bar_open'])
  assert end<=cut<=start
  record('boundary',tf=tf,offset=offset,is_end=end,oos_start=start,no_overlap=True)
# Invalid numeric inputs still rejected including oversized exponent
cat=lab();ds=synthetic_dataset(days=3);cat.save_dataset(ds);cl=client(cat)
for value in ['1e309','NaN','-1e309','"10000"','true']:
 body='{"dataset_id":"'+ds.meta.dataset_id+'","strategy_key":"'+BASE+'","config":{"initial_equity":'+value+'}}'
 response=cl.post('/api/v1/backtests',content=body,headers={'Content-Type':'application/json'})
 record('numeric_input',value=value,status=response.status_code,corrected=response.status_code==422)
# lowercase exact identity, immutable provenance, sub-second rejection, tiny price distinction
raw=make_bars([flat_bar()]*20).to_csv(index=False).encode();form={'name':'probe','symbol':'xauusd','source':'probe','kind':'synthetic'}
a=cl.post('/api/v1/datasets/import',files={'file':('neutral.csv',raw)},data=form);did=a.json()['dataset']['dataset_id'];loaded=cat.load_dataset(did)
b=cl.post('/api/v1/datasets/import',files={'file':('neutral.csv',raw)},data={**form,'symbol':'XAUUSD','kind':'historical'})
record('identity_and_provenance',lowercase_status=a.status_code,symbol=loaded.meta.symbol,conflict=b.status_code)
# Same-kind import response claims changed source/name even though persisted meta is immutable
b=cl.post('/api/v1/datasets/import',files={'file':('neutral.csv',raw)},data={**form,'name':'new name','source':'new source'})
record('import_response_vs_persisted',response_source=b.json()['dataset']['source'],persisted_source=cl.get('/api/v1/datasets/'+did).json()['source'])
# Upload line limit bypass with legal CR-only csv records
os.environ['ATO_MAX_ROWS']='10'
raw=make_bars([flat_bar()]*30).to_csv(index=False,lineterminator='\r').encode()
b=cl.post('/api/v1/datasets/import',files={'file':('carriage.csv',raw)},data={**form,'source':'CR'})
record('cr_line_limit',status=b.status_code,accepted_rows=b.json().get('dataset',{}).get('rows'));os.environ.pop('ATO_MAX_ROWS')
# Ordinary origin/host variants, no exemptions
for headers in [{'Host':'localhost.'},{'Host':'[::ffff:127.0.0.1]'}, {'Origin':'null'},{'Origin':'https://localhost.evil.example'},{'Origin':'https://evil.example'},{'Sec-Fetch-Site':'cross-site'}]:
 resp=cl.post('/api/v1/datasets/demo',json={},headers=headers);record('security_variant',headers=headers,status=resp.status_code)
# Errors midway through stream: reproduce body limit consumption independent of developer fixture
os.environ['ATO_MAX_JSON_KB']='1';app=create_app(cat);seen=0;messages=[]
async def receive():
 global seen
 seen+=1;return {'type':'http.request','body':b' '*300,'more_body':seen<20}
async def send(msg):messages.append(msg)
scope={'type':'http','method':'POST','path':'/api/v1/datasets/demo','query_string':b'','headers':[(b'host',b'localhost'),(b'x-ato-request',b'1'),(b'content-type',b'application/json')]}
asyncio.run(app(scope,receive,send));record('stream_limit',chunks_read=seen,chunks_offered=20,status=messages[0]['status']);os.environ.pop('ATO_MAX_JSON_KB')
# Raw source claims are not verified by catalog writer
cat=lab();rep,ds=import_csv(raw,name='raw',symbol='XAUUSD',source_label='probe',kind=DataKind.SYNTHETIC)
cat.save_dataset(ds,b'wrong raw bytes')
record('raw_hash_mismatch',claimed_sha=ds.meta.raw_sha256,actual_sha=hashlib.sha256((cat.root/'raw'/f'{ds.meta.raw_sha256}.csv').read_bytes()).hexdigest(),dataset_loads=cat.load_dataset(ds.meta.dataset_id).meta.dataset_id)
(P/'counter-evidence.json').write_text(json.dumps(records,indent=2,default=str))

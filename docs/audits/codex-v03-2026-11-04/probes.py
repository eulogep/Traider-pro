import os,sys,tempfile,json,copy
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent/'repo/quant/tests'))
import pandas as pd
from fastapi.testclient import TestClient
from ai_trader_optimizer.api.app import create_app
from ai_trader_optimizer.backtest import run_backtest,BacktestConfig
from ai_trader_optimizer.storage import LabCatalog
from ai_trader_optimizer.services import reproduce,save_risk
from ai_trader_optimizer.strategies import load_catalog
from ai_trader_optimizer.data import import_csv,dataset_from_frame,synthetic_dataset
from ai_trader_optimizer.safety import DataKind
from ai_trader_optimizer.data.models import fingerprint
from conftest import scripted,make_dataset,flat_bar,base_config,make_bars

def show(name,**v): print(json.dumps({'probe':name,**v},default=str))
root=Path(tempfile.mkdtemp(dir=Path(__file__).parent)); cat=LabCatalog(root); client=TestClient(create_app(cat),raise_server_exceptions=False)
spec=load_catalog().specs['baseline.ema_trend_3bars@1.0.0']; ds=synthetic_dataset(days=3);cat.save_dataset(ds)
r=run_backtest(ds,spec,BacktestConfig());cat.save_run(r)
# disk results modified: reproduce still compares manifest to newly computed result
p=cat.run_dir(r.run_id)/'metrics.json'; m=json.loads(p.read_text());m['net_pnl']=987654321;p.write_text(json.dumps(m))
show('tampered_metrics',served=client.get(f'/api/v1/backtests/{r.run_id}').json()['metrics']['net_pnl'],reproduce=client.post(f'/api/v1/backtests/{r.run_id}/reproduce').json())
r.equity.loc[:,'mtm_equity']=1;r.metrics['net_pnl']=123456
try:cat.save_run(r);show('overwrite_same_hash',accepted=True,served=cat.load_run(r.run_id).metrics['net_pnl'])
except Exception as e:show('overwrite_same_hash',error=str(e))
# synthetic data metadata can be relabelled, id identical
raw=ds.bars.to_csv(index=False).encode()
resp=client.post('/api/v1/datasets/import',files={'file':('prices.csv',raw,'text/csv')},data={'name':'relabel','symbol':'XAUUSD','source':'claimed broker','kind':'historical'})
show('relabel_dataset',status=resp.status_code,id_before=ds.meta.dataset_id,id_after=resp.json().get('dataset',{}).get('dataset_id'),kind_now=cat.dataset_meta(ds.meta.dataset_id).kind)
resp=client.post('/api/v1/datasets/import',files={'file':('prices.csv',raw,'text/csv')},data={'name':'lowercase','symbol':'xauusd','source':'test','kind':'synthetic'})
lowerid=resp.json().get('dataset',{}).get('dataset_id'); err=None
try:cat.load_dataset(lowerid)
except Exception as e:err=str(e)
show('lowercase_import',status=resp.status_code,load_error=err)
# saved risk profile ignored by supplied config
from ai_trader_optimizer.risk import RiskConfig
save_risk(cat,RiskConfig(max_trades_per_day=1))
for label,cfg in [('saved',None),('override',BacktestConfig(risk=RiskConfig(max_trades_per_day=100,max_losses_per_day=None,max_daily_loss_pct=100,max_drawdown_pct=100)).model_dump(mode='json'))]:
 resp=client.post('/api/v1/backtests',json={'dataset_id':ds.meta.dataset_id,'strategy_key':spec.key,'config':cfg})
 show('risk_'+label,status=resp.status_code,trades=resp.json().get('metrics',{}).get('trades'),configured_daily_cap=resp.json().get('manifest',{}).get('config',{}).get('risk',{}).get('max_trades_per_day'))
# gap already opened beyond target, later low touches stop
sp,st=scripted({0:(1,2,3)})
g=run_backtest(make_dataset([flat_bar(),flat_bar(),(105,106,97,99),flat_bar(99)]),sp,base_config(),strategy=st)
show('open_above_tp',trade=g.trades[['entry_price','stop_loss','take_profit','exit_reason','exit_price','net_pnl']].to_dict('records'))
# excursions extend after exit
sp,st=scripted({0:(1,2,3)})
g=run_backtest(make_dataset([flat_bar(),(100,1000,98,100),flat_bar()]),sp,base_config(),strategy=st)
show('post_exit_excursions',trade=g.trades[['exit_reason','mae_price','mfe_price','mfe_r']].to_dict('records'))
# subsecond validation and save/load
frame=make_bars([flat_bar()]*3);frame['timestamp']+=pd.Timedelta(milliseconds=500)
d=dataset_from_frame(frame,name='fractional',symbol='XAUUSD',source_label='test',kind=DataKind.SYNTHETIC);cat.save_dataset(d)
show('fractional_timestamp',before=d.bars.timestamp.iloc[0],after=cat.load_dataset(d.meta.dataset_id).bars.timestamp.iloc[0])
# financial precision collisions
f=make_bars([flat_bar()]*3);f2=f.copy();f2.loc[0,'close']+=1e-8
show('dataset_precision_collision',id1=fingerprint(f,'XAUUSD','M1','bid'),id2=fingerprint(f2,'XAUUSD','M1','bid'),different=not f.equals(f2))
# invalid timezone handler
cfg=BacktestConfig().model_dump(mode='json');cfg['risk']['day_timezone']='Not/AZone'
resp=client.post('/api/v1/backtests',json={'dataset_id':ds.meta.dataset_id,'strategy_key':spec.key,'config':cfg});show('bad_timezone',status=resp.status_code,body=resp.text)
# infinite configuration accepted at schema level
for path,change in [('initial_equity',{'initial_equity':float('inf')}),('costs',{'costs':{'spread':float('inf')}})]:
 try:cfg=BacktestConfig(**change);show('nonfinite_config',field=path,accepted=True)
 except Exception as e:show('nonfinite_config',field=path,error=str(e))
# exact same bytes, two provenance declarations
for kind in ['synthetic','historical']:
 resp=client.post('/api/v1/datasets/import',files={'file':('neutral.csv',raw,'text/csv')},data={'name':'neutral','symbol':'XAUUSD','source':kind,'kind':kind})
 show('mutable_provenance',kind=kind,status=resp.status_code,id=resp.json()['dataset']['dataset_id'])
# split at a bar open: both segments trade the same bar
from ai_trader_optimizer.ai.validation import chronological_split
bars=[flat_bar()]*11;bars[5]=(100,104,99.8,103)
d=make_dataset(bars);sp,st=scripted({4:(1,2,3)});cut=chronological_split(d.bars.timestamp.iloc[0],d.bars.timestamp.iloc[-1],.5)
for seg,cfg in [('IS',base_config(trade_end=cut.train_end.isoformat())),('OOS',base_config(trade_start=cut.test_start.isoformat()))]:
 rr=run_backtest(d,sp,cfg,strategy=st);show('split_overlap',segment=seg,cut=cut.train_end,trades=rr.trades[['entry_time','exit_time','net_pnl']].to_dict('records'))
# infinity can be sent in standard JSON as an overflowing finite-token exponent
payload=json.dumps({'dataset_id':ds.meta.dataset_id,'strategy_key':spec.key,'config':{'initial_equity':'REPLACE'}}).replace('"REPLACE"','1e309')
resp=client.post('/api/v1/backtests',content=payload,headers={'Content-Type':'application/json'});show('infinite_api',status=resp.status_code,metrics=resp.json().get('metrics'),equity=resp.json().get('manifest',{}).get('config',{}).get('initial_equity'))
# request consumed before application size limit is checked
import ai_trader_optimizer.api.app as apimod
seen={'bytes':0}; old=apimod.max_upload_bytes
async def observed(scope,receive,send):
 async def recv():
  msg=await receive();seen['bytes']+=len(msg.get('body',b''));return msg
 await client.app(scope,recv,send)
def limit():
 show('upload_before_limit',already_received=seen['bytes'],limit=1024);return 1024
apimod.max_upload_bytes=limit
big=TestClient(observed,raise_server_exceptions=False).post('/api/v1/datasets/import',files={'file':('big.csv',b'x'*(2*1024*1024),'text/csv')},data={'name':'test','symbol':'XAUUSD','source':'test','kind':'historical'})
show('upload_result',status=big.status_code);apimod.max_upload_bytes=old
resp=client.post('/api/v1/datasets/import',files={'file':('neutral.csv',raw,'text/csv')},data={'name':'from foreign origin','symbol':'XAUUSD','source':'test','kind':'historical'},headers={'Origin':'https://evil.example'})
show('cors_write',status=resp.status_code,allow_origin=resp.headers.get('access-control-allow-origin'))

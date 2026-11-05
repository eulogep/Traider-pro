import sys,os,json,tempfile,copy,hashlib,threading,concurrent.futures
from pathlib import Path
P=Path(__file__).parent;sys.path.insert(0,str(P/'repo/quant/tests'))
import pandas as pd
from fastapi.testclient import TestClient
from ai_trader_optimizer.storage import LabCatalog,CorruptRunError,RunNotFoundError
from ai_trader_optimizer.backtest import BacktestConfig,run_backtest
from ai_trader_optimizer.data import synthetic_dataset,dataset_from_frame
from ai_trader_optimizer.data.resample import resample_ohlc,align_higher_timeframe
from ai_trader_optimizer.strategies import load_catalog
from ai_trader_optimizer.safety import DataKind
from ai_trader_optimizer.services import run_and_store
from ai_trader_optimizer.backtest.codehash import code_fingerprint
from conftest import make_bars,make_dataset,base_config,flat_bar,scripted
results=[]
def out(name,**v):results.append({'name':name,**v});print(json.dumps(results[-1],default=str),flush=True)
# MTF availability and perturbation around boundary
f=make_bars([(100+i*.1,101+i*.1,99+i*.1,100+i*.1) for i in range(60)])
hi=resample_ohlc(f,'M1','M15');aligned=align_higher_timeframe(f,'M1',hi,['close'],prefix='h_')
assert aligned.h_close.iloc[:14].isna().all();assert aligned.h_available_at.iloc[14]==f.timestamp.iloc[14]+pd.Timedelta(minutes=1)
future=f.copy();future.loc[30:,'high']+=1000
alt=align_higher_timeframe(future,'M1',resample_ohlc(future,'M1','M15'),['high'],prefix='h_')
ref=align_higher_timeframe(f,'M1',hi,['high'],prefix='h_')
pd.testing.assert_frame_equal(ref.iloc[:30],alt.iloc[:30]);out('mtf_availability',pass_=True,first_context_bar=14,perturbed_future_from=30)
# Original exact B3 example with explicit money assertion
bars=[flat_bar()]*11;bars[5]=(100,104,99.8,103);sp,st=scripted({4:(1,2,3)});ds=make_dataset(bars)
a=run_backtest(ds,sp,base_config(trade_end='2026-09-07T12:05Z'),strategy=st);b=run_backtest(ds,sp,base_config(trade_start='2026-09-07T12:05Z'),strategy=st)
assert a.trades.empty and len(b.trades)==1 and abs(b.trades.iloc[0].net_pnl-31.79)<1e-9
out('original_B3',is_trades=len(a.trades),oos_trades=len(b.trades),oos_pnl=b.trades.iloc[0].net_pnl)
# Independent intermediate overflow injection: no run is published
sp,st=scripted({0:(1,2,30)});cfg=base_config();bad=make_dataset([flat_bar()]*3)
# Deliberately emulate an indicator/data calculation returning an infinite mark/exit in memory.
bad.bars.loc[2,'close']=float('inf')
try:run_backtest(bad,sp,cfg,strategy=st);out('intermediate_infinite_exit',refused=False)
except ValueError as e:out('intermediate_infinite_exit',refused=True,error=str(e))
# Publication interruption after atomic rename but before the SQLite insert
cat=LabCatalog(Path(tempfile.mkdtemp(dir=P)));ds=synthetic_dataset(days=3);cat.save_dataset(ds);spec=load_catalog().specs['baseline.ema_trend_3bars@1.0.0'];r=run_backtest(ds,spec,BacktestConfig())
orig=cat._index_run
def interrupted(*a,**k):raise OSError('injected post-rename failure')
cat._index_run=interrupted
try:cat.save_run(r)
except OSError:pass
readable=True
try:cat.load_run(r.run_id)
except RunNotFoundError:readable=False
out('post_rename_interruption',directory_present=(cat.root/'runs'/r.run_id).is_dir(),indexed_rows=len(cat.list_runs()),readable=readable)
cat._index_run=orig;cat.save_run(r);assert cat.load_run(r.run_id).manifest['result_hash']==r.manifest['result_hash'];out('post_rename_recovery',pass_=True)
# Concurrent new publication + continuous verified reads
other=run_backtest(ds,spec,BacktestConfig(strategy_params={'rr':2}));errors=[];missing=[];gate=threading.Event()
def writer():
 gate.wait();LabCatalog(cat.root).save_run(other)
def reader():
 gate.wait()
 for _ in range(10):
  try:LabCatalog(cat.root).load_run(other.run_id)
  except RunNotFoundError:missing.append(1)
  except Exception as e:errors.append(type(e).__name__+':'+str(e))
with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
 futures=[pool.submit(writer) for _ in range(4)]+[pool.submit(reader)];gate.set()
 for future in futures:future.result(timeout=60)
assert not errors;out('concurrent_writers_reader',writers=4,reads=10,not_yet_published=len(missing),partial_errors=errors)
# Code fingerprint misses new integrity/numeric/services code
h=code_fingerprint();package=P/'repo/quant/src/ai_trader_optimizer';path=package/'storage/integrity.py';old=path.read_bytes()
try:
 path.write_bytes(old.replace(b'def _close(a, b, tol=1e-9)',b'def _close(a, b, tol=1e-3)'));code_fingerprint.cache_clear();same=code_fingerprint()==h
 out('fingerprint_coverage',changed_semantic_module='storage/integrity.py consistency tolerance',hash_unchanged=same)
finally:path.write_bytes(old);code_fingerprint.cache_clear()
# Timestamp labels at END_OF_DATA
sp,st=scripted({0:(1,2,30)});x=run_backtest(make_dataset([flat_bar(),flat_bar(),(100,101,99.8,101)]),sp,base_config(),strategy=st)
out('close_timestamp',exit_time=x.trades.iloc[0].exit_time,last_bar_open=x.equity.timestamp.iloc[-1],actual_last_close=x.manifest['evaluation_window']['last_evaluated_bar_close'],exit_price=x.trades.iloc[0].exit_price)
# Guard/header without Origin remains deliberately usable for local non-browser clients
cl=TestClient(__import__('ai_trader_optimizer.api.app',fromlist=['create_app']).create_app(cat),base_url='http://localhost',headers={'X-ATO-Request':'1'})
out('no_origin_local_header',status=cl.post('/api/v1/datasets/demo',json={'days':3}).status_code)
(P/'extended-evidence.json').write_text(json.dumps(results,indent=2,default=str))

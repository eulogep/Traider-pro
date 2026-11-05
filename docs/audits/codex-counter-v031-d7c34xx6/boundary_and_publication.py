import sys,tempfile,json,threading,concurrent.futures,time
from pathlib import Path
P=Path(__file__).parent;sys.path.insert(0,str(P/'repo/quant/tests'))
import pandas as pd
from ai_trader_optimizer.ai.validation import chronological_split,walk_forward_splits
from ai_trader_optimizer.backtest import BacktestConfig,run_backtest
from ai_trader_optimizer.storage import LabCatalog,RunNotFoundError
from ai_trader_optimizer.data import synthetic_dataset
from ai_trader_optimizer.strategies import load_catalog
from conftest import make_dataset,scripted,base_config,flat_bar
records=[]
def out(name,**values):records.append({'name':name,**values});print(json.dumps(records[-1],default=str),flush=True)
bars=[flat_bar()]*11;bars[4]=(100,104,99.8,103);ds=make_dataset(bars);sp,st=scripted({3:(1,2,3)})
cut=chronological_split(ds.bars.timestamp.iloc[0],ds.bars.timestamp.iloc[-1],.5,embargo=pd.Timedelta(minutes=-1))
a=run_backtest(ds,sp,base_config(trade_end=cut.train_end.isoformat()),strategy=st);b=run_backtest(ds,sp,base_config(trade_start=cut.test_start.isoformat()),strategy=st)
out('negative_embargo_overlap',train_end=cut.train_end,test_start=cut.test_start,is_trades=a.trades[['entry_time','net_pnl']].to_dict('records'),oos_trades=b.trades[['entry_time','net_pnl']].to_dict('records'))
w=walk_forward_splits(pd.Timestamp('2026-09-07T12:00Z'),pd.Timestamp('2026-09-07T13:00Z'),pd.Timedelta(minutes=10),pd.Timedelta(minutes=5),embargo=pd.Timedelta(minutes=-1))
out('walk_forward_negative_embargo',folds=len(w),first_train_end=w[0].train_end,first_test_start=w[0].test_start)
# 4 writers with reader continuing through and after visibility
cat=LabCatalog(Path(tempfile.mkdtemp(dir=P)));ds=synthetic_dataset(days=3);cat.save_dataset(ds);r=run_backtest(ds,load_catalog().specs['baseline.ema_trend_3bars@1.0.0'],BacktestConfig())
gate=threading.Event();errors=[];counts={'missing':0,'verified':0}
def writer():gate.wait();LabCatalog(cat.root).save_run(r)
def reader():
 gate.wait();deadline=time.monotonic()+30
 while time.monotonic()<deadline and counts['verified']<2:
  try:
   rr=cat.load_run(r.run_id);assert rr.manifest['result_hash']==r.manifest['result_hash'];counts['verified']+=1
  except RunNotFoundError:counts['missing']+=1
  except Exception as exc:errors.append(type(exc).__name__+': '+str(exc));break
  time.sleep(.01)
with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
 futures=[pool.submit(writer) for _ in range(4)]+[pool.submit(reader)];gate.set()
 for f in futures:f.result(timeout=40)
assert not errors and counts['verified']>=2
out('concurrent_visibility',writers=4,**counts,partial_errors=errors)
(P/'boundary-publication-evidence.json').write_text(json.dumps(records,indent=2,default=str))

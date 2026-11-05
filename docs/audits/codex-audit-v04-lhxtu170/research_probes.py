import sys,os,json,tempfile,copy,hashlib
from pathlib import Path
P=Path(__file__).parent;sys.path.insert(0,str(P/'repo/quant/tests'))
import numpy as np
import pandas as pd
from fastapi.testclient import TestClient
from ai_trader_optimizer.data import synthetic_dataset
from ai_trader_optimizer.backtest import BacktestConfig,run_backtest
from ai_trader_optimizer.strategies import load_catalog,build_strategy
from ai_trader_optimizer.storage import LabCatalog
from ai_trader_optimizer.research import StudySettings,run_edge_study
from ai_trader_optimizer.research.labels import label_signals
from ai_trader_optimizer.research.features import bar_features,signal_features
from ai_trader_optimizer.research.study import _latest_opinion,load_study
from ai_trader_optimizer.research.stats import LogisticModel,brier
from ai_trader_optimizer.api.app import create_app
from conftest import make_dataset,flat_bar,scripted,base_config
records=[]
def out(name,**v):records.append({'name':name,**v});print(json.dumps(records[-1],default=str),flush=True);(P/'research-evidence.json').write_text(json.dumps(records,indent=2,default=str))
cat=LabCatalog(Path(tempfile.mkdtemp(prefix='study-',dir=P)));ds=synthetic_dataset(7,20);cat.save_dataset(ds);spec=load_catalog().specs['baseline.ema_trend_3bars@1.0.0'];cfg=BacktestConfig();sig=build_strategy(spec,{}).compute(ds.bars)
labels=label_signals(ds,spec,cfg,sig);engine=run_backtest(ds,spec,cfg)
start=labels.entry_time.astype('int64').to_numpy();end=labels.exit_time.astype('int64').to_numpy()+ds.bar_seconds*10**9
active=[];peak=0;overlap_pairs=0
for t,e in zip(start,end):
 active=[x for x in active if x>t];overlap_pairs+=len(active);active.append(e);peak=max(peak,len(active))
out('generation_and_overlap',seed=7,days=20,all_candidates=int((sig.signal!=0).sum()),labelled=len(labels),engine_trades=len(engine.trades),max_concurrent_labels=peak,overlapping_pairs=overlap_pairs,known_end_labels=int((labels.exit_time+pd.Timedelta(minutes=1)<=ds.bars.timestamp.iloc[-1]+pd.Timedelta(minutes=1)).sum()))
# Prefix causality on independent indices
for j in [1000,2000]:pd.testing.assert_series_equal(bar_features(ds.bars.iloc[:j+1]).iloc[-1],bar_features(ds.bars).iloc[j])
out('features_prefix',pass_=True,indices=[1000,2000])
s=run_edge_study(cat,ds.meta.dataset_id,spec,cfg,StudySettings(n_boot=200))
out('real_study',id=s['study_id'],verdict=s['result']['verdict'],signals=s['signals'],result={k:s['result'].get(k) for k in ['n_oos','n_taken','auc','brier','calibration']},latest=(s['final_model'] or {}).get('latest_signal'))
# Requested date window absent from identity and from labels
narrow=cfg.model_copy(update={'trade_start':ds.bars.timestamp.iloc[-5].isoformat(),'trade_end':(ds.bars.timestamp.iloc[-1]+pd.Timedelta(minutes=1)).isoformat()})
s2=run_edge_study(cat,ds.meta.dataset_id,spec,narrow,StudySettings(n_boot=200))
out('window_ignored',same_id=s2['study_id']==s['study_id'],requested_start=narrow.trade_start,n_labelled=s2['signals']['labelled'],max_signals_in_requested_window=5)
# Compare TIME_EXIT convention against label with long horizon
sp,st=scripted({0:(1,2,3)});dd=make_dataset([flat_bar(),flat_bar(),flat_bar(),(100,104,99.8,103),flat_bar(103),flat_bar(103)])
cc=base_config(max_bars_in_trade=1);rr=run_backtest(dd,sp,cc,strategy=st);ll=label_signals(dd,sp,cc,st.compute(dd.bars),horizon_bars=3)
out('time_exit_mismatch',engine=rr.trades[['net_pnl','r_multiple','exit_reason','exit_time']].to_dict('records'),labels=ll[['r','exit_reason','exit_time']].to_dict('records'))
# Same-bar SL labels record the open, while the outcome depends on that bar's future low.
out('label_availability',entries_exiting_same_open=int((labels.entry_time==labels.exit_time).sum()),first=labels[['entry_time','exit_time','exit_reason']].head(2).to_dict('records'))
# Model failure does not fail closed when no threshold was selected.
class BrokenModel:
 def predict_proba(self,X):return np.full(len(X),np.nan)
opinion=_latest_opinion(ds.bars,sig,cfg,BrokenModel(),None,spec.trading_hours,ds.bar_seconds)
out('nan_model_opinion',opinion=opinion)
# OOD has no detection/gate. Report largest transformed feature deviation under hypothetical model.
X=np.array([[0.,0.],[1.,1.],[-1.,-1.],[.5,-.5]])
m=LogisticModel().fit(X,np.array([0,1,0,1]));out('ood_prediction',input=[[1e9,-1e9]],probability=m.predict_proba(np.array([[1e9,-1e9]])).tolist(),has_ood_gate=hasattr(m,'ood'))
# Stored studies are accepted without checksums and bypass recomputation on repeated request.
p=cat.root/'studies'/f"{s['study_id']}.json";data=json.loads(p.read_text());data['result']['verdict']={'code':'EDGE','confidence':'99,9 %','title':'falsified edge','text':'falsified'}
if data.get('final_model') and data['final_model'].get('latest_signal'):data['final_model']['latest_signal']['opinion']='PRENDRE'
p.write_text(json.dumps(data));cl=TestClient(create_app(cat),base_url='http://localhost',headers={'X-ATO-Request':'1'},raise_server_exceptions=False)
resp=cl.get('/api/v1/research/edge-studies/'+s['study_id']);again=run_edge_study(cat,ds.meta.dataset_id,spec,cfg,StudySettings(n_boot=200))
out('study_tampering',status=resp.status_code,served_verdict=resp.json()['result']['verdict']['code'],repeat_returns_falsified=again['result']['verdict']['title']=='falsified edge')
# Unchanged study 1 never receives a later total-family correction.
a=s['multiple_testing'];s3=run_edge_study(cat,ds.meta.dataset_id,spec,cfg,StudySettings(n_boot=201))
out('repeated_testing',first_alpha=a['alpha'],second_alpha=s3['multiple_testing']['alpha'],first_cached_alpha=load_study(cat.root,s['study_id'])['multiple_testing']['alpha'],bootstrap_seed_changes=s['study_id'][:8]!=s3['study_id'][:8])
# Supervised backtest safeguards do not cover research API configs.
os.environ['ATO_RISK_POLICY']='supervised';config=cfg.model_dump(mode='json');config['contract']['symbol']='EURUSD';config['risk']['max_trades_per_day']=100
resp=cl.post('/api/v1/research/edge-studies',json={'dataset_id':ds.meta.dataset_id,'strategy_key':spec.key,'config':config,'horizon_bars':5})
out('supervised_research_override',status=resp.status_code,contract_symbol='EURUSD',dataset_symbol=ds.meta.symbol,result=resp.json().get('result',{}).get('verdict',{}).get('code'));os.environ.pop('ATO_RISK_POLICY')

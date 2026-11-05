import sys,json,tempfile
from pathlib import Path
P=Path(__file__).parent;sys.path.insert(0,str(P/'repo/quant/tests'))
import numpy as np,pandas as pd
from ai_trader_optimizer.data import synthetic_dataset,dataset_from_frame
from ai_trader_optimizer.research import StudySettings,run_edge_study
from ai_trader_optimizer.research.labels import label_signals
from ai_trader_optimizer.strategies import load_catalog,build_strategy
from ai_trader_optimizer.storage import LabCatalog
from ai_trader_optimizer.backtest import BacktestConfig,run_backtest
from ai_trader_optimizer.api.app import create_app
from fastapi.testclient import TestClient
base=load_catalog().specs['baseline.ema_trend_3bars@1.0.0'];cfg=BacktestConfig();ds=synthetic_dataset(7,20);sig=build_strategy(base,{}).compute(ds.bars)
lab=label_signals(ds,base,cfg,sig);latest=lab.signal_time.max();lastns=np.flatnonzero(sig.signal.to_numpy()!=0)
# actual latest opinion from previously recorded study, evaluated against membership in training labels
records=json.loads((P/'research-evidence.json').read_text());observed=next(x for x in records if x['name']=='real_study');lt=pd.Timestamp(observed['latest']['signal_time'])
print(json.dumps({'name':'latest_is_training_row','latest':lt.isoformat(),'in_training_labels':bool((lab.signal_time==lt).any()),'latest_outcome':lab.loc[lab.signal_time==lt,['exit_time','win','r']].to_dict('records'),'dataset_end':ds.bars.timestamp.iloc[-1].isoformat()},default=str))
# mismatched execution timeframe accepted for research while main engine rejects it
bars=ds.bars.iloc[::5].copy().reset_index(drop=True);five=dataset_from_frame(bars,name='M5',symbol=ds.meta.symbol,source_label='probe',kind=ds.meta.kind)
cat=LabCatalog(Path(tempfile.mkdtemp(dir=P)));cat.save_dataset(five)
try:run_backtest(five,base,cfg);engine='accepted'
except ValueError as exc:engine=str(exc)
study=run_edge_study(cat,five.meta.dataset_id,base,cfg,StudySettings(n_boot=200,horizon_bars=5))
print(json.dumps({'name':'timeframe_mismatch','dataset_timeframe':five.meta.timeframe,'strategy_execution':base.timeframes.execution,'main_engine':engine,'study_accepted':True,'study_verdict':study['result']['verdict']['code']}))
# AUC=0 is valid and should not be converted to missing by `or np.nan`
import ai_trader_optimizer.research.study as st
original_auc=st.auc;st.auc=lambda *args:0.0
n=1000;t=np.arange(n,dtype=np.int64)*60*10**9;rng=np.random.default_rng(91);r=np.where(rng.random(n)<.5,1.5,-1)
try:
 out=st.evaluate_signals(t,t+60*10**9,rng.normal(size=(n,2)),r,StudySettings(n_boot=200),seed=0)
 print(json.dumps({'name':'zero_auc_interval','auc':out['auc']}))
finally:st.auc=original_auc

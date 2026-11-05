import sys,json,tempfile
from pathlib import Path
P=Path(__file__).parent;sys.path.insert(0,str(P/'repo/quant/tests'))
import numpy as np,pandas as pd
from ai_trader_optimizer.research.robustness import run_robustness
from ai_trader_optimizer.research.study import evaluate_signals,StudySettings
from ai_trader_optimizer.api.app import create_app
trades=pd.DataFrame({'net_pnl':[-50.]*50+[50.]*50,'r_multiple':[-1.]*50+[1.]*50})
out=run_robustness(trades,10000,20,'12345678',n_boot=1000)
print(json.dumps({'name':'loss_clusters_permutation','result':out}))
# Compare Brier against the empirical-rate reference on a positive expectancy, non-predictable process
rng=np.random.default_rng(300);n=1500;t=np.arange(n,dtype=np.int64)*60*10**9;X=rng.normal(size=(n,4));wins=rng.random(n)<.5;r=np.where(wins,1.5,-1.)
o=evaluate_signals(t,t+60*10**9,X,r,StudySettings(n_boot=300),seed=300)
print(json.dumps({'name':'positive_edge_no_predictor','verdict':o['verdict'],'brier':o.get('brier'),'auc':o.get('auc'),'improvement':o.get('improvement')}))
app=create_app();routes=[{'method':m,'path':r.path} for r in app.routes if hasattr(r,'methods') and r.path.startswith('/api/') for m in r.methods if m not in ['OPTIONS','HEAD']]
print(json.dumps({'name':'order_routes','route_count':len(routes),'order_paths':[r for r in routes if any(word in r['path'].lower() for word in ['order','broker','execute','mt5','position'])]}))
(P/'api-routes.json').write_text(json.dumps(routes,indent=2))

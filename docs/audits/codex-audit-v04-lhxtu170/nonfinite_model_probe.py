import warnings,json,sys
from pathlib import Path
P=Path(__file__).parent;sys.path.insert(0,str(P/'repo/quant/tests'))
import numpy as np
from ai_trader_optimizer.research.stats import LogisticModel
from ai_trader_optimizer.research.study import _latest_opinion
from ai_trader_optimizer.research.features import FEATURES
from ai_trader_optimizer.data import synthetic_dataset
from ai_trader_optimizer.strategies import load_catalog,build_strategy
from ai_trader_optimizer.backtest import BacktestConfig
with warnings.catch_warnings():
 warnings.simplefilter('ignore');m=LogisticModel().fit(np.full((200,len(FEATURES)),1e308),np.arange(200)%2)
ds=synthetic_dataset(7,3);sp=load_catalog().specs['baseline.ema_trend_3bars@1.0.0'];sig=build_strategy(sp,{}).compute(ds.bars)
q=_latest_opinion(ds.bars,sig,BacktestConfig(),m,None,sp.trading_hours,ds.bar_seconds)
print(json.dumps({'input_finite':True,'coefficients_finite':bool(np.isfinite(m.coef_).all()),'opinion':q},default=str))

import sys,math
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent/'repo/quant/tests'))
from conftest import scripted,make_bars
from ai_trader_optimizer.data import dataset_from_frame
from ai_trader_optimizer.safety import DataKind
from ai_trader_optimizer.backtest import BacktestConfig,run_backtest
count=0
for side in ['bid','mid']:
 for direction in [1,-1]:
  for spread,slip,comm in [(0,0,0),(.3,.05,3),(.6,.1,7)]:
   cfg=BacktestConfig(costs={'spread':spread,'slippage':slip,'commission_per_lot_per_side':comm})
   sp,st=scripted({0:(direction,2,30)})
   ds=dataset_from_frame(make_bars([(100,100.2,99.8,100)]*3),name='probe',symbol='XAUUSD',source_label='independent',kind=DataKind.SYNTHETIC,price_side=side)
   r=run_backtest(ds,sp,cfg,strategy=st); t=r.trades.iloc[0]
   # fixed flat price: both directions must pay spread, both slips and both commissions exactly once
   unit_risk=(2+slip)*100+2*comm
   lots=math.floor((25/unit_risk)*100+1e-10)/100
   expected=-((spread+2*slip)*100+2*comm)*lots
   assert abs(t.lots-lots)<1e-9,(t.lots,lots)
   assert abs(t.net_pnl-expected)<1e-8,(t.net_pnl,expected)
   assert abs(r.metrics['final_equity']-(10000+expected))<1e-8
   count+=1
print(f'PASS {count}/{count} financial cases: BUY/SELL x bid/mid x 3 cost profiles')

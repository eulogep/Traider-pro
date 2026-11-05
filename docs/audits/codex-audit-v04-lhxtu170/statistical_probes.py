import sys,json,math,time
from pathlib import Path
P=Path(__file__).parent;sys.path.insert(0,str(P/'repo/quant/tests'))
import numpy as np
from ai_trader_optimizer.research.study import evaluate_signals,StudySettings
from ai_trader_optimizer.research.stats import auc,brier,block_length
rows=[]
def experiment(name,seeds,p=.4,cluster=1,n=1500):
 output=[]
 for seed in seeds:
  rng=np.random.default_rng(seed);t=np.arange(n,dtype=np.int64)*60*10**9
  X=rng.normal(size=(n,4))
  wins=np.repeat(rng.random(math.ceil(n/cluster))<p,cluster)[:n]
  r=np.where(wins,1.5,-1.0)
  # common outcome is only known at the end of each correlated group
  end=np.minimum((np.arange(n)//cluster+1)*cluster,n)*60*10**9
  out=evaluate_signals(t,end,X,r,StudySettings(n_boot=300),seed=seed)
  output.append({'seed':seed,'verdict':out['verdict']['code'],'n_oos':out['n_oos'],'n_taken':out.get('n_taken'), 'mean_r':out.get('filtered',{}).get('mean_r'),'ci':out.get('filtered',{}).get('ci')})
 count=sum(r['verdict']=='EDGE' for r in output)
 record={'experiment':name,'p':p,'true_expectancy_r':2.5*p-1,'cluster':cluster,'n':n,'trials':len(output),'edges':count,'seeds':output};rows.append(record)
 print(json.dumps({k:v for k,v in record.items() if k!='seeds'}),flush=True)
 (P/'statistical-evidence.json').write_text(json.dumps(rows,indent=2))
experiment('independent_null_60',range(100,160))
experiment('independent_weak_p045_30',range(200,230),p=.45)
experiment('independent_medium_p050_30',range(300,330),p=.5)
experiment('correlated_null_60',range(400,460),cluster=100,n=3000)
# exact equal-tailed binomial interval, via inversion of the binomial CDF (no scipy dependency)
def cdf(k,n,p):return sum(math.comb(n,i)*p**i*(1-p)**(n-i) for i in range(k+1))
def solve(k,n,target):
 lo,hi=0.,1.
 for _ in range(80):
  mid=(lo+hi)/2
  if cdf(k,n,mid)>target:lo=mid
  else:hi=mid
 return (lo+hi)/2
def ci(x,n):return [0. if x==0 else solve(x-1,n,.975),1. if x==n else solve(x,n,.025)]
summary={'announced_intervals_95':{'1/60':ci(1,60),'19/30':ci(19,30),'30/30':ci(30,30)},'observed_intervals_95':{e['experiment']:ci(e['edges'],e['trials']) for e in rows},'sequential_alpha_sum_60':sum(.05/i for i in range(1,61)),'independent_uniform_probability_any_60':1-math.prod(1-.05/i for i in range(1,61)),'block_for_1500':block_length(1500)}
(P/'statistical-summary.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary),flush=True)

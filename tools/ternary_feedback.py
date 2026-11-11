"""3次ループ帰還の2倍・4倍を閾値とディザの候補で比較する。"""
import json
from pathlib import Path
import numpy as np
from ternary_explore import simulate
from ternary_compare import metrics
if __name__=='__main__':
    n=1<<20;warm=65536;t=np.arange(n+warm);rows=[]
    for shift in (24,23,22):
        for threshold in (.25,.5):
            for dither in (22,23):
                scores=[]
                for hz,amp in ((1000,1.),(100000,1.),(1000,.001),(100000,.001)):
                    k=round(hz*n/50e6)
                    x=np.rint((2**31-1)*amp*np.sin(2*np.pi*k*t/n)).astype(np.int64)
                    try:
                        y,peak=simulate(x,3,int(threshold*(1<<32)),dither,0,0x1A2B3C4D,shift)
                        scores.append(float(metrics(y[warm:],k,200000)['sndr']))
                    except AssertionError:
                        scores.append(-999.)
                row=dict(feedback_shift=shift,threshold=threshold,dither=dither,sndr=scores)
                rows.append(row);print(row,flush=True)
    Path(__file__).with_name('ternary_feedback_results.json').write_text(json.dumps(rows,indent=2)+'\n')

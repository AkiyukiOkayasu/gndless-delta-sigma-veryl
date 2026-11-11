"""3値量子化器の閾値・ディザ・ゼロ連続制限を同条件で探索する。"""
import json
from pathlib import Path
import numpy as np
from numba import njit
from ternary_compare import metrics

@njit(cache=True)
def simulate(raw, order, threshold, noise_shift, run_limit, seed=0x1A2B3C4D, feedback_shift=24):
    y=np.empty(len(raw))
    a=b=c=0
    q=0
    rng=seed
    previous=rng&1
    zeros=0
    peak=np.zeros(3)
    for i in range(len(raw)):
        x=raw[i]
        if order==2:
            a+=x+4*((rng&1)-previous)-q*(1<<32)
            b+=a-q*(1<<32)
            u=b
        else:
            u=x-((11182988*a+3418645*b+453260*c)>>feedback_shift)
        d=(((rng&255)-((rng>>8)&255))<<noise_shift) if noise_shift>=0 else 0
        v=u+d
        q=1 if v>=threshold else -1 if v<=-threshold else 0
        if run_limit>0 and zeros>=run_limit and q==0:
            q=1 if v>=0 else -1
        zeros=zeros+1 if q==0 else 0
        if order==3:
            a,b,c=a+q*(1<<32)-x,b+a,c+b
        peak[0]=max(peak[0],abs(a)/(1<<32))
        peak[1]=max(peak[1],abs(b)/(1<<32))
        peak[2]=max(peak[2],abs(c)/(1<<32))
        assert abs(a)<(16<<32) and abs(b)<(64<<32) and abs(c)<(256<<32)
        y[i]=q
        previous=rng&1
        rng=(rng>>1)^(0x80200003 if rng&1 else 0)
    return y,peak

if __name__=='__main__':
    n=1<<20;warm=65536;t=np.arange(n+warm)
    cases=[]
    for hz,amp in [(1000,1.),(100000,1.),(1000,.001),(100000,.001)]:
        k=round(hz*n/50e6)
        cases.append((f'{hz}_{amp}',np.rint((2**31-1)*amp*np.sin(2*np.pi*k*t/n)).astype(np.int64),k))
    rows=[]
    for order in (2,3):
        for threshold in (.25,.5,.75):
            for shift in (-1,18,20,22,23,24):
                for limit in (0,1):
                    scores=[]
                    for name,x,k in cases:
                        try:
                            y,peak=simulate(x,order,int(threshold*(1<<32)),shift,limit)
                            scores.append(float(metrics(y[warm:],k,200000)['sndr']))
                        except AssertionError:
                            scores.append(-999.)
                    rows.append(dict(order=order,threshold=threshold,shift=shift,limit=limit,sndr=scores))
        candidates=[r for r in rows if r['order']==order]
        for row in sorted(candidates,key=lambda r:min(r['sndr'][2:]),reverse=True)[:8]:
            print(row,flush=True)
    Path(__file__).with_name('ternary_explore_results.json').write_text(json.dumps(rows,indent=2)+'\n')

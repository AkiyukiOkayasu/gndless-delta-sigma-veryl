"""採用した3値改善とコミット時点の基準を比較し、複数seedを検証する。"""
import json
from pathlib import Path
import numpy as np
from ternary_explore import simulate
from ternary_compare import simulate as second_before, metrics
from third_ternary_compare import simulate_third as third_before

if __name__ == '__main__':
    n=1<<22; warm=65536; t=np.arange(n+warm)
    rows=[]
    cases=[]
    for hz in (1000,20000,100000):
        k=round(hz*n/50e6)
        for amp in (1.,.001,.000001):
            cases.append((f'sine_{hz}_{amp}',np.rint((2**31-1)*amp*np.sin(2*np.pi*k*t/n)).astype(np.int64),k))
    for x in (0,1,-1,32,-32,65536,715827882,2147483647,-2147483648):
        cases.append((f'dc_{x}',np.full(n+warm,x,np.int64),None))
    cases.append(('square_100k',np.where(t%500<250,2147483647,-2147483648).astype(np.int64),None))
    cases.append(('saw_200k',((t%250)*17179869-2147483648).astype(np.int64),None))
    cases.append(('random_rails',np.random.default_rng(73).choice(np.array([-2147483648,2147483647],np.int64),n+warm),None))
    for name,x,k in cases:
        row={'case':name}
        for version in ('second_before','third_before','second_after','third_after'):
            if version=='second_before':
                y,peak,_=second_before(x,True)
            elif version=='third_before':
                y,peak,trips=third_before(x,True)
                assert trips==0
            else:
                order=2 if version=='second_after' else 3
                y,peak=simulate(x,order,(1<<31) if order==2 else (1<<30),23 if order==2 else 22,0,feedback_shift=24 if order==2 else 23)
            row[version]={'peak_state':peak.tolist(),'mean_error':float(np.mean(y[warm:])-np.mean(x[warm:])/(1<<32)),'bands':{str(bw):metrics(y[warm:],k,bw) for bw in (20000,100000,200000)}}
        rows.append(row)
        if k is not None:
            print(name,[(v,round(row[v]['bands']['200000']['sndr'],2)) for v in ('second_before','second_after','third_before','third_after')],flush=True)
    seeds=[]
    for seed in (1,0xDEADBEEF):
        for hz in (1000,20000,100000):
            k=round(hz*n/50e6)
            x=np.rint((2**31-1)*.001*np.sin(2*np.pi*k*t/n)).astype(np.int64)
            for order in (2,3):
                y,peak=simulate(x,order,(1<<31) if order==2 else (1<<30),23 if order==2 else 22,0,seed,24 if order==2 else 23)
                seeds.append(dict(seed=seed,hz=hz,order=order,peak_state=peak.tolist(),bands=metrics(y[warm:],k,200000)))
    Path(__file__).with_name('ternary_improvement_results.json').write_text(json.dumps(dict(main=rows,seeds=seeds),indent=2)+'\n')

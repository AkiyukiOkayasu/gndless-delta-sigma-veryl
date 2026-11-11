"""探索候補を長い観測窓とDC・急変入力で再評価する。"""
import json
from pathlib import Path
import numpy as np
from ternary_explore import simulate
from ternary_compare import metrics

if __name__ == "__main__":
    n = 1<<22
    warm = 65536
    t = np.arange(n+warm)
    cases = []
    for hz in (1000, 20000, 100000):
        k = round(hz*n/50e6)
        for amp in (1., .001):
            cases.append((f"sine_{hz}_{amp}", np.rint((2**31-1)*amp*np.sin(2*np.pi*k*t/n)).astype(np.int64), k))
    for x in (0,1,-1,32,-32,65536,715827882,2147483647,-2147483648):
        cases.append((f"dc_{x}", np.full(n+warm,x,np.int64), None))
    cases.append(("square_100k",np.where(t%500<250,2147483647,-2147483648).astype(np.int64),None))
    cases.append(("random_rails",np.random.default_rng(73).choice(np.array([-2147483648,2147483647],dtype=np.int64), n+warm),None))
    rows=[]
    for name,raw,k in cases:
        row={"case":name}
        configs=[("second_before",2,.5,-1,0),("second_dither",2,.5,23,0),("second_strong",2,.5,24,0),("third_before",3,.5,18,0),("third_dither",3,.25,22,0),("third_strong",3,.25,23,0),("third_constrained",3,.25,20,1)]
        for version,order,threshold,shift,limit in configs:
            y,peak=simulate(raw,order,int(threshold*(1<<32)),shift,limit)
            row[version]={"peak_state":peak.tolist(),"mean_error":float(np.mean(y[warm:])-np.mean(raw[warm:])/(1<<32)),"bands":{str(bw):metrics(y[warm:],k,bw) for bw in (20000,100000,200000)}}
        rows.append(row)
    Path(__file__).with_name("ternary_finalists.json").write_text(json.dumps(rows,indent=2)+"\n")
    for row in rows[:6]:
        print(row['case'],[(v,round(row[v]['bands']['200000']['sndr'],2)) for v,*_ in configs],flush=True)

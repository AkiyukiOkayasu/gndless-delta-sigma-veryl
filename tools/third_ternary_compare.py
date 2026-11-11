"""50MHz・3次2値/3値と2次3値の比較。numpyとnumbaを使用する。"""
import json
from pathlib import Path
import numpy as np
from numba import njit
def metrics(y, tone_bin=None, bandwidth=20000):
    # Hann窓でPDMの帯域外ノイズの漏れを抑え、間引きのaliasやCIC droopを含めず評価する。
    window = .5 - .5*np.cos(2*np.pi*np.arange(len(y))/len(y))
    a = np.abs(np.fft.rfft(y*window)) * 4 / len(y)
    hi = int(bandwidth * len(y) / 50e6)
    lo = max(1, int(np.ceil(20 * len(y) / 50e6)))
    band = a[lo:hi+1].copy()
    tone_bin = tone_bin if tone_bin is not None and lo <= tone_bin <= hi else None
    sig = a[tone_bin] if tone_bin is not None else 0
    if tone_bin is not None:
        band[max(0,tone_bin-lo-1):tone_bin-lo+2] = 0
    rms = np.sqrt(np.sum(band**2)/3)
    return dict(sndr=20*np.log10(sig/np.sqrt(2)/max(rms,1e-30)) if sig else None,
                noise_dbfs=20*np.log10(max(rms*np.sqrt(2),1e-30)),
                peak_dbfs=20*np.log10(max(np.max(band),1e-30)))




@njit(cache=True)
def simulate_third(raw, ternary, dither_shift=13):
    y=np.empty(len(raw))
    a=b=c=0
    rng=0x1A2B3C4D
    peak=np.zeros(3)
    trips=0
    for i in range(len(raw)):
        x=raw[i]>>5
        u=x-((11182988*a+3418645*b+453260*c)>>24)
        d=((rng&255)-((rng>>8)&255))<<dither_shift
        q=(1 if u+d >= (1<<26) else -1 if u+d <= -(1<<26) else 0) if ternary else (1 if u+d>=0 else -1)
        na=a+q*(1<<27)-x
        nb=b+a
        nc=c+b
        trip=na<-(1<<31) or na>=(1<<31) or nb<-(1<<33) or nb>=(1<<33) or nc<-(1<<35) or nc>=(1<<35)
        if trip:
            a=b=c=0
            q=0 if ternary else -1
            trips+=1
        else:
            a,b,c=na,nb,nc
        peak[0]=max(peak[0],abs(a)/(1<<27))
        peak[1]=max(peak[1],abs(b)/(1<<27))
        peak[2]=max(peak[2],abs(c)/(1<<27))
        y[i]=q
        rng=(rng>>1)^(0x80200003 if rng&1 else 0)
    return y,peak,trips

from ternary_compare import simulate as simulate_second

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
        for version in ("third_binary","third_ternary","second_ternary"):
            if version == "second_ternary":
                y,peak,_=simulate_second(raw,True)
                trips=0
            else:
                y,peak,trips=simulate_third(raw,version=="third_ternary")
            row[version]={"peak_state":peak.tolist(),"overloads":trips,"mean_error":float(np.mean(y[warm:])-np.mean(raw[warm:])/(1<<32)),"bands":{str(bw):metrics(y[warm:],k,bw) for bw in (20000,100000,200000)}}
        rows.append(row)
    Path(__file__).with_name("third_ternary_results.json").write_text(json.dumps(rows,indent=2)+"\n")
    for row in rows[:6]:
        print(row["case"],*[ (v,row[v]["bands"]["200000"]["sndr"]) for v in ("third_binary","third_ternary","second_ternary")])

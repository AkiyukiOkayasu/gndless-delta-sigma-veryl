"""整数参照モデルからVeryl testのchecksumを更新する。"""
from pathlib import Path
import re
from ternary_reference import Modulator as Second
from third_ternary_reference import Modulator as Third, stimulus
root=Path(__file__).resolve().parents[1]
p=root/'src/delta_sigma_ternary.veryl'
s=p.read_text()
m=Second()
values=[]
for raw in (0,1,-1,32,-32,2147483647,-2147483648,715827882,0):
    h=0
    for _ in range(8192):
        h=(h*31+m.step(raw)+1)&0xffffffff
    values.append(h)
it=iter(values)
s=re.sub(r'hash == 32.h[0-9a-f]+',lambda _:f"hash == 32'h{next(it):08x}",s)
p.write_text(s)
p=root/'src/delta_sigma_3rd_ternary.veryl'
s=p.read_text()
for name,seed in [('EXPECTED',0x1A2B3C4D),('EXPECTED_OTHER',1)]:
    values=[]
    for phase in range(12):
        m=Third(seed); h=2166136261
        for i in range(65536):
            q,trip=m.step(stimulus(phase,i))
            assert not trip
            h=((h^(q+1))*16777619)&0xffffffff
        values.append(f"32'h{h:08x}")
    s=re.sub(r"(const "+name+r"\s*: logic<32> \[12\] = '\{).*?(\};)",lambda m:m[1]+'\n'+', '.join(values)+'\n'+m[2],s,flags=re.S)
p.write_text(s)

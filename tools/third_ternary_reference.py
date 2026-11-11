"""3次3値の無限精度整数モデルとnative test期待値生成。"""
from dsm_reference import stimulus

class Modulator:
    def __init__(self, seed=0x1A2B3C4D):
        self.rng = seed
        self.state = (0, 0, 0)

    def step(self, raw):
        x = raw
        a, b, c = self.state
        u = x - ((11182988*a + 3418645*b + 453260*c) >> 23)
        d = ((self.rng & 255) - ((self.rng >> 8) & 255)) << 22
        q = 1 if u+d >= 1<<30 else -1 if u+d <= -(1<<30) else 0
        state = (a + q*(1<<32) - x, b+a, c+b)
        trip = any(v < -limit or v >= limit for v,limit in zip(state, (1<<36,1<<38,1<<40)))
        self.state = (0,0,0) if trip else state
        self.rng = (self.rng>>1) ^ (0x80200003 if self.rng&1 else 0)
        return (0 if trip else q), trip

if __name__ == "__main__":
    for seed in (0x1A2B3C4D, 1):
        values=[]
        for phase in range(12):
            model=Modulator(seed)
            h=2166136261
            for i in range(65536):
                q,trip=model.step(stimulus(phase,i))
                assert not trip
                h=((h^(q+1))*16777619)&0xffffffff
            values.append(f"32'h{h:08x}")
        print(seed, ", ".join(values))

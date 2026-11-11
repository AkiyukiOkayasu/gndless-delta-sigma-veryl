"""2次3値の無限精度整数モデル。"""
class Modulator:
    def __init__(self, seed=0x1A2B3C4D):
        self.a = self.b = self.q = 0
        self.rng = seed
        self.previous = seed & 1

    def step(self, raw):
        current = self.rng & 1
        self.a += raw + 4*(current-self.previous) - self.q*(1<<32)
        self.b += self.a - self.q*(1<<32)
        d = ((self.rng&255)-((self.rng>>8)&255))<<23
        v = self.b+d
        self.q = 1 if v >= 1<<31 else -1 if v <= -(1<<31) else 0
        self.previous = current
        self.rng = (self.rng>>1) ^ (0x80200003 if current else 0)
        return self.q

"""CIFF固定小数点の無限精度整数参照モデル（追加package不要）。"""
A = (11182988, 3418645, 453260)
UNITY = 1 << 27
LIMITS = (16 * UNITY, 64 * UNITY, 256 * UNITY)
SEED = 0x1A2B3C4D


class Modulator:
    def __init__(self, seed=SEED):
        assert 0 < seed < 2**32
        self.rng = seed
        self.state = (0, 0, 0)

    def step(self, raw):
        x = raw >> 5
        s1, s2, s3 = self.state
        u = x - ((A[0]*s1 + A[1]*s2 + A[2]*s3) >> 24)
        dither = ((self.rng & 255) - ((self.rng >> 8) & 255)) << 13
        bit = int(u + dither >= 0)
        q = UNITY if bit else -UNITY
        next_state = (s1 + q - x, s2 + s1, s3 + s2)
        trip = any(v < -limit or v >= limit for v, limit in zip(next_state, LIMITS))
        self.state = (0, 0, 0) if trip else next_state
        self.rng = (self.rng >> 1) ^ (0x80200003 if self.rng & 1 else 0)
        return (0 if trip else bit), trip


def stimulus(phase, i):
    if phase < 7:
        return (0, 1, -1, 32, -32, 2147483647, -2147483648)[phase]
    if phase == 7:
        t = i % 8192
        return -2147483648+t*1048576 if t < 4096 else 2147483647-(t-4096)*1048576
    if phase == 8:
        return 2147483647 if i % 500 < 250 else -2147483648
    if phase == 9:
        return 2147483647 if i % 250 < 125 else -2147483648
    if phase == 10:
        return (i % 250)*17179869 - 2147483648
    return 2147483647 if i % 2 else -2147483648


def checksums():
    for seed in (SEED, 1):
        result = []
        for phase in range(12):
            model = Modulator(seed)
            checksum = 2166136261
            for i in range(65536):
                bit, trip = model.step(stimulus(phase, i))
                assert not trip, (seed, phase, i)
                checksum = ((checksum ^ bit) * 16777619) & 0xffffffff
            result.append(checksum)
        print(hex(seed), ", ".join(f"32\x27h{x:08x}" for x in result))


def verify_lfsr_period():
    def apply(matrix, value):
        result = 0
        for index in range(32):
            if value & (1 << index):
                result ^= matrix[index]
        return result

    def jump(value, cycles):
        matrix = [((1 << index) >> 1) ^ (0x80200003 if index == 0 else 0) for index in range(32)]
        while cycles:
            if cycles & 1:
                value = apply(matrix, value)
            matrix = [apply(matrix, column) for column in matrix]
            cycles >>= 1
        return value

    period = 2**32 - 1
    assert jump(1, period) == 1
    for prime in (3, 5, 17, 257, 65537):
        assert jump(1, period//prime) != 1


if __name__ == "__main__":
    verify_lfsr_period()
    checksums()

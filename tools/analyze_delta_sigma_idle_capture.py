#!/usr/bin/env python3
"""DeltaSigma2nd無音PDMキャプチャのCIC出力を時変スペクトルとして解析する。"""

from __future__ import annotations

import argparse
import csv
import math
from array import array
from pathlib import Path


CLOCK_HZ = 50_000_000.0
CIC_DECIMATION = 1024
CIC_STAGES = 3
CIC_GAIN = CIC_DECIMATION**CIC_STAGES
CIC_OUTPUT_WIDTH = 64
SAMPLE_RATE_HZ = CLOCK_HZ / CIC_DECIMATION
REQUIRED_COLUMNS = {"index", "cycle", "cic_3stage_1024x_bits"}


def decode_twos_complement(value: str, width: int) -> int:
    """Verylが16進数で書いた固定幅の符号付き値を復号する。"""
    raw = int(value, 16)
    mask = (1 << width) - 1
    if raw & ~mask:
        raise ValueError(f"値 {value!r} は{width}bitに収まらない")
    if raw & (1 << (width - 1)):
        return raw - (1 << width)
    return raw


def read_capture(path: Path) -> array:
    """CSVを検証しつつ、CICゲインで正規化したPDM値を読む。"""
    samples = array("d")
    previous_index: int | None = None
    previous_cycle: int | None = None
    with path.open(newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        missing = REQUIRED_COLUMNS - set(reader.fieldnames or ())
        if missing:
            raise ValueError(f"CSVの列が不足している: {', '.join(sorted(missing))}")

        for line_number, row in enumerate(reader, start=2):
            try:
                index = int(row["index"])
                cycle = int(row["cycle"])
                value = decode_twos_complement(row["cic_3stage_1024x_bits"], CIC_OUTPUT_WIDTH)
            except (KeyError, TypeError, ValueError) as error:
                raise ValueError(f"CSV {line_number}行目を解釈できない: {error}") from error

            if previous_index is not None and index != previous_index + 1:
                raise ValueError(f"CSV {line_number}行目のindexが連続していない")
            if previous_cycle is not None and cycle != previous_cycle + CIC_DECIMATION:
                raise ValueError(f"CSV {line_number}行目のcycle間隔が{CIC_DECIMATION}ではない")
            previous_index = index
            previous_cycle = cycle
            samples.append(value / CIC_GAIN)

    if not samples:
        raise ValueError("CSVにデータ行がない")
    return samples


def fft(values: list[complex]) -> list[complex]:
    """依存なしのradix-2 FFT。window_sizeは2の冪であること。"""
    size = len(values)
    if size == 0 or size & (size - 1):
        raise ValueError("FFTサイズは2の冪でなければならない")

    result = values[:]
    bit_reversed = 0
    for index in range(1, size):
        bit = size >> 1
        while bit_reversed & bit:
            bit_reversed ^= bit
            bit >>= 1
        bit_reversed ^= bit
        if index < bit_reversed:
            result[index], result[bit_reversed] = result[bit_reversed], result[index]

    stage = 2
    while stage <= size:
        twiddle_step = complex(math.cos(-2.0 * math.pi / stage), math.sin(-2.0 * math.pi / stage))
        half = stage // 2
        for start in range(0, size, stage):
            twiddle = 1.0 + 0.0j
            for offset in range(half):
                left = start + offset
                right = left + half
                value = twiddle * result[right]
                result[right] = result[left] - value
                result[left] += value
                twiddle *= twiddle_step
        stage *= 2
    return result


def dbfs(value: float) -> float:
    """正規化済みPDM振幅をdBFSへ変換する。"""
    return 20.0 * math.log10(max(value, 1.0e-300))


def analyze(
    samples: array,
    window_size: int,
    hop_size: int,
    discard_seconds: float,
) -> list[dict[str, float]]:
    """Hann窓FFTで時間窓ごとのRMSと最強トーンを返す。"""
    discard = int(discard_seconds * SAMPLE_RATE_HZ)
    if discard >= len(samples):
        raise ValueError("--discard-secondsがキャプチャ長以上")
    if len(samples) - discard < window_size:
        raise ValueError("解析可能なサンプル数がwindow_sizeに不足している")

    window = [0.5 - 0.5 * math.cos(2.0 * math.pi * index / window_size) for index in range(window_size)]
    window_sum = sum(window)
    low_bin = max(1, math.ceil(20.0 * window_size / SAMPLE_RATE_HZ))
    high_bin = min(window_size // 2, math.floor(20_000.0 * window_size / SAMPLE_RATE_HZ))
    results: list[dict[str, float]] = []

    for start in range(discard, len(samples) - window_size + 1, hop_size):
        source = samples[start : start + window_size]
        mean = sum(source) / window_size
        centered = [float(value) - mean for value in source]
        rms = math.sqrt(sum(value * value for value in centered) / window_size)
        spectrum = fft([complex(value * weight, 0.0) for value, weight in zip(centered, window)])

        peak_bin = low_bin
        peak_amplitude = 0.0
        for index in range(low_bin, high_bin + 1):
            amplitude = 2.0 * abs(spectrum[index]) / window_sum
            if amplitude > peak_amplitude:
                peak_amplitude = amplitude
                peak_bin = index

        results.append(
            {
                "start_seconds": start / SAMPLE_RATE_HZ,
                "rms_dbfs": dbfs(rms),
                "peak_frequency_hz": peak_bin * SAMPLE_RATE_HZ / window_size,
                "peak_dbfs": dbfs(peak_amplitude),
            }
        )
    return results


def write_analysis(path: Path, results: list[dict[str, float]]) -> None:
    """時間窓ごとの解析結果をCSVへ書き出す。"""
    with path.open("w", newline="") as csv_file:
        writer = csv.DictWriter(
            csv_file,
            fieldnames=("start_seconds", "rms_dbfs", "peak_frequency_hz", "peak_dbfs"),
        )
        writer.writeheader()
        writer.writerows(results)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "csv_path",
        nargs="?",
        type=Path,
        default=Path("target/test_delta_sigma_2nd_idle_capture.csv"),
    )
    parser.add_argument("--window-size", type=int, default=16_384)
    parser.add_argument("--hop-size", type=int, default=8_192)
    parser.add_argument("--discard-seconds", type=float, default=1.0)
    parser.add_argument("--tone-threshold-dbfs", type=float, default=-100.0)
    parser.add_argument("--analysis-path", type=Path)
    args = parser.parse_args()

    if args.window_size <= 0 or args.window_size & (args.window_size - 1):
        parser.error("--window-sizeは2の冪で指定する")
    if args.hop_size <= 0:
        parser.error("--hop-sizeは1以上で指定する")
    if args.discard_seconds < 0.0:
        parser.error("--discard-secondsは0以上で指定する")

    samples = read_capture(args.csv_path)
    results = analyze(samples, args.window_size, args.hop_size, args.discard_seconds)
    analysis_path = args.analysis_path or args.csv_path.with_name(f"{args.csv_path.stem}_analysis.csv")
    write_analysis(analysis_path, results)

    duration_seconds = len(samples) / SAMPLE_RATE_HZ
    loudest = max(results, key=lambda result: result["peak_dbfs"])
    detections = [result for result in results if result["peak_dbfs"] >= args.tone_threshold_dbfs]
    print(f"capture={args.csv_path}")
    print(f"samples={len(samples)} sample_rate_hz={SAMPLE_RATE_HZ:.6f} duration_seconds={duration_seconds:.6f}")
    print(f"analysis={analysis_path} windows={len(results)}")
    print(
        "loudest_tone="
        f"time={loudest['start_seconds']:.6f}s "
        f"frequency={loudest['peak_frequency_hz']:.3f}Hz "
        f"level={loudest['peak_dbfs']:.2f}dBFS"
    )
    if detections:
        first = detections[0]
        last = detections[-1]
        print(
            "tone_windows="
            f"count={len(detections)} threshold={args.tone_threshold_dbfs:.2f}dBFS "
            f"time={first['start_seconds']:.6f}..{last['start_seconds']:.6f}s "
            f"frequency={min(item['peak_frequency_hz'] for item in detections):.3f}.."
            f"{max(item['peak_frequency_hz'] for item in detections):.3f}Hz"
        )
    else:
        print(f"tone_windows=count=0 threshold={args.tone_threshold_dbfs:.2f}dBFS")


if __name__ == "__main__":
    main()

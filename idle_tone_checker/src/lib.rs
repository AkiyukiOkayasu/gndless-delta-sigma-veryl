use std::collections::VecDeque;

use rustfft::{FftPlanner, num_complex::Complex};
use veryl_component::*;

const SAMPLE_RATE_HZ: f64 = 50_000_000.0 / 1024.0;
const CIC_GAIN: f64 = 1024.0 * 1024.0 * 1024.0;
const DISCARD_SAMPLES: u64 = 48_829;
const WINDOW_SIZE: usize = 16_384;
const HOP_SIZE: usize = WINDOW_SIZE / 2;
const LOW_FREQUENCY_HZ: f64 = 20.0;
const HIGH_FREQUENCY_HZ: f64 = 20_000.0;
const MAX_TONE_DBFS: f64 = -100.0;

#[derive(Clone, Copy)]
struct SpectralPeak {
    frequency_hz: f64,
    level_dbfs: f64,
}

/// 3段CICで間引いた無音PDMを監視し、可聴帯域の狭帯域トーンを検出する。
///
/// CIC出力を50MHz / 1024で取得し、リセット後1秒を除外して16384点Hann窓FFTを
/// 50% overlapで実行する。20Hzから20kHzの最大ピークが-100dBFS以上なら失敗とする。
#[derive(Component)]
#[component(kind = clocked)]
pub struct IdleToneChecker {
    /// CICと同じサンプリングクロック。
    clk: ClockPort,
    /// テスト初期化をコンポーネントの状態にも反映するリセット。
    rst: ResetPort,
    /// CIC出力が有効なクロックを示す信号。
    sample_valid: InputPort,
    /// CICゲイン1024^3を含む64bit signed CIC出力。
    sample: InputPort,
    observed_samples: u64,
    windows: u64,
    samples: VecDeque<f64>,
    loudest: Option<SpectralPeak>,
    reported_failure: bool,
}

#[component_impl]
impl IdleToneChecker {
    fn on_build(&mut self, _ctx: &mut BuildCtx) -> Result<()> {
        if self.sample.width() != 64 {
            bail!("sample port must be 64 bits, got {}", self.sample.width());
        }
        Ok(())
    }

    fn on_reset(&mut self, _ctx: &mut SimCtx) -> Result<()> {
        // ResetPortを持つことで、テスト途中の再リセットでも解析状態を破棄する。
        let _ = self.rst;
        self.observed_samples = 0;
        self.windows = 0;
        self.samples.clear();
        self.loudest = None;
        self.reported_failure = false;
        Ok(())
    }

    fn on_clock(&mut self, ctx: &mut SimCtx) -> Result<()> {
        if !ctx.fired(self.clk) {
            return Ok(());
        }
        if !ctx.read(self.sample_valid).as_bool() {
            return Ok(());
        }

        self.observed_samples += 1;
        if self.observed_samples <= DISCARD_SAMPLES {
            return Ok(());
        }

        let sample = ctx.read(self.sample).as_i64()? as f64 / CIC_GAIN;
        self.samples.push_back(sample);
        if self.samples.len() != WINDOW_SIZE {
            return Ok(());
        }

        let peak = spectral_peak(self.samples.make_contiguous());
        self.windows += 1;
        if self
            .loudest
            .is_none_or(|current| peak.level_dbfs > current.level_dbfs)
        {
            self.loudest = Some(peak);
        }
        if peak.level_dbfs >= MAX_TONE_DBFS && !self.reported_failure {
            ctx.fail(format!(
                "idle tone detected: window={} frequency={:.3}Hz level={:.2}dBFS (limit {:.2}dBFS)",
                self.windows, peak.frequency_hz, peak.level_dbfs, MAX_TONE_DBFS
            ));
            self.reported_failure = true;
        }
        self.samples.drain(..HOP_SIZE);
        Ok(())
    }

    fn on_finish(&mut self, ctx: &mut SimCtx) -> Result<()> {
        match self.loudest {
            Some(peak) if !self.reported_failure => ctx.log(format!(
                "idle-tone check passed: windows={} loudest={:.3}Hz/{:.2}dBFS",
                self.windows, peak.frequency_hz, peak.level_dbfs
            )),
            Some(_) => {}
            None => ctx.fail("idle-tone check did not collect a full FFT window"),
        }
        Ok(())
    }
}

veryl_component_export!("idle_tone_checker" => IdleToneChecker);

fn spectral_peak(samples: &[f64]) -> SpectralPeak {
    let mean = samples.iter().sum::<f64>() / samples.len() as f64;
    let mut window_sum = 0.0;
    let mut spectrum = Vec::with_capacity(samples.len());
    for (index, sample) in samples.iter().enumerate() {
        let window =
            0.5 - 0.5 * (2.0 * std::f64::consts::PI * index as f64 / WINDOW_SIZE as f64).cos();
        window_sum += window;
        spectrum.push(Complex::new((sample - mean) * window, 0.0));
    }

    let mut planner = FftPlanner::<f64>::new();
    planner.plan_fft_forward(WINDOW_SIZE).process(&mut spectrum);

    let low_bin = (LOW_FREQUENCY_HZ * WINDOW_SIZE as f64 / SAMPLE_RATE_HZ).ceil() as usize;
    let high_bin = (HIGH_FREQUENCY_HZ * WINDOW_SIZE as f64 / SAMPLE_RATE_HZ).floor() as usize;
    let mut peak = SpectralPeak {
        frequency_hz: low_bin as f64 * SAMPLE_RATE_HZ / WINDOW_SIZE as f64,
        level_dbfs: f64::NEG_INFINITY,
    };
    for (index, value) in spectrum.iter().enumerate().take(high_bin + 1).skip(low_bin) {
        let amplitude = 2.0 * value.norm() / window_sum;
        let level_dbfs = 20.0 * amplitude.max(1.0e-300).log10();
        if level_dbfs > peak.level_dbfs {
            peak = SpectralPeak {
                frequency_hz: index as f64 * SAMPLE_RATE_HZ / WINDOW_SIZE as f64,
                level_dbfs,
            };
        }
    }
    peak
}

#[cfg(test)]
mod tests {
    use super::*;
    use veryl_component::testing::MockSim;

    #[test]
    fn clock_runs() {
        let mut sim = MockSim::new()
            .clock_port("clk")
            .reset_port("rst")
            .input("sample_valid", 1)
            .input("sample", 64);
        let mut c = sim.build::<IdleToneChecker>().unwrap();
        sim.clock(&mut c).unwrap();
        assert!(!sim.failed());
    }

    #[test]
    fn finds_a_narrowband_tone() {
        let bin = 336;
        let samples: Vec<f64> = (0..WINDOW_SIZE)
            .map(|index| {
                (2.0 * std::f64::consts::PI * bin as f64 * index as f64 / WINDOW_SIZE as f64).sin()
                    * 0.01
            })
            .collect();
        let peak = spectral_peak(&samples);
        assert!(
            (peak.frequency_hz - bin as f64 * SAMPLE_RATE_HZ / WINDOW_SIZE as f64).abs() < 0.001
        );
        assert!((-40.1..-39.9).contains(&peak.level_dbfs));
    }
}

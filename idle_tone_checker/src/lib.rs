use std::collections::VecDeque;

use rustfft::{FftPlanner, num_complex::Complex};
use veryl_component::*;

const SAMPLE_RATE_HZ: f64 = 50_000_000.0 / 1024.0;
const CIC_GAIN: i64 = 1024 * 1024 * 1024;
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

/// 無音PDMを3段CICで間引き、可聴帯域の狭帯域トーンを検出する。
///
/// CICは50MHz入力、1/1024間引き、3段、64bit wraparoundで実行する。リセット後1秒を
/// 除外して16384点Hann窓FFTを50% overlapで実行し、20Hzから20kHzの最大ピークが
/// -100dBFS以上なら失敗とする。
#[derive(Component)]
#[component(kind = clocked)]
pub struct IdleToneChecker {
    /// CICと同じサンプリングクロック。
    clk: ClockPort,
    /// テスト初期化をコンポーネントの状態にも反映するリセット。
    rst: ResetPort,
    /// DeltaSigma変調器の1bit PDM出力。
    pdm: InputPort,
    decimation_count: u16,
    integrator: [i64; 3],
    comb_delay: [i64; 3],
    observed_samples: u64,
    windows: u64,
    samples: VecDeque<f64>,
    loudest: Option<SpectralPeak>,
    reported_failure: bool,
}

#[component_impl]
impl IdleToneChecker {
    fn on_build(&mut self, _ctx: &mut BuildCtx) -> Result<()> {
        if self.pdm.width() != 1 {
            bail!("pdm port must be 1 bit, got {}", self.pdm.width());
        }
        Ok(())
    }

    fn on_reset(&mut self, _ctx: &mut SimCtx) -> Result<()> {
        // ResetPortを持つことで、テスト途中の再リセットでも解析状態を破棄する。
        let _ = self.rst;
        self.observed_samples = 0;
        self.windows = 0;
        self.decimation_count = 0;
        self.integrator = [0; 3];
        self.comb_delay = [0; 3];
        self.samples.clear();
        self.loudest = None;
        self.reported_failure = false;
        Ok(())
    }

    fn on_clock(&mut self, ctx: &mut SimCtx) -> Result<()> {
        if !ctx.fired(self.clk) {
            return Ok(());
        }
        if let Some(sample) = self.cic_step(if ctx.read(self.pdm).as_bool() { 1 } else { -1 }) {
            self.observed_samples += 1;
            if self.observed_samples > DISCARD_SAMPLES {
                self.samples.push_back(sample as f64 / CIC_GAIN as f64);
                if self.samples.len() == WINDOW_SIZE {
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
                }
            }
        }
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

impl IdleToneChecker {
    /// 1クロック分のCICを実行し、間引き出力時だけ値を返す。
    fn cic_step(&mut self, input: i64) -> Option<i64> {
        self.integrator[0] = self.integrator[0].wrapping_add(input);
        for index in 1..self.integrator.len() {
            self.integrator[index] =
                self.integrator[index].wrapping_add(self.integrator[index - 1]);
        }

        if self.decimation_count != 1023 {
            self.decimation_count += 1;
            return None;
        }
        self.decimation_count = 0;

        let comb_0 = self.integrator[2].wrapping_sub(self.comb_delay[0]);
        let comb_1 = comb_0.wrapping_sub(self.comb_delay[1]);
        let comb_2 = comb_1.wrapping_sub(self.comb_delay[2]);
        self.comb_delay = [self.integrator[2], comb_0, comb_1];
        Some(comb_2)
    }
}

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
            .input("pdm", 1);
        let mut c = sim.build::<IdleToneChecker>().unwrap();
        sim.clock(&mut c).unwrap();
        assert!(!sim.failed());
    }

    #[test]
    fn cic_gain_matches_three_stage_decimator() {
        let mut sim = MockSim::new()
            .clock_port("clk")
            .reset_port("rst")
            .input("pdm", 1);
        let mut checker = sim.build::<IdleToneChecker>().unwrap();
        let mut output = None;
        for _ in 0..(1024 * 4) {
            output = checker.cic_step(1);
        }
        assert_eq!(output, Some(CIC_GAIN));
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

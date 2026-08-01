# Changelog

## [Unreleased]

## [0.1.1] - 2026-08-02

### Added

- 1次・2次delta-sigma modulatorの無音時アイドルトーンを44秒間検査するNative Testを追加
- 3段CICとFFTによる可聴帯域ピーク検査を行う`idle_tone_checker` Rust verification componentを追加

### Changed

- `DeltaSigma2nd`へ正負対称帰還と±1 LSBのHP-TPDFディザを適用
- CIC検査モデルをVeryl依存から`idle_tone_checker` Rust componentへ移動し、CSV出力とPython後処理を廃止
- 1次delta-sigma modulatorは無音時の0/1完全交互列を検査し、ディザを追加しない構成を明記
- 2次delta-sigma modulatorの比較専用試験を整理し、対称帰還とHP-TPDFディザを長時間回帰試験の出荷構成として固定

### Fixed

- 2次delta-sigma modulatorの無音時アイドルトーンを抑制

## [0.1.0] - 2026-07-31

### Added

- Q1.31 delta-sigma modulatorを独立packageへ移動

### Changed

- 公開moduleのparam/port doc commentを追加
- doc commentの句点と体言止めの表記を整理
- doc commentのsummary表記を統一
- 各testのdoc commentへ検証対象を明記

# Changelog

## [0.3.0] - 2026-11-11

### Added

- 単段1bit CIFF `DeltaSigma3rd`を追加した（H_inf約1.4、閾値ディザ、状態保護、CSD定数乗算）
- 2次3値差動出力の`DeltaSigma2ndTernary`を追加した（Q1.31全32bit保持、閾値ディザ、復調利得1/2）
- 3次3値差動出力の`DeltaSigma3rdTernary`を追加した（Q1.31全32bit保持、Q23係数、状態保護、復調利得1/2）
- 3値版の整数参照モデル、CV累積誤差・入力LSB・参照列・矩形波sweepの検証と、閾値・ディザ・帰還係数の比較資料を追加した
- 2次2値・3値のVeryl synthとGowin合成・配置配線比較を追加した（GW5A-25、両方DSP=0、50MHz制約通過）

### Changed

- `DeltaSigma1st`は入力32bit精度を維持し、出力をキャリーFFへ直結して1 FFと1clockの遅延を削減した
- `DeltaSigma2nd`は入力rawを切り捨てず小数32bitで処理し、DC周期性対策の微小HPディザを維持し、LFSRをresetで直接初期化する構成へ変更した

### Compatibility / Known limitations

- 既存moduleのportと公開parameterは維持するが、1次の出力latency短縮と1次・2次の入力精度変更により、以前のbit列やcycle単位の出力時刻には依存しないこと
- 3値出力は`10=+1、00=0、01=-1`で、独立した2本のGPIOと差動復調段が必要。相補固定のLVDS出力には接続しないこと
- 3次2値版は入力下位5bitを切り捨てるが、3次3値版は全32bitを保持する
- 3値版でも全DC値・全seedのトーン不在や任意入力列の安定性は保証しない。2次の閾値ディザは一部DC値の雑音と大振幅SNDRにトレードオフがある
- 単体のGowin配置配線結果は実機全体の出力スキュー・アナログ精度・タイミングを保証しない。実機測定と既存の長時間idle testは未実施

## [0.2.2] - 2026-10-27

### Added

- `DeltaSigma2nd`のフルスケール入力長時間動作testを追加した

### Changed

- `DeltaSigma2nd`のフルスケールPDM密度が約0.25/0.75になることをREADMEとdoc commentへ明記した
- `gndless_fixedpoint`の package をトップレベル import し、`FixedPointValue` / `Q1_31` の完全修飾パスを短縮（Veryl 0.20.3 の namespace import 機能を使用）

## [0.2.1] - 2026-08-08

### Changed

- `DeltaSigma2nd`の積分器幅を40bitから36bitへ縮小し資源を削減した
- `gndless_fixedpoint`依存を0.2.2へ更新
- github依存解決のlockを反映した

## [0.2.0] - 2026-08-04

### Changed

- 破壊的変更: `DeltaSigma1st`と`DeltaSigma2nd`のQ1.31入力を`FixedPointValue::<Q1_31>` interfaceへ変更
- `gndless_fixedpoint`依存を0.2.0へ更新

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

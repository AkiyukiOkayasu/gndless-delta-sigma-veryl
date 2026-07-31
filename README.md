# gndless_delta_sigma

PCMから1bit PDMへ変換する1次・2次delta-sigma modulatorです。

入力はQ1.31( `gndless_fixedpoint::Q1_31::Raw` )。出力は常に1bitです。stateは同期resetで初期化し、`enable`停止中は保持します。

```veryl
inst modulator: delta_sigma::DeltaSigma2nd (...);
```

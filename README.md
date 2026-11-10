# gndless_delta_sigma

PCMから1bit PDMへ変換する1次・2次delta-sigma modulatorです。

入力はQ1.31の`gndless_fixedpoint::FixedPointValue::<gndless_fixedpoint::Q1_31>`です。出力は常に1bitです。resetの極性・同期性はVerylのbuild設定に従います。`DeltaSigma2nd`は入力全32bitを保持し、復調利得1/2で変換します。フルスケール入力のPDM密度は約0.25/0.75になります。

`DeltaSigma2nd`はDC・微小入力の周期性への備えとして、微小なハイパスディザを加えます。`DITHER_SEED`は非ゼロ値とし、resetで同じ乱数系列を再開します。全入力でのトーン抑制は保証しません。

`DeltaSigma1st` は無音時に0/1の完全な交互列となり、同じ3段CIC検査で可聴帯域の
トーンを検出しなかったため、ディザは加えません。これは`audio = 0`の固定入力に
限る結果であり、非ゼロ入力・入力遷移を含む全条件でのスプリアス不在を保証するものではありません。

```veryl
inst modulator: delta_sigma::DeltaSigma2nd (...);
```

## 無音アイドルトーン検査

1次・2次の現行実装について長時間無音時挙動を確認するNative Testを用意しています。通常のテストからは除外されているため、必要時だけ実行します。
Rust verification componentを使用するため、Veryl nightlyが必要です。

```sh
veryl test --ignored
```

50MHzで44秒間のPDMを3段CIC・1/1024で間引き、Rust verification component が内部で解析します。リセット後1秒を除外し、16384点Hann窓FFTを50% overlapで実行します。20Hzから20kHzの最大狭帯域ピークが-100dBFS以上ならテストは失敗します。通常時は、最強ピークの周波数とレベルをテスト出力へ表示します。CSVは出力しません。

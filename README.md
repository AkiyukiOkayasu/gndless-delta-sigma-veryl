# gndless_delta_sigma

PCMから1bit PDMへ変換する1次・2次delta-sigma modulatorです。

入力はQ1.31の`gndless_fixedpoint::FixedPointValue::<gndless_fixedpoint::Q1_31>`です。出力は常に1bitです。stateは同期resetで初期化します。

`DeltaSigma2nd` は無音時のアイドル・トーンを避けるため、変調器入力へ
±1 LSBのハイパスTPDFディザを加えます。`DITHER_SEED`は非ゼロ値を指定し、複数
インスタンスを並列使用する場合はチャンネルごとに異なる値を指定してください。
固定ゼロ入力・固定リセット位相での比較では対称帰還が主に可聴帯域成分を抑えましたが、
全入力・全状態でディザ不要とは結論できないため、出荷構成ではHP-TPDFディザを併用します。

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

# gndless_delta_sigma

PCMから1bit PDMへ変換する1次・2次delta-sigma modulatorです。

入力はQ1.31( `gndless_fixedpoint::Q1_31::Raw` )。出力は常に1bitです。stateは同期resetで初期化します。

`DeltaSigma2nd` は無音時のアイドル・トーンを避けるため、変調器入力へ
±1 LSBのハイパスTPDFディザを加えます。`DITHER_SEED`は非ゼロ値を指定し、複数
インスタンスを並列使用する場合はチャンネルごとに異なる値を指定してください。

```veryl
inst modulator: delta_sigma::DeltaSigma2nd (...);
```

## 無音アイドルPDMキャプチャ

長時間の無音時挙動を確認するNative Testを用意しています。通常のテストからは除外されているため、必要時だけ実行します。

```sh
veryl test --ignored
```

`target/test_delta_sigma_2nd_idle_capture.csv` に、50MHzで44秒間のPDMを3段CIC・1/1024で間引いた値を書き出します。出力レートは48.828125kHz、値にはCICゲイン `1024^3` が含まれます。

```sh
python3 tools/analyze_delta_sigma_idle_capture.py
```

解析器はCICゲインを正規化し、Hann窓FFTによる時間窓ごとのRMS・最大トーン周波数・最大トーンレベルを `*_analysis.csv` に出力します。無音時のスイープは、時刻に対する `peak_frequency_hz` の連続的な上昇または下降として確認します。

# gndless_delta_sigma

Q1.31波形を毎clock 1bit PDMへ変換するVeryl packageです。

| module | 復調利得 | 特徴 |
| --- | --- | --- |
| `DeltaSigma1st` | 1 | 入力32bitを保持するキャリー方式 |
| `DeltaSigma2ndTernary` | 1/2 | 2次3値、差動GPIO、resetは00 |
| `DeltaSigma2nd` | 1/2 | 入力32bitを保持、微小HPディザ |
| `DeltaSigma3rdTernary` | 1/2 | 単段CIFFの3値差動GPIO、入力下位5bit切捨て、過負荷通知 |
| `DeltaSigma3rd` | 1/2 | 入力下位5bitを切り捨てる単段CIFF、閾値ディザ、過負荷通知 |

入力型は`gndless_fixedpoint::FixedPointValue::<gndless_fixedpoint::Q1_31>`です。入力を受理したposedge後に登録PDMを更新します。enable・補間器・リミッターは持たず、入力とPDMを同じclockで毎周期更新します。

```veryl
inst modulator: gndless_delta_sigma::DeltaSigma3rd (
    clk: waveform_clk,
    rst: rst,
    audio: waveform,
    pdm: pdm,
    overload: overload,
);
```

2次・3次の`DITHER_SEED`は非ゼロとし、並列チャンネルには異なる値を指定します。3次の`overload=1`では状態とPDMを0にして、次周期から通常処理へ戻ります。出力異常の診断信号として使ってください。

resetの極性・同期性はVerylのbuild設定に従います。reset中のPDM=0固定は復調上の負フルスケールなので、必要な起動時ミュートは利用側で扱います。PDMの復調精度と応答は復調フィルタにも依存し、入力32bitがそのままアナログ32bit精度になるわけではありません。

3次の数値形式・係数・過負荷条件は[設計仕様](THIRD_ORDER.md)を参照してください。

```sh
veryl fmt
veryl check
veryl test
veryl build
veryl test --ignored  # 長時間のゼロ入力検査
```

ゼロ入力検査はnative testとRust verification componentを使い、1次・2次は各44秒、3次は4秒のPDMをCIC・FFTで評価します。通常testからは除外しています。

3次のnative testで使うbit列期待値とLFSR周期は、標準ライブラリだけで動く整数モデルで確認できます。

```sh
python3 tools/dsm_reference.py
```

3値版の接続・比較結果・制約は[設計と評価](TERNARY.md)を参照してください。

3次3値版の数値契約と比較結果は[設計資料](THIRD_ORDER_TERNARY.md)を参照してください。

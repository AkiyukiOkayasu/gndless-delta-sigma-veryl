# 3次3値CIFF

`DeltaSigma3rdTernary`は既存`DeltaSigma3rd`のCIFF係数、固定小数点幅、閾値ディザ、過負荷保護を使う3値版。50MHzで毎posedgeに入力を取り込み、直後に2本の登録GPIOを更新する。復調利得1/2、符号化は`10=+1、00=0、01=-1`。resetと過負荷検出時は00、11は生成しない。独立した2本のGPIOを使い、相補固定のLVDS出力には接続しない。

```veryl
inst modulator: gndless_delta_sigma::DeltaSigma3rdTernary (
    clk: clk_50mhz,
    rst: rst,
    audio: waveform,
    pdm_p: dac_p,
    pdm_n: dac_n,
    overload: overload,
);
```

## ループ

UNITY=2^27、x=Q1.31 rawを算術右シフト5bitした値。a1/a2/a3は11182988/3418645/453260を各2^24で割った係数である。状態はedge前の値を使用する。

```
u = x - ((11182988*s1 + 3418645*s2 + 453260*s3) >>> 24)
v = u + dither
q = +1 if v >= UNITY/2
    -1 if v <= -UNITY/2
     0 otherwise
s1_next = s1 + q*UNITY - x
s2_next = s2 + s1
s3_next = s3 + s2
```

状態のsigned幅は32/34/36bit、小数27bitで保持範囲は±16/64/256。更新候補は各1bit拡張し、選択された候補のoverflowを保存前に検出する。ゼロ出力時のs1更新候補も保護対象。過負荷時は全状態・両GPIOを0、overloadを1にして次周期から再開する。LFSRは保護時も継続する。resetで乱数seedも復元する。

定数積和は既存と同じ57bitのCSD加算木で計算し、一度だけ24bit算術右シフトする。入力下位5bitは負無限大方向に切り捨て、有効入力精度は27bit。したがって全32bitを保持する2次3値版とは異なり、微小CVには量子化誤差と正負非対称がある。

ディザは既存3次と同じ32bit Galois LFSR（非ゼロseed、マスク0x80200003）の8bit区画差を13bit左シフトし、量子化器のみに加える。最大振幅は255/2^14。強さを変更した別設計を混在させず、まず既存2値版との差を比較する。線形化NTF/STFは[既存3次の設計](THIRD_ORDER.md)と同じであり、実際の量子化器は非線形である。

## 比較

`python tools/third_ternary_compare.py`で再現できる（numpy、numbaが必要）。結果は`tools/third_ternary_results.json`。50MHz、2^22点=83.9ms、先行65536周期破棄、Hann窓FFTで評価した。以下は20Hz〜200kHz帯域SNDR、基本波と隣接binを除去。復調信号振幅は入力の半分で、GPIO・アナログ回路の誤差を含まない。

| 入力 | 3次2値 | 3次3値 | 2次3値 |
|---|---:|---:|---:|
| フルスケール 1kHz | 98.10dB | 99.68dB | 92.38dB |
| フルスケール 20kHz | 97.38dB | 98.07dB | 92.27dB |
| フルスケール 100kHz | 97.55dB | 100.92dB | 92.58dB |
| -60dB 1kHz | 38.50dB | 35.42dB | 32.16dB |
| -60dB 20kHz | 44.40dB | 35.14dB | 25.85dB |
| -60dB 100kHz | 42.99dB | 30.41dB | 19.98dB |

3次3値は大振幅では改善したが、小振幅では3次2値より劣る。ゼロ近傍でゼロ出力が続き、蓄積した状態が閾値を越えた際にパルスが出るため、3値化で常に雑音が下がるわけではない。音源の微小高調波を重視する場合はこの結果に注意する。

DCは0、±1LSB、±32LSB、65536、約1/3、正負端点を比較した。ゼロ入力は全区間00、状態も0である。+1LSBは入力切捨てによりゼロとなる一方、-1LSBは-32LSB相当となる。CV用途で入力全32bitの精度が必要なら2次3値版を使う。100kHz最大振幅矩形波・ランダム端点も含めた全17条件でoverloadなし、3次3値の状態ピークは約1.51/3.54/18.78以内だった。これは有限の試験結果であり、任意入力列の安定性の証明ではない。

帯域外基本波を含むJSONのnoise値や矩形波・ランダム入力のnoise値には信号電力が入るため、雑音性能として比較しない。実機の50MHzタイミング収束、GPIO間の遅延差・電圧差、復調フィルタ、ジッタ、CVの温度ドリフトは別途検証が必要。

## 検証

`tools/third_ternary_reference.py`は追加package不要の無限精度整数モデルで、native testのchecksumを生成する。12入力条件、2seed、各65536周期をreset再現性も含め2回検証する。11禁止、過負荷なし、resetの00を確認する。別のnative testで10種類の周期と5種類のdutyを連続変更し、平均利得と過負荷なしを確認する。

通常の`veryl test`は既存分を含め12 passed / 0 failed / 3 ignored。3次3値の2テストは`--backend-validate 64`でも成功し、backend間の不一致なし。`veryl fmt`、`veryl check`、`veryl build`も成功し、生成SVの正負閾値比較と2本の登録出力を確認した。既存の長時間idle testは未実施。

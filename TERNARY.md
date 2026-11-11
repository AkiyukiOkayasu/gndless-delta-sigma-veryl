# 2次3値の設計

`DeltaSigma2ndTernary`は50MHzの独立した差動GPIO向け。Q1.31全32bitを保持し、復調利得は1/2。`pdm_p,pdm_n`は`10=+1、00=0、01=-1`で、11は生成せずresetは00。相補固定のLVDSバッファでは00を表現できないため独立した2本のGPIOが必要になる。

入力を毎posedgeで受理し直後に両GPIOを登録更新する。入力も同じclock domainで保持または補間する。enableや補間器は内蔵しない。

```veryl
inst modulator: gndless_delta_sigma::DeltaSigma2ndTernary (
    clk: clk_50mhz,
    rst: rst,
    audio: waveform,
    pdm_p: dac_p,
    pdm_n: dac_n,
);
```

## 数値契約

UNITY=2^32、x=Q1.31 raw、q=前周期の差動値。状態と中間値は小数32bit・signed 38bitで、範囲[-32,32)を外れる演算はwrapする。

```
a_next = a + x + hp_dither - q*UNITY
b_next = b + a_next - q*UNITY
v = b_next + threshold_dither
q_next = +1 if v >= UNITY/2
         -1 if v <= -UNITY/2
          0 otherwise
```

LFSRは32bit右シフトGalois、マスク0x80200003、DITHER_SEEDは非ゼロ。resetで同じ系列を再現する。HPディザはLSBの前後差×4で累積寄与は±4LSB以内。閾値ディザは8bit区画2個の差×2^23で、ピーク255/512（約0.498）、RMS約0.204。乱数は時間相関を持つ決定論的な系列である。閾値ディザは積分器入力へ直接加えない。ゼロ出力の連続制限は設けない。

線形化NTFは(1-z^-1)^2、STFは1。ディザはDC平均を入力側でずらさないが、有限窓の平均誤差やトーン不在は保証しない。

[改善評価と比較結果](TERNARY_IMPROVEMENT.md)を参照。`tools/ternary_compare.py`と`tools/ternary_results.json`はコミットfe31383の基準モデル・測定結果として保持する。現在の整数参照モデルは`tools/ternary_reference.py`、比較は`tools/ternary_improvement.py`。

## 実機確認

配置配線後の50MHzタイミング、GPIO間の電圧・遅延差、差動復調段のコモンモード除去を確認する。00と±1ではコモンモードが変わる。CVでは基準電圧・オフセット・温度ドリフト、100kHz波形では帯域外PDM雑音を減衰する復調フィルタが精度を制約する。入力全32bit保持はアナログ32bit精度の保証ではない。

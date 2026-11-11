# 3次3値CIFF

`DeltaSigma3rdTernary`は50MHzの独立した差動GPIO向け。復調利得1/2、入力Q1.31全32bitを保持する。`10=+1、00=0、01=-1`、11は禁止、resetと過負荷検出時は00。入力を毎posedgeで受理し、直後に2本の登録GPIOを更新する。

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

## 数値契約

UNITY=2^32、x=Q1.31 raw。状態はedge前の値を使う。

```
u = x - ((11182988*s1 + 3418645*s2 + 453260*s3) >>> 23)
v = u + dither
q = +1 if v >= UNITY/4
    -1 if v <= -UNITY/4
     0 otherwise
s1_next = s1 + q*UNITY - x
s2_next = s2 + s1
s3_next = s3 + s2
```

状態はsigned 37/39/41bit、小数32bit、保持範囲は[-16,16)/[-64,64)/[-256,256)。候補幅は38/40/42bit、量子化器入力はsigned 39bit、係数積和はsigned 62bit・小数55bit。CSD加算木で積和を計算し、一度だけ23bit算術右シフトして負無限大へ丸める。入力の下位bitは切り捨てない。

更新候補のoverflowを保存前に検出し、全状態と両GPIOを0、overloadを1にして次周期から再開する。ゼロ出力時の更新候補も保護対象。LFSRは保護時も継続し、reset時だけseedへ戻す。

閾値ディザは32bit Galois LFSR（マスク0x80200003）の8bit区画差×2^22。ピーク255/1024（約0.249）、RMS約0.102。DITHER_SEEDは非ゼロとする。入力xへ直接加えず、判定だけに使用する。ゼロ連続制限は設けない。

整数係数は[3次2値版](THIRD_ORDER.md)と同じだが、Q23として解釈し帰還係数を2倍にする。線形化STFは1、NTFは(1-z^-1)^3/D(z)で、D(z)=1-1.6668839455z^-1+0.7413021326z^-2-0.0203853846z^-3。線形化した極は0.81873696±0.15104228jと0.02941003で、H_infは約2.3333。係数と閾値の変更により、既存3次2値のH_inf=1.4とは異なる。量子化器は非線形であり、全入力列の安定性やトーン不在は保証しない。復調フィルタ、IO誤差、配置配線後の50MHzタイミングは実機で確認する。

## 評価と再現

[改善評価](TERNARY_IMPROVEMENT.md)を参照。`tools/third_ternary_compare.py`と`tools/third_ternary_results.json`はfe31383時点の27bit入力基準として保持する。現在の比較は`tools/ternary_improvement.py`、無限精度整数参照は`tools/third_ternary_reference.py`、native test期待値の更新は`python tools/update_ternary_vectors.py`で行う。

native testでは12入力条件×2seed×65536周期をreset再現性も含め2回検証し、11禁止・過負荷なし・resetの00を確認する。10周期×5dutyの連続矩形波sweep、および正負1LSBが状態へ入ることも確認する。

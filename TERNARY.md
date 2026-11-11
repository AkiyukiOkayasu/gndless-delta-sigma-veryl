# 2次3値の設計と評価

`DeltaSigma2ndTernary`は50 MHzで更新する差動GPIO向けの試作である。Q1.31全32bitを保持し、既存`DeltaSigma2nd`と同じ復調利得1/2とする。依存packageと既存APIは変更しない。

| pdm_p | pdm_n | 差動値 |
|---|---|---|
| 0 | 0 | 0 |
| 1 | 0 | +1 |
| 0 | 1 | -1 |

11は生成しない。resetは00。2本ともposedge直後に更新する。相補出力専用のLVDSバッファでは00を表せないため、独立した2本のGPIOと差動復調回路が必要になる。

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

UNITY=2^32、x=Q1.31のraw値、q=前周期の差動値とする。

```
a_next = a + x + d - q*UNITY
b_next = b + a_next - q*UNITY
q_next = +1 if b_next >= UNITY/2
         -1 if b_next <= -UNITY/2
          0 otherwise
```

状態はsigned 38bit、小数32bit、範囲[-32,32)。中間演算も同じ幅でwrapする。微小HPディザdは既存2値版と同じ非ゼロseedのLFSRから生成し、隣接bitの差の4倍とする。累積ディザは±4LSB以内。入力の平均にDCオフセットを追加しない。通常使用のフルスケール入力は帰還基準の±0.5である。NTFは線形化すると(1-z^-1)^2、STFは1。量子化誤差の非線形性はこの式だけでは評価できない。

## 再現方法と結果

`python tools/ternary_compare.py`（numpy、numbaが必要）で整数モデル比較を実行できる。結果は`tools/ternary_results.json`。各条件2^22点（83.9ms）、先行65536周期を破棄、50MHz、Hann窓、基本波と隣接binを除いたSNDRである。dBFSは差動±1の正弦波基準、入力フルスケールの復調振幅は0.5。アナログフィルタ・GPIO誤差は含まない。

| フルスケール正弦波 | 2値 SNDR | 3値 SNDR |
|---|---:|---:|
| 約1kHz | 84.54dB | 92.38dB |
| 約20kHz | 84.55dB | 92.27dB |
| 約100kHz | 84.46dB | 92.58dB |

上表は20Hz〜200kHz帯域の結果。100kHzまでの波形を扱うため、100kHz基本波を帯域端から離して評価した。JSONの帯域外基本波を持つnoise値はその信号成分を含むため雑音値として比較しない。

DCは0、±1LSB、±32LSB、65536、1/3付近、正負端点を比較し、100kHz最大振幅矩形波・毎周期ランダム端点も評価した。全条件で状態幅のoverflowなし。3値の状態ピークは約2.00以内、2値は約13.81以内。有限窓の平均誤差は両方式とも概ね5e-7以内であり、CVのアナログ精度を保証する数値ではない。

無入力の3値出力は観測区間すべて00で、GPIOの切替を抑えられた。ただし±1LSBなどの微小DCはバースト状出力となり、100kHz帯域の雑音値は両方式とも約-96.8dBFS。微小入力で常に改善するわけではない。-60dB入力100kHz正弦波の200kHz帯域SNDRは両方式とも約20dBに留まる。高域で非常に小さい倍音まで高精度に必要なら、より高次の方式・高いclock・別のディザ設計を検討する必要がある。

native testは9区間×8192周期の整数参照hash、入力LSB、11禁止、状態範囲、動作後resetを検証する。参照hashにはDC端点から反対端点への急変も含める。長時間・全入力列についての安定性証明はしていない。

## 実機で残る確認

50MHzのタイミング収束は対象FPGAの配置配線後に確認する。GPIOを同一bankで近接配置し、IOレジスタと同一IO規格を使用する。00と±1ではコモンモードが異なるため、出力段のコモンモード除去と2経路の抵抗・遅延・立上り立下り差が精度を制約する。CVは基準電圧・オフセット・温度ドリフトの実測が必要。100kHzを通す低域フィルタでは帯域外PDMノイズを十分減衰させる設計が必要で、音源更新レートが低い場合は変調器の前段で補間する。

調査参考：[Analog Devicesの解説](https://www.analog.com/en/resources/analog-dialogue/articles/using-sigma-delta-converters-1.html)は2次でも帯域内アイドルトーンが生じることを説明している。[AESの3値系に関する研究要旨](https://aes.org/publications/elibrary/elibrary-page/?id=9820)も3値でのトーンと量子化器飽和の影響を扱っている。3値化のみでトーンが消えるという前提は置いていない。

## 実行済み検証

`veryl fmt`、`veryl check`、`veryl test`、`veryl build`を実行し成功。通常testは10 passed / 0 failed / 3 ignored（既存の長時間idle検査）。追加testは`veryl test -t test_delta_sigma_ternary --backend-validate 1`でも成功し、cc/Cranelift間の不一致なし。生成SVの符号付き閾値比較と2本の登録出力も確認した。既存の44秒idle検査と実機検証は未実施。

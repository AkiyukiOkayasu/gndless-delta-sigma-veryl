# 2次2値・3値のリソース比較

ソースはb2fa1c9。対象は`DeltaSigma2nd`と`DeltaSigma2ndTernary`のみ。変調器RTLは変更せず、Gowin比較では共通の32bit入力レジスタを追加する。2値は1本、3値は2本の出力を外部へ接続し、出力や入力を定数にして回路が削除されることを避ける。

## 再現手順

package rootで実行する。Gowinの出力は指定した一時ディレクトリへ保存し、ボードには書き込まない。

```sh
veryl build
veryl synth --top DeltaSigma2nd --format json --dump-area > /tmp/dsm-second-binary-synth.json
veryl synth --top DeltaSigma2ndTernary --format json --dump-area > /tmp/dsm-second-ternary-synth.json

export DSM_RESOURCE_BUILD=/tmp/dsm-resource-b2fa1c9
export DYLD_LIBRARY_PATH=/Applications/GowinIDE.app/Contents/Resources/Gowin_EDA/IDE/lib
export DYLD_FRAMEWORK_PATH="$DYLD_LIBRARY_PATH"
DSM_RESOURCE_VARIANT=binary gw_sh tools/resource_compare/run.tcl
DSM_RESOURCE_VARIANT=ternary gw_sh tools/resource_compare/run.tcl
python3 tools/resource_compare/collect.py --root "$DSM_RESOURCE_BUILD" --binary /tmp/dsm-second-binary-synth.json --ternary /tmp/dsm-second-ternary-synth.json
```

Gowin V1.9.12、GW5A-LV25MG121NC1/I0 version A、20ns制約、timing_driven=1、place=1、route=2。IOB packingは無効。resetはasync_lowでfalse path。I/Oの配置は自動、外部のinput/output delayは指定していない。従ってFmaxはこの単体トップの内部レジスタ間の配置配線後評価であり、実機全体の保証ではない。

`run.tcl`は指定したvariantの比較projectを作成し、そのprojectのimplだけを再生成する。既存の実機projectは使用しない。結果と入力SVのSHA256は`results.json`へ記録する。Verylはモジュール本体だけ、GowinのFF数は入力レジスタ32個を含む。

## Gowin結果

| 指標 | 2値 | 3値 | 差 |
|---|---:|---:|---:|
| 合成後LUT | 10 | 23 | +13 |
| 合成後ALU | 117 | 149 | +32 |
| 合成後Logic（LUT+ALU） | 127 | 172 | +35.4% |
| 配置配線後LUT | 8 | 22 | +14 |
| 配置配線後ALU | 119 | 151 | +32 |
| 配置配線後Logic | 127 | 173 | +36.2% |
| FF（入力レジスタ込み） | 142 | 143 | +1 |
| FF（変調器本体） | 110 | 111 | +1 |
| DSP | 0 | 0 | 0 |
| BSRAM | 0 | 0 | 0 |
| 配置配線後Fmax | 119.083MHz | 91.843MHz | -22.9% |
| setup違反endpoint | 0 | 0 | 0 |
| hold違反endpoint | 0 | 0 | 0 |

両方とも50MHz制約を満たした。GowinのALUはcarry用のロジックprimitiveでありDSPではない。合成XMLのリソースと生成ネットリストのprimitive一覧を確認し、MULT系・DSP系primitiveがないことを確認した。合成ログと実行ログにWARNING/ERRORはなかった。

3値では状態幅は増えていないため、FF増加は出力の1個だけ。組合せ回路ではディザ用の差分・加算、ゼロを含む帰還選択、正負の閾値判定が増える。クリティカル経路はGowin timing reportから確認できる。

## Veryl synth結果

Veryl 0.22.1 (8521c8c)、内蔵sky130ライブラリ、入力レジスタなしのモジュール単体。

| 概算指標 | 2値 | 3値 | 差 |
|---|---:|---:|---:|
| cells | 1908 | 2206 | +15.6% |
| area.total | 20922.5 | 24272.5 | +16.0% |
| area.combinational | 12462.5 | 14260.0 | +14.4% |
| FF表示 | 376 | 445 | +69 |
| 概算遅延 | 2.42ns | 3.80ns | +57.0% |

これはFPGAへのLUT/ALUマッピング結果ではない。FF表示もGowinの変調器本体110/111とは一致しないため、VerylのFF数や概算遅延を実FPGAのFF数やFmaxとして使わない。今回の採用判断にはGowinのマッピング・配置配線後の値を使う。JSONのpowerはVeryl既定の100MHz・activity=0.1に基づく概算であり、50MHzでの測定値ではないため比較対象から外す。

Gowinでは合成後Logicが約35%増、配置配線後は約36%増となった。追加回路は主に組合せロジックで、FFの増分は1個。両方式ともDSP=0、50MHz動作にはこの単体測定では余裕がある。

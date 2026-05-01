# dsdf-converter

`dsdf-converter` は Defi Sports Display F (`.dsd`) テレメトリログをCSVに変換するコマンドラインユーティリティです。

バイナリ DSDF ログデータをパースしてタイムスタンプ付きテレメトリレコードを抽出し、ISO8601形式でタイムゾーン対応のCSVにエクスポートします。

## 機能

* `.dsd` バイナリログをCSVに変換
* ISO8601タイムスタンプ（タイムゾーン付き）
* 標準出力または入力ファイル名由来のCSVへ出力
* デフォルトタイムゾーン: JST (`+09:00`)
* 3つの出力モード（計算値のみ/生データのみ/デバッグ）
* `DefiSportsDisplayF.xml` の出力列と計算式に基づいた計算処理
* 実ログから確認した `SportsDisplay-F` バイナリレコード構造のデコード
* モータースポーツおよび車両テレメトリワークフロー対応

## 出力形式

デフォルトではCSVを標準出力へ出力します。`-o` を指定した場合は、入力ファイルと同じ場所に拡張子だけ `.csv` へ変更したファイルを生成します。

```text
20260426_004729.dsd  →  20260426_004729.csv
```

## 使用方法

### デフォルト（計算値のみ）

```bash
python dsdf-converter.py input.dsd
```

出力: 標準出力へCSV (23列)

ファイルへ保存する場合:

```bash
python dsdf-converter.py input.dsd -o
```

出力: `input.csv` (23列)

### 生データのみ

```bash
python dsdf-converter.py input.dsd --raw
```

出力: 標準出力へCSV (21列)

### デバッグモード（生データ+計算値）

```bash
python dsdf-converter.py input.dsd --debug
```

出力: 標準出力へCSV (43列)

## 計算処理（XMLより実装）

| フィールド | 説明 | 計算 |
|-----------|------|------|
| Cnt | 経過時間 | UtcTime / 1000 (秒) |
| SP_AD | 速度 (KPH) | adSP / 10 |
| SP_AD_MPH | 速度 (MPH) | adSP / 16.093 |
| TU_AD | 多様体圧 (kPa) | (adTU - 1000) / 10 |
| OP_AD | オイル圧 | adOP / 220 |
| FP_AD | 燃料圧 (kPa) | 未接続のため 0 |
| DP_AD | 圧力差 | adFP - adTU |
| OT_AD | オイル温度 (°C) | adOT / 20 |
| WT_AD | 水温 (°C) | adWT / 20 |
| EGT_AD | 排気温度 (°C) | adET / 5 |
| TH | スロットル位置 (%) | 未接続のため 0 |
| IN-Air | 吸気温度 (°C) | obdIT |
| GX/GY/GZ | G-Force | (Acc* - 4000) / 1000 |
| RL/PC/YW | 姿勢角 (°) | (Attitude - 4000) / 1000 |
| LATITUDE | 緯度 | LAT / 10000000 |
| LONGITUDE | 経度 | LNG / 10000000 |

`HEADING` は `DefiSportsDisplayF.xml` では `HeadingCalculator` の出力列ですが、DashWare側で緯度経度から算出する想定のため、このスクリプトではCSVへ直接出力しません。

## バイナリフィールド

`.dsd` は先頭に `SportsDisplay-F` シグネチャを持ち、112バイトのヘッダー後に96バイト単位のレコードが続きます。現在確認しているレコード内フィールドは以下です。

```
offset 0   → 年/月/日
offset 4   → UtcTime（日中ミリ秒）
offset 8   → LAT
offset 12  → LNG
offset 18  → adTU
offset 20  → AccX
offset 22  → AccY
offset 24  → AccZ
offset 26  → ROLL
offset 28  → Pitch
offset 30  → Yaw
offset 40  → adSP
offset 44  → adTA
offset 48  → adOP
adFP       → 未接続のため 0
offset 64  → adOT
offset 68  → adWT
offset 72  → adET
obdTH      → 未接続のため 0
offset 77  → obdIT
offset 78  → adGear
```

`--raw` ではデコード後の生フィールドを以下の列名で出力します。

```text
datetime_iso8601,UtcTime,adTA,adSP,adTU,adOP,adFP,adOT,adWT,adET,obdTH,obdIT,adGear,AccX,AccY,AccZ,ROLL,Pitch,Yaw,LAT,LNG
```

## 出力例

```csv
datetime_iso8601,Cnt,SP_AD,SP_AD_MPH,adTA,TU_AD,OP_AD,FP_AD,DP_AD,OT_AD,WT_AD,EGT_AD,TH,IN-Air,adGear,GX,GY,GZ,RL,PC,YW,LATITUDE,LONGITUDE
2026-04-26T00:47:29.900+09:00,2849.900,0.0,0.0,2429,-16.8,77.0,23.0,-602,25.9,32.3,66.0,55.3,0,0,-0.142,-0.088,-1.280,0.000,0.000,0.027,35.58891120,140.12460850
```

## 注意事項

* `.dsd` バイナリフォーマットは公開されていません
* このプロジェクトは実際の DSDF ログファイルのリバースエンジニアリングに基づいています
* XMLフォーマット定義（DefiSportsDisplayF.xml）の計算処理を実装しています
* 未確認のバイト領域があります。追加ログを確認する場合はデバッグモードで検証してください

## 対応デバイス

* Defi Sports Display F

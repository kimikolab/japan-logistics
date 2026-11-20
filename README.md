# ニッポン物流網（プロトタイプ）

日本の47都道府県を路線で結び、荷物を自動配送する物流ネットワーク構築ゲームのプロトタイプ。

## 構成

| パス | 内容 |
|---|---|
| `proto/core.js` | シミュレーション本体。画面に依存しない（Nodeで実行可能） |
| `proto/template.html` | 画面（地図描画・操作盤）。`/*CORE*/` `/*CITIES*/` `/*GEO*/` を埋め込んで使う |
| `proto/build.py` | `core.js` とデータを `template.html` に埋め込み、単体の `index.html` を作る |
| `proto/test.js` | 本体の動作確認（`node proto/test.js`） |
| `data/cities.json` | 47都道府県の代表都市（座標・地方・需要の重み・特産品） |
| `data/geo.json` | 簡略化した県境（描画用） |
| `data/build.mjs` | 県境データの生成スクリプト（`jpn-atlas` が必要） |
| `sim/` | 企画検証に使ったPythonシミュレーター（検証A・B・C） |

## ビルド

```
python3 proto/build.py   # proto/index.html を生成
```

生成された `index.html` をブラウザで開くと動く。外部への通信は Google Fonts のみ。

## 注意

- 数値（運賃、維持費、需要、道路時間）はすべて仮設定。道路時間は直線距離×1.3÷時速75kmの概算。
- 特産品は各県1品目の仮置き。
- 県境データの出典：国土地理院「地球地図日本」（npm パッケージ `jpn-atlas`、BSD-3-Clause 経由）。
- 保存機能なし。

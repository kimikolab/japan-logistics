import fs from "fs";
import * as topojson from "topojson-client";
import * as ts from "topojson-simplify";
import { geoAzimuthalEqualArea, geoContains } from "d3-geo";
const topo = JSON.parse(fs.readFileSync("node_modules/jpn-atlas/japan/japan.json"));
const proj = geoAzimuthalEqualArea().center([138.5, 36 - 18/60]).rotate([-138.5, -36 + 18/60]).scale(1700).translate([2500, -1930]);
const C = `01 北海道 札幌 43.06 141.35 0 4 じゃがいも
02 青森 青森 40.82 140.74 1 1.2 りんご
03 岩手 盛岡 39.70 141.15 1 1.2 わかめ
04 宮城 仙台 38.27 140.87 1 3 笹かまぼこ
05 秋田 秋田 39.72 140.10 1 1.1 米
06 山形 山形 38.24 140.36 1 1.1 さくらんぼ
07 福島 福島 37.75 140.47 1 1.3 もも
08 茨城 水戸 36.34 140.45 2 1.5 納豆
09 栃木 宇都宮 36.57 139.88 2 1.5 いちご
10 群馬 前橋 36.39 139.06 2 1.5 こんにゃく
11 埼玉 さいたま 35.86 139.65 2 4 ねぎ
12 千葉 千葉 35.60 140.12 2 3.5 落花生
13 東京 東京 35.69 139.69 2 10 書籍
14 神奈川 横浜 35.45 139.64 2 6 しゅうまい
15 新潟 新潟 37.90 139.02 3 2 米
16 富山 富山 36.70 137.21 3 1.2 ほたるいか
17 石川 金沢 36.59 136.63 3 1.5 金箔
18 福井 福井 36.07 136.22 3 1 めがね
19 山梨 甲府 35.66 138.57 3 1 ぶどう
20 長野 長野 36.65 138.18 3 1.5 レタス
21 岐阜 岐阜 35.39 136.72 3 1.5 刃物
22 静岡 静岡 34.98 138.38 3 2.5 お茶
23 愛知 名古屋 35.18 136.91 3 5 自動車部品
24 三重 津 34.73 136.51 4 1.3 真珠
25 滋賀 大津 35.00 135.87 4 1.2 近江牛
26 京都 京都 35.02 135.76 4 3 八つ橋
27 大阪 大阪 34.69 135.52 4 7 医薬品
28 兵庫 神戸 34.69 135.18 4 3.5 日本酒
29 奈良 奈良 34.69 135.83 4 1.2 柿
30 和歌山 和歌山 34.23 135.17 4 1 みかん
31 鳥取 鳥取 35.50 134.24 5 0.8 梨
32 島根 松江 35.47 133.05 5 0.8 しじみ
33 岡山 岡山 34.66 133.93 5 2 デニム
34 広島 広島 34.40 132.46 5 3 かき
35 山口 山口 34.19 131.47 5 1.1 ふぐ
36 徳島 徳島 34.07 134.56 6 0.9 すだち
37 香川 高松 34.34 134.04 6 1.1 うどん
38 愛媛 松山 33.84 132.77 6 1.3 タオル
39 高知 高知 33.56 133.53 6 0.9 かつお
40 福岡 福岡 33.61 130.42 7 4 明太子
41 佐賀 佐賀 33.25 130.30 7 0.9 のり
42 長崎 長崎 32.74 129.87 7 1.2 カステラ
43 熊本 熊本 32.79 130.74 7 2 トマト
44 大分 大分 33.24 131.61 7 1.1 しいたけ
45 宮崎 宮崎 31.91 131.42 7 1.1 マンゴー
46 鹿児島 鹿児島 31.56 130.56 7 1.5 さつまいも
47 沖縄 那覇 26.21 127.68 7 1.4 パイナップル`.split("\n").map(l => { const [id, pref, name, lat, lon, reg, mass, prod] = l.split(" "); return { id, pref, name, lat: +lat, lon: +lon, reg: +reg, mass: +mass, prod }; });
// 検証: 各都市が自県のポリゴン内に入るか（投影の一致確認）
const feats = topojson.feature(topo, topo.objects.prefectures).features;
const pip = (pt, rings) => { let inside = false; for (const r of rings) for (let i = 0, j = r.length - 1; i < r.length; j = i++) { const [xi, yi] = r[i], [xj, yj] = r[j]; if ((yi > pt[1]) !== (yj > pt[1]) && pt[0] < (xj - xi) * (pt[1] - yi) / (yj - yi) + xi) inside = !inside; } return inside; };
let bad = 0;
for (const c of C) { const p = proj([c.lon, c.lat]); c.x = +p[0].toFixed(1); c.y = +p[1].toFixed(1);
  const f = feats.find(f => f.id === c.id); const polys = f.geometry.type === "Polygon" ? [f.geometry.coordinates] : f.geometry.coordinates;
  if (!polys.some(rs => pip(p, rs))) { bad++; console.log("NG", c.pref, c.name, p); } }
console.log("cities outside own prefecture:", bad);
// 簡略化
const pre = ts.presimplify(topo); const W = +process.argv[2] || 0.6;
const simp = ts.simplify(pre, W);
const out = {};
const area = r => { let a = 0; for (let i = 0, j = r.length - 1; i < r.length; j = i++) a += (r[j][0] - r[i][0]) * (r[j][1] + r[i][1]); return Math.abs(a / 2); };
for (const f of topojson.feature(simp, simp.objects.prefectures).features) {
  const polys = f.geometry.type === "Polygon" ? [f.geometry.coordinates] : f.geometry.coordinates;
  const rings = polys.map(p => p[0]).filter(r => r.length >= 4 && area(r) > (f.id === "47" ? 0.8 : 2.5));
  out[f.id] = rings.map(r => { const flat = []; let lx, ly; for (const [x, y] of r) { const qx = Math.round(x * 5), qy = Math.round(y * 5); if (qx !== lx || qy !== ly) { flat.push(qx, qy); lx = qx; ly = qy; } } return flat; });
}
fs.writeFileSync("geo.json", JSON.stringify(out)); fs.writeFileSync("cities.json", JSON.stringify(C));
console.log("geo bytes", fs.statSync("geo.json").size, "rings", Object.values(out).reduce((a, r) => a + r.length, 0));

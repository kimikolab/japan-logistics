// ===== ニッポン物流網 プロトタイプ: シミュレーション本体（画面に依存しない） =====
const CAP = 10, CAP_BIG = 20, TRUCK_PRICE_BIG = 9000, UPKEEP_BIG = 3500, STOP_H = 0.5, GRACE = 6, MAX_STOPS = 6;
const TRUCK_PRICE = 4000, UPKEEP_WEEK = 2000, REGION_PRICE = 10000, START_MONEY = 20000, TRUCK_SELL = 2000, FIRST_BONUS = 1000, OPEN_BONUS = 1000, GATE = 0.9, GOAL = 0.95, GOAL_WEEKS = 4;
const FEE_BASE = 10, FEE_PER_H = 4, DEMAND_K = 0.025;
const REGIONS = ["北海道", "東北", "関東", "中部", "近畿", "中国", "四国", "九州・沖縄"];
const ROUTE_COLORS = ["#d1495b", "#1f7a8c", "#e09f3e", "#5b5f97", "#3a7d44", "#b5179e", "#8d6e63", "#0077b6", "#bc6c25", "#6a4c93"];
const EDGE_SRC = "北海道-青森:8:sea,青森-岩手,青森-秋田,岩手-秋田,岩手-宮城,秋田-山形,宮城-山形,宮城-福島,山形-福島,山形-新潟,福島-栃木,福島-新潟,福島-茨城,栃木-埼玉,栃木-茨城,栃木-群馬,茨城-千葉,茨城-東京,埼玉-東京,埼玉-群馬,東京-千葉,東京-神奈川,東京-山梨,神奈川-静岡,群馬-長野,群馬-新潟,新潟-長野,新潟-富山,長野-山梨,長野-富山,長野-愛知,山梨-静岡,静岡-愛知,富山-石川,石川-福井,富山-岐阜,岐阜-愛知,福井-滋賀,愛知-三重,岐阜-滋賀,三重-滋賀,三重-奈良,滋賀-京都,京都-大阪,京都-奈良,奈良-大阪,大阪-和歌山,大阪-兵庫,兵庫-岡山,兵庫-鳥取,岡山-鳥取,鳥取-島根,岡山-広島,島根-広島,広島-山口,島根-山口,岡山-香川,兵庫-徳島,徳島-香川,香川-愛媛,香川-高知,徳島-高知,愛媛-高知,広島-愛媛:2.75,山口-福岡,福岡-佐賀,佐賀-長崎,福岡-大分,福岡-熊本,大分-宮崎,熊本-鹿児島,熊本-宮崎,宮崎-鹿児島,熊本-大分,鹿児島-沖縄:24:sea";

function createGame(CITY_DATA, rng) {
  rng = rng || Math.random;
  const cities = CITY_DATA.map((c, i) => ({ ...c, i, wait: [], cancels: [] }));
  const byPref = {}; cities.forEach(c => byPref[c.pref] = c.i);
  const hav = (a, b) => { const R = 6371, r = Math.PI / 180, dl = (b.lat - a.lat) * r, dn = (b.lon - a.lon) * r;
    const h = Math.sin(dl / 2) ** 2 + Math.cos(a.lat * r) * Math.cos(b.lat * r) * Math.sin(dn / 2) ** 2; return 2 * R * Math.asin(Math.sqrt(h)); };
  const edges = EDGE_SRC.split(",").map(s => { const [ab, h, sea] = s.split(":"), [a, b] = ab.split("-").map(p => byPref[p]);
    // 道路時間(仮): 直線距離×1.3÷時速75km。海をまたぐ区間は個別指定
    return { a, b, h: h ? +h : Math.max(0.5, Math.round(hav(cities[a], cities[b]) * 1.3 / 75 * 4) / 4), sea: !!sea }; });
  const G = { t: 0, money: START_MONEY, cities, edges, routes: [], unlocked: new Set([2]), dist: [], nxt: [], table: {}, pairs: [], cum: [], rate: 0,
    judged: [], lf: 0.5, week: { n: 0, ok: 0, rev: 0, upkeep: 0, bonus: 0 }, garage: 0, garageBig: 0, lastBonus: 0, streak: 0, completed: null, records: { profit: null, trucks: null }, weekNo: 1, reports: [], log: [], nextRouteId: 1, sweepAt: 0, fx: [], firsts: new Set(), totalDelivered: 0, onChange: null };
  const N = cities.length;

  function rebuildRoads() {
    const d = [], nx = [];
    for (let i = 0; i < N; i++) { d.push(new Array(N).fill(Infinity)); nx.push(new Array(N).fill(-1)); d[i][i] = 0; }
    for (const e of edges) if (G.unlocked.has(cities[e.a].reg) && G.unlocked.has(cities[e.b].reg)) { d[e.a][e.b] = d[e.b][e.a] = e.h; nx[e.a][e.b] = e.b; nx[e.b][e.a] = e.a; }
    for (let k = 0; k < N; k++) for (let i = 0; i < N; i++) { const ik = d[i][k]; if (ik === Infinity) continue;
      for (let j = 0; j < N; j++) if (ik + d[k][j] < d[i][j]) { d[i][j] = ik + d[k][j]; nx[i][j] = nx[i][k]; } }
    G.dist = d; G.nxt = nx;
  }
  function roadPath(a, b) { if (G.dist[a][b] === Infinity) return null; const p = [a]; while (a !== b) { a = G.nxt[a][b]; p.push(a); } return p; }
  function edgeH(a, b) { const e = edges.find(e => (e.a === a && e.b === b) || (e.a === b && e.b === a)); return e ? e.h : Infinity; }

  function routeGeom(r) {
    r.legs = [];
    for (let k = 0; k < r.stops.length - 1; k++) { const p = roadPath(r.stops[k], r.stops[k + 1]); let h = 0; const cum = [0];
      for (let q = 0; q < p.length - 1; q++) { h += edgeH(p[q], p[q + 1]); cum.push(h); } r.legs.push({ pts: p, cum, h }); }
    r.cycle = 2 * r.legs.reduce((s, l) => s + l.h, 0) + 2 * (r.stops.length - 1) * STOP_H;
  }
  const headway = r => r.cycle / Math.max(1, r.trucks.length);

  function replan() {
    const at = {}; for (const r of G.routes) r.stops.forEach((c, i) => (at[c] = at[c] || []).push([r, i]));
    const table = {};
    for (const o in at) { const best = {}; best[o] = { c: 0, p: [] }; const done = new Set();
      for (;;) { let u = -1, uc = Infinity; for (const k in best) if (!done.has(k) && best[k].c < uc) { uc = best[k].c; u = k; }
        if (u === -1) break; done.add(u); const bp = best[u].p;
        for (const [r, i] of at[u] || []) { const base = uc + headway(r) / 2 + STOP_H + (bp.length ? 1 : 0);
          for (const dir of [1, -1]) { let acc = 0; for (let j = i + dir; j >= 0 && j < r.stops.length; j += dir) {
            acc += r.legs[Math.min(j, j - dir)].h + (Math.abs(j - i) > 1 ? STOP_H : 0); const v = r.stops[j];
            if (!best[v] || base + acc < best[v].c - 1e-9) best[v] = { c: base + acc, p: bp.concat([{ r: r.id, a: i, b: j }]) }; } } } }
      table[o] = {}; for (const d in best) if (d !== o) table[o][d] = best[d].p; }
    G.table = table; G.pairs = []; G.cum = []; let s = 0;
    for (const o in table) for (const d in table[o]) { s += cities[o].mass * cities[d].mass / (1 + G.dist[o][d]); G.pairs.push([+o, +d]); G.cum.push(s); }
    G.rate = s * DEMAND_K;
    for (const c of cities) for (const sh of c.wait) sh.path = planFrom(c.i, sh.d);
    if (G.onChange) G.onChange();
  }
  const planFrom = (o, d) => { const p = G.table[o] && G.table[o][d]; return p ? p.slice() : null; };

  function addRoute(stops, free) {
    if (stops.length < 2 || stops.length > MAX_STOPS) return "路線は2〜6都市で作ります";
    for (let k = 0; k < stops.length - 1; k++) if (!roadPath(stops[k], stops[k + 1])) return "道路がつながっていない都市があります";
    if (!free && !G.garage && G.money < TRUCK_PRICE) return "資金が足りません（1台目の車両に " + TRUCK_PRICE.toLocaleString() + "G 必要。車庫に車両があれば無料）";
    const before = served();
    const r = { id: G.nextRouteId++, stops: stops.slice(), trucks: [], lf: 0.3, wkRev: 0, wkCost: 0, lastRev: null, lastCost: null }; r.color = ROUTE_COLORS[(r.id - 1) % ROUTE_COLORS.length];
    routeGeom(r); G.routes.push(r); addTruck(r, free, 0);
    G.lastBonus = free ? 0 : stops.filter(c => !before.has(c)).length * OPEN_BONUS; G.money += G.lastBonus; G.week.bonus += G.lastBonus; return null;
  }
  // 車両: 小型(10箱)と大型(20箱)。大型は高価だが1便で多く運べる
  const upkeepOf = r => r.trucks.reduce((a, t) => a + (t.big ? UPKEEP_BIG : UPKEEP_WEEK), 0);
  function addTruck(r, free, delay, big) {
    const price = big ? TRUCK_PRICE_BIG : TRUCK_PRICE, gk = big ? "garageBig" : "garage";
    if (!free) { if (G[gk] > 0) G[gk]--; else { if (G.money < price) return "資金が足りません（" + (big ? "大型" : "小型") + "1台 " + price.toLocaleString() + "G）"; G.money -= price; } }
    r.trucks.push({ route: r, idx: 0, to: 0, dir: 1, load: [], state: "dwell", start: G.t, until: G.t + STOP_H + (delay || 0), big: !!big, cap: big ? CAP_BIG : CAP }); replan(); return null;
  }
  function dropLoad(tr) { const c = cities[tr.route.stops[tr.state === "move" ? tr.to : tr.idx]]; for (const s of tr.load) c.wait.push(s); tr.load = []; }
  function removeTruck(r, big) {
    if (r.trucks.length <= 1) return "最後の1台は減らせません（路線ごと廃止できます）";
    let k = -1; r.trucks.forEach((t, q) => { if (t.big === !!big) k = q; }); if (k < 0) return "この路線に" + (big ? "大型" : "小型") + "の車両はありません";
    dropLoad(r.trucks[k]); r.trucks.splice(k, 1); G[big ? "garageBig" : "garage"]++; replan(); return null; }
  function sellTruck(big) { const gk = big ? "garageBig" : "garage"; if (G[gk] < 1) return "車庫に車両がありません"; G[gk]--; G.money += big ? TRUCK_PRICE_BIG / 2 : TRUCK_SELL; return null; }
  function removeRoute(r) { r.trucks.forEach(tr => { dropLoad(tr); G[tr.big ? "garageBig" : "garage"]++; }); G.routes = G.routes.filter(x => x !== r); replan(); }
  // 路線の編集: 停車都市を入れ替える。車両はそのまま（積み荷は降ろし、始発に戻る）
  function editRoute(r, stops) {
    if (stops.length < 2 || stops.length > MAX_STOPS) return "路線は2〜6都市で作ります";
    for (let k = 0; k < stops.length - 1; k++) if (!roadPath(stops[k], stops[k + 1])) return "道路がつながっていない都市があります";
    const before = served(); r.trucks.forEach(dropLoad); r.stops = stops.slice(); routeGeom(r);
    r.trucks.forEach((tr, k) => { tr.idx = 0; tr.to = 0; tr.dir = 1; tr.state = "dwell"; tr.start = G.t; tr.until = G.t + STOP_H + k * r.cycle / r.trucks.length; });
    G.lastBonus = stops.filter(c => !before.has(c)).length * OPEN_BONUS; G.money += G.lastBonus; G.week.bonus += G.lastBonus; replan(); return null;
  }
  function regionAdjacent(reg) { return edges.some(e => { const ra = cities[e.a].reg, rb = cities[e.b].reg; return (ra === reg && G.unlocked.has(rb)) || (rb === reg && G.unlocked.has(ra)); }); }
  function unlockRegion(reg) {
    if (G.unlocked.has(reg)) return null; if (!regionAdjacent(reg)) return "隣の地方を先に解放してください";
    if (G.money < REGION_PRICE) return "資金が足りません（" + REGION_PRICE.toLocaleString() + "G 必要）";
    const ot = onTime(); if (ot !== null && ot < GATE) return "納期遵守率が" + Math.round(GATE * 100) + "%以上になると進出できます（現在 " + Math.floor(ot * 100) + "%）";
    G.money -= REGION_PRICE; G.unlocked.add(reg); rebuildRoads(); replan(); return null;
  }

  function judge(ok, s, delivered) {
    G.judged.push([G.t, ok]); G.week.n++; if (ok) G.week.ok++;
    if (delivered) { const fee = (FEE_BASE + FEE_PER_H * G.dist[s.o][s.d]) * (ok ? 1 : 0.5); G.money += fee; G.week.rev += fee; G.totalDelivered++;
      G.log.push({ t: G.t, kind: "d", o: s.o, d: s.d, ok }); if (G.log.length > 200) G.log.splice(0, 100);
      G.fx.push({ type: "deliver", c: s.d, fee, ok });
      if (s.rides) { const tot = s.rides.reduce((a, x) => a + x[1], 0) || 1; for (const [rid, h] of s.rides) { const rr = G.routes.find(x => x.id === rid); if (rr) rr.wkRev += fee * h / tot; } }
      if (ok && !G.firsts.has(s.o)) { G.firsts.add(s.o); G.money += FIRST_BONUS; G.week.bonus += FIRST_BONUS; G.fx.push({ type: "first", o: s.o, d: s.d }); G.log.push({ t: G.t, kind: "f", o: s.o, d: s.d }); } }
  }
  function arrive(tr, when) {
    const r = tr.route, i = tr.idx, city = cities[r.stops[i]], keep = [];
    for (const s of tr.load) { if (s.path && s.path[0] && s.path[0].r === r.id && s.path[0].b !== i) { keep.push(s); continue; }
      const l0 = s.path && s.path[0]; if (l0 && l0.r === r.id) { let h = 0; for (let q = Math.min(l0.a, l0.b); q < Math.max(l0.a, l0.b); q++) h += r.legs[q].h; (s.rides = s.rides || []).push([r.id, h]); }
      if (s.d === city.i) judge(when <= s.due, s, true); else { s.path = planFrom(city.i, s.d); city.wait.push(s); } }
    if (i === r.stops.length - 1) tr.dir = -1; else if (i === 0) tr.dir = 1;
    const cand = [], rest = [];
    for (const s of city.wait) { const l = s.path && s.path[0]; (l && l.r === r.id && l.a === i && (l.b - i) * tr.dir > 0 ? cand : rest).push(s); }
    if (cand.length > tr.cap - keep.length) cand.sort((a, b) => ((a.due < when) - (b.due < when)) || a.due - b.due);
    const room = tr.cap - keep.length; tr.load = keep.concat(cand.slice(0, room)); city.wait = rest.concat(cand.slice(room));
  }
  function stepTruck(tr) {
    while (tr.until <= G.t) { const r = tr.route;
      if (tr.state === "dwell") { tr.to = tr.idx + tr.dir; tr.leg = r.legs[Math.min(tr.idx, tr.to)]; tr.state = "move"; tr.start = tr.until; tr.until += tr.leg.h;
        G.lf = G.lf * 0.98 + (tr.load.length / tr.cap) * 0.02; r.lf = r.lf * 0.94 + (tr.load.length / tr.cap) * 0.06; }
      else { tr.idx = tr.to; arrive(tr, tr.until); tr.state = "dwell"; tr.start = tr.until; tr.until += STOP_H; } }
  }
  function poisson(l) { const L = Math.exp(-l); let k = 0, p = 1; do { k++; p *= rng(); } while (p > L); return k - 1; }
  function step(dt) {
    G.t += dt;
    if (G.rate > 0) { for (let n = poisson(G.rate * dt); n > 0; n--) { const x = rng() * G.cum[G.cum.length - 1]; let lo = 0, hi = G.cum.length - 1;
      while (lo < hi) { const m = (lo + hi) >> 1; if (G.cum[m] < x) lo = m + 1; else hi = m; } const [o, d] = G.pairs[lo];
      cities[o].wait.push({ o, d, born: G.t, due: G.t + 8 + 4 * G.dist[o][d], path: planFrom(o, d) }); } }
    for (const r of G.routes) for (const tr of r.trucks) stepTruck(tr);
    let up = 0; for (const r of G.routes) { const c = upkeepOf(r) / 168 * dt; r.wkCost += c; up += c; } G.money -= up; G.week.upkeep += up;
    if (G.t >= G.sweepAt) { G.sweepAt = G.t + 0.5;
      for (const c of cities) if (c.wait.length) c.wait = c.wait.filter(s => { if (G.t > s.due + GRACE) { judge(false, s, false); c.cancels.push(G.t); return false; } return true; });
      for (const c of cities) while (c.cancels.length && c.cancels[0] < G.t - 24) c.cancels.shift();
      while (G.judged.length && G.judged[0][0] < G.t - 72) G.judged.shift(); }
    if (G.t >= G.weekNo * 168) { const w = G.week; G.reports.push({ week: G.weekNo, n: w.n, rate: w.n ? w.ok / w.n : 1, rev: w.rev, upkeep: w.upkeep, bonus: w.bonus, trucks: truckCount() });
      { const rp = G.reports[G.reports.length - 1], full = served().size === N && rp.rate >= GOAL; G.streak = full ? G.streak + 1 : 0;   // 完成条件: 全国接続かつ遵守率95%以上を4週連続
        if (full) { const pf = rp.rev - rp.upkeep; if (G.records.profit === null || pf > G.records.profit) G.records.profit = pf; if (G.records.trucks === null || rp.trucks < G.records.trucks) G.records.trucks = rp.trucks; }
        if (!G.completed && G.streak >= GOAL_WEEKS) { G.completed = { week: rp.week, trucks: rp.trucks }; G.fx.push({ type: "complete" }); } }
      for (const r of G.routes) { r.lastRev = r.wkRev; r.lastCost = r.wkCost; r.wkRev = 0; r.wkCost = 0; }
      G.log.push({ t: G.t, kind: "w", rep: G.reports[G.reports.length - 1] }); G.weekNo++; G.week = { n: 0, ok: 0, rev: 0, upkeep: 0, bonus: 0 }; }
  }
  const onTime = () => G.judged.length ? G.judged.reduce((s, j) => s + (j[1] ? 1 : 0), 0) / G.judged.length : null;
  const served = () => { const s = new Set(); G.routes.forEach(r => r.stops.forEach(c => s.add(c))); return s; };
  const truckCount = () => G.routes.reduce((s, r) => s + r.trucks.length, 0);

  // 都市の状態: 0=順調 1=混雑 2=遅延発生
  function cityStatus(c) {
    let overdue = 0, stranded = 0, top = null, tc = 0; const byR = {};
    for (const s of c.wait) { if (s.due < G.t) overdue++; const l = s.path && s.path[0]; if (!l) stranded++; else byR[l.r] = (byR[l.r] || 0) + 1; }
    for (const k in byR) if (byR[k] > tc) { tc = byR[k]; top = +k; }
    const n = c.wait.length, level = (overdue > 0 || c.cancels.length >= 2) ? 2 : n >= 15 ? 1 : 0;
    return { level, n, overdue, stranded, cancels: c.cancels.length, topRoute: top, topCount: tc };
  }
  // 新しくつなぐ都市の見込み需要（箱/週、概算）
  function forecast(newIdx) {
    const sv = served(), add = newIdx.filter(i => !sv.has(i)); if (!add.length) return 0; const all = new Set([...sv, ...add]); let s = 0;
    for (const o of all) for (const d of all) if (o !== d && (add.includes(o) || add.includes(d)) && G.dist[o][d] < Infinity) s += cities[o].mass * cities[d].mass / (1 + G.dist[o][d]);
    return s * DEMAND_K * 168;
  }
  rebuildRoads();
  // 開始時の路線（関東の一部だけ接続済み。水戸・宇都宮は未接続）
  addRoute(["神奈川", "東京", "埼玉", "群馬"].map(p => byPref[p]), true); addTruck(G.routes[0], true, G.routes[0].cycle / 2);
  addRoute(["千葉", "東京"].map(p => byPref[p]), true);
  return Object.assign(G, { step, addRoute, addTruck, removeTruck, removeRoute, unlockRegion, regionAdjacent, roadPath, headway, onTime, served, truckCount, byPref, cityStatus, forecast, sellTruck, editRoute, upkeepOf });
}
if (typeof module !== "undefined") module.exports = { createGame, REGIONS, CAP_BIG, TRUCK_PRICE_BIG, UPKEEP_BIG, GATE, GOAL, GOAL_WEEKS, TRUCK_SELL, FIRST_BONUS, OPEN_BONUS, TRUCK_PRICE, REGION_PRICE, CAP, UPKEEP_WEEK, MAX_STOPS };

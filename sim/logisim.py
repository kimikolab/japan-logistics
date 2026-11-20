"""ニッポン物流網 簡易シミュレーション（路線構成の比較用）
仮定はすべて仮置き。時間の単位はゲーム時間(h)。
"""
import heapq, random, itertools, sys, statistics as st

ROADS = {  # 道路区間と所要時間(h) ※概算の仮置き
    ("横浜", "東京"): 0.75, ("東京", "さいたま"): 0.75, ("さいたま", "宇都宮"): 1.25,
    ("宇都宮", "郡山"): 1.5, ("郡山", "仙台"): 1.5, ("東京", "水戸"): 1.5,
    ("水戸", "いわき"): 1.25, ("いわき", "仙台"): 2.25, ("さいたま", "高崎"): 1.25,
    ("高崎", "宇都宮"): 1.5, ("宇都宮", "水戸"): 1.25, ("郡山", "いわき"): 1.25,
}
STOP_H = 0.5      # 停車・荷役
CAP = 10          # 積載量
SORT_RATE = 10.0  # 仕分け 箱/時間（積み替えのみ）
GRACE = 6.0       # 納期超過後の猶予
HORIZON = 15 * 24
WARMUP = 24

def road_dist(cities):
    d = {a: {b: (0 if a == b else 1e9) for b in cities} for a in cities}
    for (a, b), h in ROADS.items():
        if a in d and b in d:
            d[a][b] = d[b][a] = h
    for k, i, j in itertools.product(cities, repeat=3):
        if d[i][k] + d[k][j] < d[i][j]:
            d[i][j] = d[i][k] + d[k][j]
    return d

ALL = ["横浜", "東京", "さいたま", "宇都宮", "郡山", "仙台", "水戸", "いわき", "高崎"]
DIST = road_dist(ALL)

def deadline_hours(o, d):
    return 8 + 4 * DIST[o][d]   # 東京-さいたま 11h / 東京-仙台 28h / 横浜-仙台 31h

class Route:
    def __init__(self, rid, stops, trucks):
        self.id, self.stops, self.n = rid, stops, trucks
        self.leg = [DIST[a][b] for a, b in zip(stops, stops[1:])]
        self.cycle = 2 * sum(self.leg) + 2 * (len(stops) - 1) * STOP_H
        self.headway = self.cycle / trucks

def plan_paths(routes, cities):
    """静的経路表: (発,着) -> [(route, 乗車idx, 降車idx), ...]。乗り継ぎ待ち=運行間隔の半分で概算"""
    import math
    table = {}
    for o in cities:
        # Dijkstra over cities; 辺 = 同一路線上の任意2停車間の乗車
        best = {o: (0.0, [])}
        pq = [(0.0, 0, o, [])]
        cnt = 0
        done = set()
        while pq:
            c, _, u, path = heapq.heappop(pq)
            if u in done:
                continue
            done.add(u)
            for r in routes:
                if u not in r.stops:
                    continue
                i = r.stops.index(u)
                for j, v in enumerate(r.stops):
                    if j == i:
                        continue
                    lo, hi = min(i, j), max(i, j)
                    ride = sum(r.leg[lo:hi]) + (hi - lo - 1) * STOP_H
                    wait = r.headway / 2
                    xfer = (1.0 if path else 0.0)
                    nc = c + wait + ride + STOP_H + xfer
                    if v not in best or nc < best[v][0] - 1e-9:
                        best[v] = (nc, path + [(r.id, i, j)])
                        cnt += 1
                        heapq.heappush(pq, (nc, cnt, v, best[v][1]))
        for d, (c, p) in best.items():
            if d != o:
                table[(o, d)] = p
    return table

def simulate(route_defs, cities, weights, rate, seed):
    rnd = random.Random(seed)
    routes = [Route(i, s, n) for i, (s, n) in enumerate(route_defs)]
    table = plan_paths(routes, cities)
    pairs = list(weights.keys())
    w = [weights[p] for p in pairs]
    # 荷物生成
    ships = []
    t = 0.0
    while True:
        t += rnd.expovariate(rate)
        if t >= HORIZON:
            break
        o, d = rnd.choices(pairs, w)[0]
        ships.append({"t": t, "o": o, "d": d, "due": t + deadline_hours(o, d),
                      "path": list(table.get((o, d), [])), "done": None, "ready": t})
    waiting = {(c, r.id): [] for c in cities for r in routes}
    sort_free = {c: 0.0 for c in cities}
    ev = []
    cnt = 0
    for i, s in enumerate(ships):
        heapq.heappush(ev, (s["t"], cnt, "gen", i)); cnt += 1
    trucks = []
    for r in routes:
        for k in range(r.n):
            trucks.append({"r": r, "idx": 0, "dir": 1, "load": []})
            heapq.heappush(ev, (k * r.headway, cnt, "arr", len(trucks) - 1)); cnt += 1
    carried = 0.0; offered = 0.0
    while ev:
        now, _, kind, x = heapq.heappop(ev)
        if now > HORIZON + 48:
            break
        if kind == "gen":
            s = ships[x]
            if s["path"]:
                rid = s["path"][0][0]
                waiting[(s["o"], rid)].append(x)
            continue
        tr = trucks[x]; r = tr["r"]; city = r.stops[tr["idx"]]
        # 荷下ろし
        keep = []
        for si in tr["load"]:
            s = ships[si]
            if s["path"][0][2] == tr["idx"]:
                s["path"].pop(0)
                if not s["path"]:
                    s["done"] = now
                else:  # 積み替え: 仕分け待ち
                    start = max(now, sort_free[city])
                    sort_free[city] = start + 1.0 / SORT_RATE
                    s["ready"] = sort_free[city]
                    waiting[(city, s["path"][0][0])].append(si)
            else:
                keep.append(si)
        tr["load"] = keep
        # 折り返し
        if tr["idx"] == len(r.stops) - 1:
            tr["dir"] = -1
        elif tr["idx"] == 0:
            tr["dir"] = 1
        # 積み込み: 進行方向が合う荷物。納期内を納期順で優先、超過分は後回し、猶予切れは破棄
        q = waiting[(city, r.id)]
        cand, rest = [], []
        for si in q:
            s = ships[si]
            if now > s["due"] + GRACE:
                continue  # キャンセル
            ok = s["ready"] <= now and (s["path"][0][2] - tr["idx"]) * tr["dir"] > 0
            (cand if ok else rest).append(si)
        cand.sort(key=lambda si: (ships[si]["due"] < now, ships[si]["due"]))
        room = CAP - len(tr["load"])
        tr["load"] += cand[:room]
        waiting[(city, r.id)] = rest + cand[room:]
        # 次の停車へ
        nxt = tr["idx"] + tr["dir"]
        leg = r.leg[min(tr["idx"], nxt)]
        if WARMUP < now < HORIZON:
            carried += len(tr["load"]) * leg; offered += CAP * leg
        tr["idx"] = nxt
        heapq.heappush(ev, (now + STOP_H + leg, cnt, "arr", x)); cnt += 1
    judged = [s for s in ships if WARMUP <= s["t"] and s["due"] <= HORIZON]
    ontime = sum(1 for s in judged if s["done"] is not None and s["done"] <= s["due"])
    return ontime / max(1, len(judged)), carried / max(1e-9, offered)

def make_weights(cities, pattern):
    w = {}
    for o in cities:
        for d in cities:
            if o == d:
                continue
            dist = DIST[o][d]
            if pattern == "均等":
                v = 1.0
            elif pattern == "東京発集中":
                v = 6.0 if o == "東京" else 1.0
            elif pattern == "長距離中心":
                v = dist ** 2
            elif pattern == "近距離中心":
                v = 1.0 / dist ** 2
            w[(o, d)] = v
    return w

SPINE = ["横浜", "東京", "さいたま", "宇都宮", "郡山", "仙台"]
STAGES = {
    "6都市(一本道)": (SPINE, {
        "A 長距離1本x4台": [(SPINE, 4)],
        "B 長距離2本x2台": [(SPINE, 2), (["東京", "仙台"], 2)],
        "C 短距離3本": [(["横浜", "東京", "さいたま"], 2), (["さいたま", "宇都宮", "郡山"], 1), (["郡山", "仙台"], 1)],
    }),
    "9都市(ループあり)": (ALL, {
        "A 長距離1本x4台": [(SPINE, 4)],
        "B 長距離2本x2台": [(["東京", "さいたま", "宇都宮", "郡山", "仙台"], 2), (["横浜", "東京", "水戸", "いわき", "仙台"], 2)],
        "C 短距離3本": [(["横浜", "東京", "さいたま", "高崎"], 1), (["東京", "水戸", "いわき"], 1), (["さいたま", "宇都宮", "郡山", "仙台"], 2)],
    }),
}

if __name__ == "__main__":
    N = int(sys.argv[1]) if len(sys.argv) > 1 else 100
    for stage, (cities, configs) in STAGES.items():
        for rate in (1.0, 2.0, 3.0):
            print(f"\n## {stage}  需要 {rate} 箱/時")
            print("| 需要パターン | " + " | ".join(configs) + " |")
            print("|---|" + "---|" * len(configs))
            for pat in ("均等", "東京発集中", "長距離中心", "近距離中心"):
                wts = make_weights(cities, pat)
                cells = []
                for name, rd in configs.items():
                    res = [simulate(rd, cities, wts, rate, s) for s in range(N)]
                    cells.append(f"{100*st.mean(r[0] for r in res):.0f}% (積載{100*st.mean(r[1] for r in res):.0f}%)")
                print(f"| {pat} | " + " | ".join(cells) + " |")

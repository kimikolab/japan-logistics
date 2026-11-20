"""ニッポン物流網 簡易シミュレーター v2（長期経営型の検証用）
- 定常状態の計測用モデル。ゲームの進行モデル（15日生存など）ではない。
- 数値はすべて仮置き。道路時間は高速道路ベースの概算で未検証。
"""
import heapq, random, itertools, statistics as st

STOP_H = 0.5   # 停車・荷役(h)
CAP = 10       # 積載量(箱)
GRACE = 6.0    # 納期超過後の猶予(h)
MAX_STOPS = 6

# 9都市（検証A。前回と同じ道路網）
ROADS9 = {
    ("横浜", "東京"): 0.75, ("東京", "さいたま"): 0.75, ("さいたま", "宇都宮"): 1.25,
    ("宇都宮", "郡山"): 1.5, ("郡山", "仙台"): 1.5, ("東京", "水戸"): 1.5,
    ("水戸", "いわき"): 1.25, ("いわき", "仙台"): 2.25, ("さいたま", "高崎"): 1.25,
    ("高崎", "宇都宮"): 1.5, ("宇都宮", "水戸"): 1.25, ("郡山", "いわき"): 1.25,
}
# 25都市（検証B）
ROADS25 = {
    ("東京", "横浜"): 0.75, ("東京", "さいたま"): 0.75, ("東京", "千葉"): 0.75,
    ("さいたま", "宇都宮"): 1.25, ("東京", "水戸"): 1.5, ("千葉", "水戸"): 1.5,
    ("さいたま", "高崎"): 1.25, ("高崎", "宇都宮"): 1.5, ("宇都宮", "水戸"): 1.25,
    ("東京", "八王子"): 0.75, ("横浜", "八王子"): 1.0, ("八王子", "さいたま"): 1.0,
    ("横浜", "小田原"): 1.0,
    ("八王子", "甲府"): 1.25, ("甲府", "松本"): 1.5, ("松本", "長野"): 1.0,
    ("高崎", "長野"): 1.5, ("長野", "上越"): 1.0, ("上越", "長岡"): 1.0,
    ("高崎", "長岡"): 2.0, ("長岡", "新潟"): 1.0,
    ("宇都宮", "郡山"): 1.5, ("郡山", "福島"): 0.75, ("福島", "仙台"): 1.0,
    ("水戸", "いわき"): 1.25, ("いわき", "郡山"): 1.25, ("いわき", "仙台"): 2.25,
    ("郡山", "会津若松"): 1.0, ("会津若松", "新潟"): 1.5, ("福島", "山形"): 1.5,
    ("仙台", "山形"): 1.0, ("仙台", "盛岡"): 2.25, ("盛岡", "秋田"): 1.75,
    ("山形", "秋田"): 3.0, ("盛岡", "八戸"): 1.5, ("盛岡", "青森"): 2.25,
    ("八戸", "青森"): 1.5, ("秋田", "青森"): 2.5, ("新潟", "山形"): 3.0,
}
MASS = {  # 需要の重み（人口規模を参考にした仮値）
    "東京": 10, "横浜": 6, "さいたま": 4, "千葉": 4, "宇都宮": 2, "水戸": 1.5, "高崎": 2,
    "八王子": 2, "小田原": 1, "甲府": 1, "松本": 1.5, "長野": 1.5, "上越": 1, "長岡": 1,
    "新潟": 3, "郡山": 1.5, "福島": 1.5, "仙台": 5, "山形": 1.5, "盛岡": 1.5, "秋田": 1.5,
    "青森": 1.5, "いわき": 1.5, "会津若松": 1, "八戸": 1,
}
STAGE_CITIES = [
    ["東京", "横浜", "さいたま", "千葉", "宇都宮"],
    ["水戸", "高崎", "八王子", "小田原"],
    ["甲府", "松本", "長野", "上越", "長岡", "新潟"],
    ["郡山", "福島", "仙台", "山形", "盛岡", "秋田", "青森", "いわき", "会津若松", "八戸"],
]
STAGE_TRUCKS = [4, 8, 12, 20]


class Net:
    def __init__(self, cities, roads):
        self.cities = list(cities)
        cs = set(cities)
        self.adj = {c: {} for c in cities}
        d = {a: {b: (0.0 if a == b else 1e9) for b in cities} for a in cities}
        for (a, b), h in roads.items():
            if a in cs and b in cs:
                d[a][b] = d[b][a] = h
                self.adj[a][b] = self.adj[b][a] = h
        for k in cities:
            dk = d[k]
            for i in cities:
                dik = d[i][k]
                if dik >= 1e9:
                    continue
                di = d[i]
                for j in cities:
                    if dik + dk[j] < di[j]:
                        di[j] = dik + dk[j]
        self.dist = d

    def road_path(self, a, b):
        """道路上の最短経路（都市列）"""
        pq = [(0.0, a, [a])]; seen = set()
        while pq:
            c, u, p = heapq.heappop(pq)
            if u == b:
                return p
            if u in seen:
                continue
            seen.add(u)
            for v, h in self.adj[u].items():
                if v not in seen:
                    heapq.heappush(pq, (c + h, v, p + [v]))
        return None


def deadline_hours(dist):
    return 8 + 4 * dist


class Route:
    def __init__(self, rid, stops, trucks, net):
        self.id, self.stops, self.n = rid, list(stops), trucks
        self.leg = [net.dist[a][b] for a, b in zip(stops, stops[1:])]
        self.cycle = 2 * sum(self.leg) + 2 * (len(stops) - 1) * STOP_H
        self.headway = self.cycle / trucks


def plan_paths(routes, cities):
    """静的経路表。乗り継ぎ待ち＝運行間隔の半分で概算。"""
    by_city = {}
    for r in routes:
        for i, c in enumerate(r.stops):
            by_city.setdefault(c, []).append((r, i))
    table = {}
    for o in cities:
        best = {o: (0.0, [])}
        pq = [(0.0, 0, o, [])]; cnt = 0; done = set()
        while pq:
            c, _, u, path = heapq.heappop(pq)
            if u in done:
                continue
            done.add(u)
            for r, i in by_city.get(u, ()):
                base = c + r.headway / 2 + STOP_H + (1.0 if path else 0.0)
                acc = 0.0
                for j in range(i + 1, len(r.stops)):
                    acc += r.leg[j - 1] + (STOP_H if j - 1 > i else 0.0)
                    v = r.stops[j]
                    if v not in best or base + acc < best[v][0] - 1e-9:
                        best[v] = (base + acc, path + [(r.id, i, j)]); cnt += 1
                        heapq.heappush(pq, (base + acc, cnt, v, best[v][1]))
                acc = 0.0
                for j in range(i - 1, -1, -1):
                    acc += r.leg[j] + (STOP_H if j + 1 < i else 0.0)
                    v = r.stops[j]
                    if v not in best or base + acc < best[v][0] - 1e-9:
                        best[v] = (base + acc, path + [(r.id, i, j)]); cnt += 1
                        heapq.heappush(pq, (base + acc, cnt, v, best[v][1]))
        for d, (c, p) in best.items():
            if d != o:
                table[(o, d)] = p
    return table


class Demand:
    def __init__(self, weights):
        self.pairs = list(weights)
        self.cum = list(itertools.accumulate(weights[p] for p in self.pairs))


def gravity(cities, net, mass=MASS):
    return Demand({(o, d): mass[o] * mass[d] / (1 + net.dist[o][d])
                   for o in cities for d in cities if o != d})


FEE_BASE, FEE_PER_H, LATE_RATIO = 10.0, 4.0, 0.5   # 運賃(仮): 10G + 4G×道路時間。遅延は半額、キャンセルは0


def simulate(route_defs, net, demand, rate, seed, sort_rate=20.0, days=7, warm=1, tail=None):
    rnd = random.Random(seed)
    cities = net.cities
    routes = [Route(i, s, n, net) for i, (s, n) in enumerate(route_defs)]
    table = plan_paths(routes, cities)
    H = days * 24; W = warm * 24
    ships = []; t = 0.0
    while True:
        t += rnd.expovariate(rate)
        if t >= H:
            break
        o, d = rnd.choices(demand.pairs, cum_weights=demand.cum)[0]
        ships.append([t, o, d, t + deadline_hours(net.dist[o][d]), list(table.get((o, d), ())), None, t, 0.0, 0])
        #             0  1  2  3 due                                4 path                        5 done 6 ready/arr 7 xferwait 8 nxfer
    waiting = {}
    for r in routes:
        for c in r.stops:
            waiting[(c, r.id)] = []
    sort_free = {c: 0.0 for c in cities}
    ev = []; cnt = 0
    for i, s in enumerate(ships):
        ev.append((s[0], cnt, 0, i)); cnt += 1
    trucks = []
    for r in routes:
        for k in range(r.n):
            trucks.append([r, 0, 1, []])
            ev.append((k * r.headway, cnt, 1, len(trucks) - 1)); cnt += 1
    heapq.heapify(ev)
    carried = offered = 0.0
    END = H + 72
    while ev:
        now, _, kind, x = heapq.heappop(ev)
        if now > END:
            break
        if kind == 0:
            s = ships[x]
            if s[4]:
                waiting[(s[1], s[4][0][0])].append(x)
            continue
        tr = trucks[x]; r = tr[0]; idx = tr[1]; city = r.stops[idx]
        keep = []
        for si in tr[3]:
            s = ships[si]
            if s[4][0][2] == idx:
                s[4].pop(0)
                if not s[4]:
                    s[5] = now
                else:
                    start = max(now, sort_free[city])
                    sort_free[city] = start + 1.0 / sort_rate
                    s[6] = now; s[8] += 1
                    s.append(sort_free[city]) if len(s) == 9 else s.__setitem__(9, sort_free[city])
                    waiting[(city, s[4][0][0])].append(si)
            else:
                keep.append(si)
        tr[3] = keep
        if idx == len(r.stops) - 1:
            tr[2] = -1
        elif idx == 0:
            tr[2] = 1
        dr = tr[2]
        q = waiting[(city, r.id)]
        cand = []; rest = []
        for si in q:
            s = ships[si]
            if now > s[3] + GRACE:
                continue
            avail = s[9] if len(s) > 9 and s[8] > 0 else s[0]
            if avail <= now and (s[4][0][2] - idx) * dr > 0:
                cand.append(si)
            else:
                rest.append(si)
        if len(cand) > CAP - len(keep):
            cand.sort(key=lambda si: (ships[si][3] < now, ships[si][3]))
        room = CAP - len(keep)
        for si in cand[:room]:
            s = ships[si]
            if s[8] > 0:
                s[7] += now - s[6]
        tr[3] = keep + cand[:room]
        waiting[(city, r.id)] = rest + cand[room:]
        nxt = idx + dr
        leg = r.leg[min(idx, nxt)]
        if W < now < H:
            carried += len(tr[3]) * leg; offered += CAP * leg
        tr[1] = nxt
        heapq.heappush(ev, (now + STOP_H + leg, cnt, 1, x)); cnt += 1
    if tail:   # 経済計測: 発生時刻で区切り、全件の結末が出るまで待つ
        judged = [s for s in ships if W <= s[0] <= H - tail]
    else:
        judged = [s for s in ships if s[0] >= W and s[3] <= H]
    n = max(1, len(judged))
    dl = [s for s in judged if s[5] is not None]
    ontime = sum(1 for s in dl if s[5] <= s[3])
    xf = [s for s in dl if s[8] > 0]
    rev = 0.0
    if tail:
        for s in dl:
            fee = FEE_BASE + FEE_PER_H * net.dist[s[1]][s[2]]
            rev += fee if s[5] <= s[3] else fee * LATE_RATIO
        rev = rev / (H - tail - W) * 168.0   # 週あたり
    return {
        "rev": rev,
        "ontime": ontime / n,
        "load": carried / max(1e-9, offered),
        "time": st.mean(s[5] - s[0] for s in dl) if dl else float("nan"),
        "xwait": (sum(s[7] for s in xf) / sum(s[8] for s in xf)) if xf else 0.0,
        "xfers": sum(s[8] for s in dl) / max(1, len(dl)),
        "undeliv": 1 - len(dl) / n,
    }


def evaluate(route_defs, net, demand, rate, seeds, **kw):
    rs = [simulate(route_defs, net, demand, rate, s, **kw) for s in seeds]
    return {k: st.mean(r[k] for r in rs) for k in rs[0]}


def score(m):
    return (round(m["ontime"], 4), -round(m["time"], 2) if m["time"] == m["time"] else -1e9)


# ---------- 路線の自動探索（山登り法） ----------
def mutate(routes, frozen, net, rnd):
    """routes: [(stops tuple, trucks)]。先頭 frozen 本は変更不可。"""
    R = [(list(s), n) for s, n in routes]
    mut = list(range(frozen, len(R)))
    if not mut:
        return None
    op = rnd.choice(["ext", "ext", "trim", "drop", "move", "move", "new", "new", "del", "ins"])
    if op in ("move", "new"):   # 車両を出せる路線から選ぶ
        donors = [m for m in mut if R[m][1] >= 2]
        if not donors:
            return None
        i = rnd.choice(donors)
    else:
        i = rnd.choice(mut)
    s, n = R[i]
    if op == "ext" and len(s) < MAX_STOPS:
        end = rnd.choice([0, -1])
        opts = [c for c in net.adj[s[end]] if c not in s]
        if not opts:
            return None
        c = rnd.choice(opts)
        s.insert(0, c) if end == 0 else s.append(c)
    elif op == "trim" and len(s) > 2:
        s.pop(rnd.choice([0, -1]))
    elif op == "drop" and len(s) > 2:
        s.pop(rnd.randrange(1, len(s) - 1))
    elif op == "ins" and len(s) < MAX_STOPS:
        k = rnd.randrange(len(s) - 1)
        p = net.road_path(s[k], s[k + 1])
        mid = [c for c in p[1:-1] if c not in s]
        if not mid:
            return None
        s.insert(k + 1, rnd.choice(mid))
    elif op == "move" and len(mut) > 1:
        j = rnd.choice([m for m in mut if m != i])
        if n < 2:
            return None
        R[i] = (s, n - 1); R[j] = (R[j][0], R[j][1] + 1)
    elif op == "new":
        if n < 2:
            return None
        a = rnd.choice(net.cities); b = rnd.choice(list(net.adj[a]))
        R[i] = (s, n - 1); R.append(([a, b], 1))
    elif op == "del" and len(mut) > 1:
        j = rnd.choice([m for m in mut if m != i])
        R[j] = (R[j][0], R[j][1] + n); R.pop(i)
    else:
        return None
    return [(tuple(s), n) for s, n in R]


def optimize(routes, frozen, net, demand, rate, iters, seeds=(1, 2), rseed=0, **kw):
    rnd = random.Random(rseed)
    cur = [(tuple(s), n) for s, n in routes]
    cs = score(evaluate(cur, net, demand, rate, seeds, **kw))
    for _ in range(iters):
        cand = mutate(cur, frozen, net, rnd)
        if cand is None:
            continue
        sc = score(evaluate(cand, net, demand, rate, seeds, **kw))
        if sc >= cs:
            cur, cs = cand, sc
    return cur


def connect_new(prev_routes, net, new_cities, new_trucks):
    """維持案の初期形: 既存路線はそのまま、新都市を最寄りの既存都市へつなぐ路線を追加。"""
    covered = {c for s, _ in prev_routes for c in s}
    hub = "東京"
    todo = sorted((c for c in new_cities if c not in covered), key=lambda c: -net.dist[hub][c])
    added = []
    for c in todo:
        if c in covered:
            continue
        tgt = min(covered, key=lambda k: net.dist[c][k])
        p = net.road_path(c, tgt)[:MAX_STOPS]
        added.append((tuple(p), 1)); covered |= set(p)
    while len(added) > new_trucks:   # 路線が多すぎる場合は短いものを落とす
        added.sort(key=lambda r: len(r[0])); added.pop(0)
    k = 0
    while sum(n for _, n in added) < new_trucks:
        added[k % len(added)] = (added[k % len(added)][0], added[k % len(added)][1] + 1); k += 1
    return list(prev_routes) + added


def fmt(routes):
    return " / ".join(f"{'-'.join(s)}×{n}" for s, n in routes)

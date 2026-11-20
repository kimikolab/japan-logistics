"""資金モデルの検証: 9都市・首都圏集中4倍・総需要16箱/時（固定）
固定路線での増減車 と 路線再編 を、同じ需要で比較する。"""
import sys, json, itertools, random
from logisim2 import *
C9=["横浜","東京","さいたま","宇都宮","郡山","仙台","水戸","いわき","高崎"]
net=Net(C9,ROADS9); metro={"横浜","東京","さいたま"}
D=Demand({(o,d):(4.0 if o in metro and d in metro else 1.0) for o in C9 for d in C9 if o!=d})
RATE=16.0; KW=dict(days=9,warm=1,tail=48); SE=(1,2,3); EV=range(100,130)
SP=("横浜","東京","さいたま","宇都宮","郡山","仙台")
BASE={"L":[SP,("高崎","さいたま","東京","水戸","いわき","仙台")],
 "T":[SP,("横浜","東京","さいたま"),("高崎","さいたま"),("東京","水戸","いわき","郡山")],
 "S":[("横浜","東京","さいたま"),("さいたま","高崎"),("さいたま","宇都宮","郡山"),("郡山","仙台"),("東京","水戸","いわき"),("いわき","郡山")]}
def ev(r,seeds): return evaluate(r,net,D,RATE,seeds,**KW)
def sc(r): m=ev(r,SE); return (round(m["rev"]), -round(m["time"],2))
def alloc(shapes,N,start=None):
    k=len(shapes); a=start[:] if start else [1]*k
    i=0
    while sum(a)<N: a[i%k]+=1; i+=1
    while sum(a)>N:
        j=max(range(k),key=lambda x:a[x]); a[j]-=1
    cur=sc(list(zip(shapes,a))); imp=True
    while imp:
        imp=False
        for i,j in itertools.permutations(range(k),2):
            if a[i]<2: continue
            b=a[:]; b[i]-=1; b[j]+=1; s=sc(list(zip(shapes,b)))
            if s>cur: a,cur,imp=b,s,True
    return a
def climb(r,iters,rs):
    rnd=random.Random(rs); cur=[(tuple(s),n) for s,n in r]; cs=sc(cur)
    for _ in range(iters):
        c=mutate(cur,0,net,rnd)
        if c is None: continue
        s=sc(c)
        if s>=cs: cur,cs=c,s
    return cur
def drop_one(r):
    best=None
    for i,(s,n) in enumerate(r):
        c=[x for x in r]
        if n>=2: c[i]=(s,n-1)
        elif len(r)>1: c.pop(i)
        else: continue
        v=sc(c)
        if best is None or v>best[0]: best=(v,c)
    return best[1]
def rec(r):
    m=ev(r,EV); return {"N":sum(n for _,n in r),"routes":fmt(r),"nroutes":len(r),**{k:round(v,4) for k,v in m.items()}}
name=sys.argv[1]; IT=int(sys.argv[2]); shapes=BASE[name]; out={"fixed":{}, "reorg":{}}
a=None
for N in range(len(shapes),17):
    a=alloc(shapes,N,a); out["fixed"][N]=rec(list(zip(shapes,a)))
    x=out["fixed"][N]; print(f"[{name}] 固定 N={N:2d} 遵守{100*x['ontime']:5.1f}% 収入{x['rev']:7.0f} 積載{100*x['load']:3.0f}% 配送{x['time']:.1f}h {a}",flush=True)
# 再編: 16台から1台ずつ減らしながら探索（各台数で固定路線の解からも探索し、良い方を採用）
cur=climb(list(zip(shapes,alloc(shapes,16))),IT,0)
for N in range(16,3,-1):
    if N<16: cur=climb(drop_one(cur),IT,N)
    if str(N) in map(str,out["fixed"]):
        alt=climb([(tuple(s),n) for s,n in (lambda f: [(tuple(p.split("×")[0].split("-")),int(p.split("×")[1])) for p in f.split(" / ")])(out["fixed"][N]["routes"])],IT,100+N)
        if sc(alt)>sc(cur): cur=alt
    out["reorg"][N]=rec(cur); x=out["reorg"][N]
    print(f"[{name}] 再編 N={N:2d} 遵守{100*x['ontime']:5.1f}% 収入{x['rev']:7.0f} 積載{100*x['load']:3.0f}% 配送{x['time']:.1f}h {x['routes']}",flush=True)
json.dump(out,open(f"econ_{name}.json","w"),ensure_ascii=False,indent=1)

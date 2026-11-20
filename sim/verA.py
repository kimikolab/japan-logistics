import sys, itertools, statistics as st
from logisim2 import *
C9=["横浜","東京","さいたま","宇都宮","郡山","仙台","水戸","いわき","高崎"]
net=Net(C9,ROADS9)
SP=("横浜","東京","さいたま","宇都宮","郡山","仙台")
CFG={
 "L 長距離中心(2本)":[SP,("高崎","さいたま","東京","水戸","いわき","仙台")],
 "T 幹線+区間便(4本)":[SP,("横浜","東京","さいたま"),("高崎","さいたま"),("東京","水戸","いわき","郡山")],
 "S 短距離中心(6本)":[("横浜","東京","さいたま"),("さいたま","高崎"),("さいたま","宇都宮","郡山"),("郡山","仙台"),("東京","水戸","いわき"),("いわき","郡山")],
}
metro={"横浜","東京","さいたま"}
def dem(f): return Demand({(o,d):(f if o in metro and d in metro else 1.0) for o in C9 for d in C9 if o!=d})
def alloc(shapes,N,D,rate,sort_rate):
    k=len(shapes); a=[1]*k
    for i in range(N-k): a[i%k]+=1
    ev=lambda a: score(evaluate(list(zip(shapes,a)),net,D,rate,(1,2,3),sort_rate=sort_rate))
    cur=ev(a); improved=True
    while improved:
        improved=False
        for i,j in itertools.permutations(range(k),2):
            if a[i]<2: continue
            b=a[:]; b[i]-=1; b[j]+=1; s=ev(b)
            if s>cur: a,cur,improved=b,s,True
    return a
per=float(sys.argv[1]); sr=float(sys.argv[2])
print(f"### 需要 {per} 箱/時/台, 仕分け {sr} 箱/時")
for N in (6,8,12,16):
    for f in (1,4,10):
        D=dem(f); rate=per*N
        for name,shapes in CFG.items():
            a=alloc(shapes,N,D,rate,sr)
            m=evaluate(list(zip(shapes,a)),net,D,rate,range(10,40),sort_rate=sr)
            print(f"N={N:2d} 集中x{f:<2d} {name:14s} 配分{a} 遵守{100*m['ontime']:5.1f}% 積載{100*m['load']:4.0f}% 配送{m['time']:5.1f}h 乗継待{m['xwait']:4.1f}h 乗継{m['xfers']:.2f}回", flush=True)

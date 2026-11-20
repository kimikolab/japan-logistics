import sys, time, json
from logisim2 import *
c=float(sys.argv[1]); IT=[int(x) for x in sys.argv[2].split(",")]; tag=sys.argv[3]
SE=(1,2,3)
def stage(k):
    cities=[x for st_ in STAGE_CITIES[:k+1] for x in st_]
    net=Net(cities,ROADS25); return net, gravity(cities,net), c*STAGE_TRUCKS[k]
def show(label,r,k):
    net,D,rate=stage(k); m=evaluate(r,net,D,rate,range(100,130))
    served=len({x for s,_ in r for x in s})
    print(f"[{tag}] 段階{k+1} {label}: 遵守{100*m['ontime']:.1f}% 積載{100*m['load']:.0f}% 配送{m['time']:.1f}h 乗継待{m['xwait']:.1f}h 乗継{m['xfers']:.2f}回 未達{100*m['undeliv']:.1f}% 接続{served}/{len(net.cities)}都市 路線{len(r)}本\n    {fmt(r)}",flush=True)
    m["served"]=served; m["routes"]=len(r); return m
def restricted(prev,k,rs):
    net,D,rate=stage(k); nt=STAGE_TRUCKS[k]-STAGE_TRUCKS[k-1]
    x=connect_new(prev,net,STAGE_CITIES[k],nt)
    for i in range(2): x=optimize(x,len(prev),net,D,rate,IT[k],seeds=SE,rseed=rs+i)
    return x
out={}
net,D,rate=stage(0)
R=optimize([(("横浜","東京","さいたま","宇都宮"),3),(("東京","千葉"),1)],0,net,D,rate,IT[0],seeds=SE)
out["1"]={"R":show("最適化",R,0)}
N=R
for k in (1,2,3):
    net,D,rate=stage(k); t0=time.time()
    K2=restricted(R,k,k*10)
    K=optimize(K2,len(R),net,D,rate,IT[k],seeds=SE,rseed=k*10+5)
    Rn=optimize(K2,0,net,D,rate,IT[k],seeds=SE,rseed=k*10+6)
    changed=sum(1 for r in R if r not in Rn)
    o={"keep":show("維持(前段階の路線は固定)",K,k),"reorg":show(f"再編(旧路線{len(R)}本中{changed}本を変更)",Rn,k),"changed":changed,"old":len(R)}
    if k>=2:
        Nn=restricted(N,k,k*10+7); Nn=optimize(Nn,len(N),net,D,rate,IT[k],seeds=SE,rseed=k*10+9)
        o["never"]=show("一度も再編しない",Nn,k); N=Nn
    else: N=K
    out[str(k+1)]=o; R=Rn
    print(f"   ({time.time()-t0:.0f}s)",flush=True)
    json.dump(out,open(f"B2_{tag}.json","w"),ensure_ascii=False)

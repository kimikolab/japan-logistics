import sys, time, json
from logisim2 import *
trucks=int(sys.argv[1]); IT=int(sys.argv[2]); tag=sys.argv[3]; RATE=25.0
def parse(s): return [(tuple(a.split("×")[0].split("-")),int(a.split("×")[1])) for a in s.split(" / ")]
R3=parse("横浜-東京-さいたま-宇都宮×3 / 東京-千葉×1 / 高崎-さいたま×1 / 小田原-横浜×1 / 千葉-水戸-宇都宮×1 / 八王子-東京×1 / 新潟-長岡-高崎×1 / 松本-長野-上越-長岡×1 / 宇都宮-高崎-長野×1 / 松本-甲府-八王子×1")
cities=[x for s in STAGE_CITIES for x in s]; net=Net(cities,ROADS25); D=gravity(cities,net); SE=(1,2,3)
def show(label,r):
    m=evaluate(r,net,D,RATE,range(100,130)); served=len({x for s,_ in r for x in s})
    print(f"[{tag}] {label}: 遵守{100*m['ontime']:.1f}% 積載{100*m['load']:.0f}% 配送{m['time']:.1f}h 乗継待{m['xwait']:.1f}h 乗継{m['xfers']:.2f}回 未達{100*m['undeliv']:.1f}% 接続{served}/25 路線{len(r)}本\n    {fmt(r)}",flush=True)
t0=time.time()
x=connect_new(R3,net,STAGE_CITIES[3],trucks-12); show("初期(新都市を最寄りへ接続しただけ)",x)
for i in range(2): x=optimize(x,len(R3),net,D,RATE,IT,seeds=SE,rseed=i)
show("維持・途中",x)
K=optimize(x,len(R3),net,D,RATE,IT,seeds=SE,rseed=5); show("維持(関東甲信越の10路線は固定)",K)
Rn=optimize(x,0,net,D,RATE,IT,seeds=SE,rseed=6)
ch=sum(1 for r in R3 if r not in Rn); show(f"再編(旧10路線中{ch}本を変更)",Rn)
print(f"({time.time()-t0:.0f}s)")

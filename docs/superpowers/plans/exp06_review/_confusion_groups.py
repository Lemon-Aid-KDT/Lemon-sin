"""혼동군 추출 — 서로 양방향으로 헷갈리는 클래스 클러스터.

exp11(selectstar 편향 없는 AIHub-only) 모델로 실환경(wild+realworld val) 혼동행렬 →
대칭 그래프 클러스터링(union-find) → 혼동군. 각 군에서 유지/병합 후보 제안.
"""
import sys, glob, os, re
sys.stdout.reconfigure(encoding="utf-8")
from collections import defaultdict, Counter
from pathlib import Path
import cv2, numpy as np, yaml
from ultralytics import YOLO

AIHUB = Path(r"C:\Lemon-sin\data\food_images\processed\aihub_yolo_taxo59_bal1500")
WILD = Path(r"D:\Deeplearning\lemon\data\raw\friend_contributed\wild_keep_dedup_list.txt")
WBASE = Path(r"D:\Deeplearning\lemon\data\raw\friend_contributed\inbox")
RW = Path(r"C:\Lemon-sin\data\food_images\processed\realworld_collected_v1\val")
W = r"C:\Lemon-sin\runs\food_yolo\exp11_yolo26s_taxo59bal1500_pc1_s42_b16_w8_cache_disk_det_true\weights\best.pt"
DROPPED = {"cold-ramen", "nagasaki-champon", "tteokbokki-jajang", "tteokbokki-cream-rose"}

names = yaml.safe_load((AIHUB / "data.yaml").read_text(encoding="utf-8"))["names"]
names = names if isinstance(names, list) else [names[i] for i in sorted(names)]

items = []  # (gt_name, image_path)
for ln in WILD.read_text(encoding="utf-8").splitlines():
    if ln.strip():
        fp, c = ln.split("\t"); items.append((c, WBASE / fp))
for lf in glob.glob(str(RW / "labels" / "*.txt")):
    line = open(lf).readline().split()
    if line:
        gt = names[int(line[0])]
        img = RW / "images" / (Path(lf).stem + ".jpg")
        if img.exists():
            items.append((gt, img))

m = YOLO(W)
conf = defaultdict(Counter)
for cls, p in items:
    if cls in DROPPED:
        continue
    im = cv2.imread(str(p))
    if im is None:
        continue
    r = m.predict(im, conf=0.01, verbose=False, device="cpu")[0]
    pred = m.names[int(r.boxes.cls[int(np.argmax(r.boxes.conf.tolist()))])] if len(r.boxes) else "(none)"
    conf[cls][pred] += 1

N = {c: sum(v.values()) for c, v in conf.items()}
recog = {c: conf[c].get(c, 0) / N[c] if N[c] else 0 for c in conf}

# 방향 에지: A의 이미지 중 B로 가는 게 유의미(>=2 & >=15%)
def edge(a, b):
    return b != "(none)" and b != a and conf[a][b] >= max(2, 0.15 * N[a])

E = {}  # (a,b) -> count
for a in conf:
    for b, n in conf[a].items():
        if edge(a, b):
            E[(a, b)] = n

# union-find로 무방향 군집
parent = {}
def find(x):
    parent.setdefault(x, x)
    while parent[x] != x:
        parent[x] = parent[parent[x]]; x = parent[x]
    return x
def union(a, b):
    parent[find(a)] = find(b)
for (a, b) in E:
    union(a, b)

groups = defaultdict(set)
for (a, b) in E:
    groups[find(a)].add(a); groups[find(a)].add(b)

mutual = sorted({tuple(sorted((a, b))) for (a, b) in E if (b, a) in E})

print("=" * 70)
print("강한 혼동쌍 (양방향 — 서로를 서로로 예측)")
print("=" * 70)
for a, b in mutual:
    print(f"  {a}({N.get(a,0)}) <-> {b}({N.get(b,0)})   {a}->{b}:{conf[a][b]}  {b}->{a}:{conf[b][a]}")

print("\n" + "=" * 70)
print("혼동군 (연결 클러스터) — 유지/병합 제안")
print("=" * 70)
for root, mem in sorted(groups.items(), key=lambda kv: -sum(N.get(x, 0) for x in kv[1])):
    mem = [x for x in mem if x in conf]
    if len(mem) < 2:
        continue
    # 유지 후보 = 군 내 최고 (recog * n) — 가장 잘 잡고 표본 많은 것
    keep = max(mem, key=lambda x: recog.get(x, 0) * N.get(x, 0) + N.get(x, 0) * 0.01)
    print(f"\n[군] " + " · ".join(sorted(mem, key=lambda x: -N.get(x, 0))))
    for x in sorted(mem, key=lambda x: -N.get(x, 0)):
        within = ", ".join(f"{b}{conf[x][b]}" for b in mem if b != x and conf[x][b]) or "-"
        tag = "  <= 유지권장" if x == keep else ""
        print(f"    {x:22s} n{N.get(x,0):3d} recog{recog.get(x,0):4.2f}  군내혼동: {within}{tag}")

print("\n※ recog=실환경 정답률. '강한 혼동쌍'은 사람도 헷갈리거나 같은 음식 split일 가능성.")
print("※ 각 군에서 유지권장 1개만 남기고 나머지는 merge(데이터 흡수) 또는 drop 후보.")

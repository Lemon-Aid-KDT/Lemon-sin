"""추가 drop 후보 탐색 — 혼동/오염/과적합-무특징 신호 종합 (CPU, 학습 방해 X).

신호:
  recog(wild)    : 실환경 정답률 (낮을수록 실패)
  scatter        : 자기 이미지가 몇 종류 클래스로 흩어지나 (높을수록 특징 못잡음)
  confused_with  : 가장 많이 틀리는 대상 (merge 후보)
  magnet         : 다른 클래스 이미지를 잘못 빨아들인 수 (높을수록 오염원/false-pos 자석)
  codes          : AIHub 음식코드 다양성 (1~2=동질=과적합prone)
  studioAP-wildR : 누수 갭 (높을수록 암기-무일반화)
"""
import sys, glob, os, re, csv
sys.stdout.reconfigure(encoding="utf-8")
from collections import defaultdict, Counter
from pathlib import Path
import cv2, numpy as np, yaml
from ultralytics import YOLO

AIHUB = Path(r"C:\Lemon-sin\data\food_images\processed\aihub_yolo_taxo59_bal1500")
WILD = Path(r"D:\Deeplearning\lemon\data\raw\friend_contributed\wild_keep_dedup_list.txt")
WBASE = Path(r"D:\Deeplearning\lemon\data\raw\friend_contributed\inbox")
W = r"C:\Lemon-sin\runs\food_yolo\exp14_balanced_pc1_s42_b16_w8_cache_disk_det_true\weights\best.pt"
EVALAP = Path(r"C:\Lemon-sin\docs\superpowers\plans\exp06_review\_eval_exp14_aihub_val.csv")
EVALWILD = Path(r"C:\Lemon-sin\docs\superpowers\plans\exp06_review\_eval_exp14_wild.csv")
DROPPED = {"cold-ramen", "nagasaki-champon", "tteokbokki-jajang", "tteokbokki-cream-rose"}

names = yaml.safe_load((AIHUB / "data.yaml").read_text(encoding="utf-8"))["names"]
names = names if isinstance(names, list) else [names[i] for i in sorted(names)]
wild = []
for ln in WILD.read_text(encoding="utf-8").splitlines():
    if ln.strip():
        fp, c = ln.split("\t"); wild.append((c, WBASE / fp))

m = YOLO(W)
conf = defaultdict(Counter)
for cls, p in wild:
    im = cv2.imread(str(p))
    if im is None:
        continue
    r = m.predict(im, conf=0.01, verbose=False, device="cpu")[0]
    pred = m.names[int(r.boxes.cls[int(np.argmax(r.boxes.conf.tolist()))])] if len(r.boxes) else "(none)"
    conf[cls][pred] += 1

# magnet: 다른 클래스가 잘못 예측된 대상
magnet = Counter()
for gt, c in conf.items():
    for pred, n in c.items():
        if pred != gt:
            magnet[pred] += n
# codes
codes = defaultdict(set)
for lf in glob.glob(str(AIHUB / "train" / "labels" / "*.txt")):
    mt = re.match(r"train_([A-Za-z0-9]+)_", os.path.basename(lf))
    c = int(open(lf).readline().split()[0])
    if mt:
        codes[names[c]].add(mt.group(1))
# studio AP / wild recog
ap = {r["class"]: float(r["exp14_ap"]) for r in csv.DictReader(EVALAP.open(encoding="utf-8-sig"))}
wr = {r["class"]: float(r["exp14_strict"]) for r in csv.DictReader(EVALWILD.open(encoding="utf-8-sig"))}

print(f"{'class':22s} {'n':>3s} {'recog':>5s} {'scat':>4s} {'magnet':>6s} {'codes':>5s} {'sAP':>4s} {'gap':>4s}  confused_with")
rows = []
for cls in names:
    if cls in DROPPED:
        continue
    c = conf.get(cls, Counter()); n = sum(c.values())
    rec = c.get(cls, 0) / n if n else 0
    scat = len([k for k in c if k != cls])
    mag = magnet.get(cls, 0)
    nc = len(codes.get(cls, []))
    sap = ap.get(cls, 0); gap = sap - wr.get(cls, 0)
    cw = ", ".join(f"{k}{v}" for k, v in c.most_common(3) if k != cls)[:40]
    # drop-score: 낮은recog + 흩어짐 + 자석 + 1코드 + 큰갭
    score = (1 - rec) * 2 + scat * 0.15 + (mag / 10) + (2 if nc <= 1 else 0) + gap
    rows.append((score, cls, n, rec, scat, mag, nc, sap, gap, cw))
rows.sort(reverse=True)
for score, cls, n, rec, scat, mag, nc, sap, gap, cw in rows:
    print(f"  {cls:22s} {n:3d} {rec:5.2f} {scat:4d} {mag:6d} {nc:5d} {sap:4.2f} {gap:4.2f}  {cw}")
print("\n※ magnet 큰 클래스 = 다른 음식을 잘못 빨아들이는 '오염원'(false-positive 자석)")
print("※ scat 큰 + recog 낮음 = 특징 못잡고 흩어짐(과적합/무특징)")

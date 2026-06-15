# -*- coding: utf-8 -*-
"""디텍터 크롭 패딩 sweep — 크롭 페널티(-0.12)가 맥락(패딩) 늘리면 회복되나.

디텍터 박스는 이미지당 1회만 계산(캐시), 패딩만 0.05~2.0으로 바꿔 재크롭→DINOv3 프로브.
풀이미지 0.842 / 타이트크롭(pad0.05) 0.723 대비 어느 패딩이 풀이미지에 근접하나.
usage: python -u _eval_detcrop_padsweep.py   (GPU, HF_TOKEN 설정 후)
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import torch
import yaml
from PIL import Image
from transformers import AutoImageProcessor, AutoModel
from ultralytics import YOLO

sys.stdout.reconfigure(encoding="utf-8")
EVAL = Path(r"D:\Deeplearning\lemon\data\raw\friend_contributed\wild_eval545_supported40.txt")
WBASE = Path(r"D:\Deeplearning\lemon\data\raw\friend_contributed\inbox")
PLUSRW = Path(r"C:\Lemon-sin\data\food_images\processed\aihub_taxo50_plus_realworld")
DET = Path(r"C:\Lemon-sin\backend\food_image_analysis\detector\detector_best.pt")
DINO_ID = "facebook/dinov3-vitb16-pretrain-lvd1689m"
SEED = 42
PADS = [0.05, 0.20, 0.40, 0.80, 1.50]
EXCLUDE10 = {"seafood-jjim", "seafood-spicy-tang", "seafood-clear-tang", "squid-dish",
             "shrimp-dish", "grilled-beef", "jjamppong", "fried-rice", "dumplings", "rice-bowl"}
dev = "cuda" if torch.cuda.is_available() else "cpu"

det = YOLO(str(DET))
_proc = AutoImageProcessor.from_pretrained(DINO_ID)
_model = AutoModel.from_pretrained(DINO_ID).to(dev).eval()


def box_of(im):
    r = det.predict(im, conf=0.25, iou=0.15, agnostic_nms=True, max_det=50, imgsz=512, verbose=False)[0]
    if not len(r.boxes):
        return None
    bi = int(r.boxes.conf.argmax())
    return [float(v) for v in r.boxes.xyxy[bi]]


def crop(im, box, pad):
    if box is None:
        return im  # fallback 풀이미지
    x1, y1, x2, y2 = box
    W, H = im.size
    px, py = (x2 - x1) * pad, (y2 - y1) * pad
    return im.crop((max(0, x1 - px), max(0, y1 - py), min(W, x2 + px), min(H, y2 + py)))


@torch.no_grad()
def feats_for(paths, boxes, pad, bs=48):
    out = []
    for i in range(0, len(paths), bs):
        ims = [crop(Image.open(p).convert("RGB"), boxes[j], pad)
               for j, p in enumerate(paths[i:i + bs], start=i)]
        inp = _proc(images=ims, return_tensors="pt").to(dev)
        o = _model(**inp)
        f = getattr(o, "pooler_output", None)
        if f is None:
            f = o.last_hidden_state[:, 0]
        f = f / f.norm(dim=-1, keepdim=True)
        out.append(f.cpu().numpy())
    return np.concatenate(out)


def names_of(ds):
    nm = yaml.safe_load((ds / "data.yaml").read_text(encoding="utf-8"))["names"]
    return nm if isinstance(nm, list) else [nm[i] for i in sorted(nm)]


def collect(ds, glob):
    names = names_of(ds); by = {}
    for lf in sorted((ds / "train" / "labels").glob(glob + ".txt")):
        ln = lf.read_text(encoding="utf-8").splitlines()
        if not ln or not ln[0].strip():
            continue
        cls = names[int(ln[0].split()[0])]
        if cls in EXCLUDE10:
            continue
        img = ds / "train" / "images" / (lf.stem + ".jpg")
        if img.exists():
            by.setdefault(cls, []).append(img)
    paths, labels = [], []
    for c, ims in by.items():
        paths += ims; labels += [c] * len(ims)
    return paths, labels


@torch.no_grad()
def boxes_for(paths):
    return [box_of(Image.open(p).convert("RGB")) for p in paths]


def probe(Xtr, ytr, Xw, wg):
    torch.manual_seed(SEED); np.random.seed(SEED)
    classes = sorted(set(ytr)); cidx = {c: i for i, c in enumerate(classes)}
    Xt = torch.tensor(Xtr, dtype=torch.float32, device=dev)
    yt = torch.tensor([cidx[c] for c in ytr], dtype=torch.long, device=dev)
    cnt = np.bincount([cidx[c] for c in ytr], minlength=len(classes)).astype(float)
    w = torch.tensor(cnt.sum() / (len(classes) * np.maximum(cnt, 1)), dtype=torch.float32, device=dev)
    lin = torch.nn.Linear(Xtr.shape[1], len(classes)).to(dev)
    opt = torch.optim.AdamW(lin.parameters(), lr=1e-3, weight_decay=1e-4)
    lossf = torch.nn.CrossEntropyLoss(weight=w)
    lin.train()
    for _ in range(300):
        opt.zero_grad(); lossf(lin(Xt), yt).backward(); opt.step()
    lin.eval()
    with torch.no_grad():
        pidx = lin(torch.tensor(Xw, dtype=torch.float32, device=dev)).argmax(1).cpu().numpy()
    pred = [classes[i] for i in pidx]
    return np.mean([pred[i] == wg[i] for i in range(len(wg))])


def main():
    items = [(WBASE / ln.split("\t")[0].replace("\\", "/"), ln.split("\t")[1])
             for ln in EVAL.read_text(encoding="utf-8").splitlines() if ln.strip() and not ln.startswith("#")]
    wp = [p for p, _ in items]; wg = [g for _, g in items]
    rw_p, rw_y = collect(PLUSRW, "rw_*")
    print(f"wild {len(items)} / realworld {len(rw_p)} / DINOv3-vitb16 / seed {SEED}")
    print("디텍터 박스 1회 계산중...")
    rw_box = boxes_for(rw_p); w_box = boxes_for(wp)
    print(f"  미검출(fallback): rw {sum(b is None for b in rw_box)} / wild {sum(b is None for b in w_box)}")
    print("\n================= 크롭 패딩 sweep (DINOv3 프로브, wild 545) =================")
    print("  기준: 풀이미지 0.842 / 타이트(pad0.05) 0.723")
    for pad in PADS:
        Xrw = feats_for(rw_p, rw_box, pad)
        Xw = feats_for(wp, w_box, pad)
        acc = probe(Xrw, rw_y, Xw, wg)
        print(f"  pad={pad:.2f} (박스의 {pad*100:.0f}% 확장): {acc:.3f}")


if __name__ == "__main__":
    main()

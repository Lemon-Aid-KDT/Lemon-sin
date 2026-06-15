# -*- coding: utf-8 -*-
"""방해음식 마스킹 검증 (정수님 아이디어) — 통제 합성 실험.

가설: 다중요리에서 타겟을 분류할 때, 타이트 크롭(맥락손실, 0.72) 대신
'다른 음식만 지우고 전체 장면 분류'(맥락보존)가 더 낫다.
측정 불가(다중요리 라벨 없음) → 단일요리(타겟, GT 알려짐)에 다른 음식을 작게 합성→방해 추가,
타겟 분류 정확도를 전략별 비교:
  ref  : 원본 풀이미지 (방해 없음, 상한 0.842)
  full : 합성(방해 포함) 풀이미지 (방해가 헷갈리게 함)
  crop : 타겟 박스 타이트 크롭 (맥락손실)
  mask : 방해음식 영역만 회색 마스킹 + 전체 분류  ← 정수님 방식
DINOv3-vitb16 프로브(realworld full 학습, 시드42).
usage: python -u _eval_distractor_mask.py   (GPU, HF_TOKEN 설정 후)
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
EXCLUDE10 = {"seafood-jjim", "seafood-spicy-tang", "seafood-clear-tang", "squid-dish",
             "shrimp-dish", "grilled-beef", "jjamppong", "fried-rice", "dumplings", "rice-bowl"}
dev = "cuda" if torch.cuda.is_available() else "cpu"

det = YOLO(str(DET))
_proc = AutoImageProcessor.from_pretrained(DINO_ID)
_model = AutoModel.from_pretrained(DINO_ID).to(dev).eval()


def _small(im):
    """프로세서 입력 전 896px로 축소. DINOv3는 내부에서 224×224로 리사이즈하므로
    896은 모델 입력의 4배 = 무손실(4000px 원본을 줘도 모델 계산은 동일). CPU OOM만 방지."""
    im = im.copy(); im.thumbnail((896, 896)); return im


@torch.no_grad()
def feats(ims, bs=24):
    out = []
    for i in range(0, len(ims), bs):
        batch = [_small(x) for x in ims[i:i + bs]]
        inp = _proc(images=batch, return_tensors="pt").to(dev)
        o = _model(**inp)
        f = getattr(o, "pooler_output", None)
        if f is None:
            f = o.last_hidden_state[:, 0]
        f = f / f.norm(dim=-1, keepdim=True)
        out.append(f.cpu().numpy())
    return np.concatenate(out)


def det_box(im):
    r = det.predict(im, conf=0.25, iou=0.15, agnostic_nms=True, max_det=50, imgsz=512, verbose=False)[0]
    if not len(r.boxes):
        W, H = im.size
        return [W * 0.1, H * 0.1, W * 0.9, H * 0.9]
    bi = int(r.boxes.conf.argmax())
    return [float(v) for v in r.boxes.xyxy[bi]]


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
    p, y = [], []
    for c, ims in by.items():
        p += ims; y += [c] * len(ims)
    return p, y


def probe(Xtr, ytr):
    torch.manual_seed(SEED); np.random.seed(SEED)
    classes = sorted(set(ytr)); cidx = {c: i for i, c in enumerate(classes)}
    Xt = torch.tensor(Xtr, dtype=torch.float32, device=dev)
    yt = torch.tensor([cidx[c] for c in ytr], dtype=torch.long, device=dev)
    cnt = np.bincount([cidx[c] for c in ytr], minlength=len(classes)).astype(float)
    w = torch.tensor(cnt.sum() / (len(classes) * np.maximum(cnt, 1)), dtype=torch.float32, device=dev)
    lin = torch.nn.Linear(Xtr.shape[1], len(classes)).to(dev)
    opt = torch.optim.AdamW(lin.parameters(), lr=1e-3, weight_decay=1e-4)
    lf = torch.nn.CrossEntropyLoss(weight=w)
    lin.train()
    for _ in range(300):
        opt.zero_grad(); lf(lin(Xt), yt).backward(); opt.step()
    lin.eval()
    return lin, classes


def main():
    items = [(WBASE / ln.split("\t")[0].replace("\\", "/"), ln.split("\t")[1])
             for ln in EVAL.read_text(encoding="utf-8").splitlines() if ln.strip() and not ln.startswith("#")]
    wp = [p for p, _ in items]; wg = [g for _, g in items]
    rw_p, rw_y = collect(PLUSRW, "rw_*")
    print(f"wild {len(items)} / realworld {len(rw_p)} / DINOv3-vitb16 / seed {SEED}")

    # 프로브 학습 (realworld full → 0.842 셋업)
    print("프로브 학습(realworld full)...")
    lin, classes = probe(feats([Image.open(p).convert("RGB") for p in rw_p]), rw_y)
    cset = set(classes)

    # 원본 로드 + 타겟 박스
    print("원본 로드 + 디텍터 박스...")
    origs = [Image.open(p).convert("RGB") for p in wp]
    tboxes = [det_box(im) for im in origs]

    # 합성: 타겟 i 에 다른클래스 음식 j 를 우상단에 30% 크기로 붙임
    rng = np.random.default_rng(SEED)
    n = len(origs)
    ref_imgs, full_imgs, crop_imgs, mask_imgs, gts = [], [], [], [], []
    for i in range(n):
        if wg[i] not in cset:
            continue
        # 방해음식: 다른 클래스 하나 고름
        j = int(rng.integers(0, n))
        tries = 0
        while wg[j] == wg[i] and tries < 20:
            j = int(rng.integers(0, n)); tries += 1
        T = origs[i].copy()
        W, H = T.size
        D = origs[j].resize((max(1, W // 3), max(1, H // 3)))
        dw, dh = D.size
        dx, dy = W - dw, 0  # 우상단
        comp = T.copy(); comp.paste(D, (dx, dy))
        # ref(방해없음), full(방해포함), crop(타겟박스), mask(방해영역 회색)
        x1, y1, x2, y2 = tboxes[i]
        px, py = (x2 - x1) * 0.05, (y2 - y1) * 0.05
        crop = comp.crop((max(0, x1 - px), max(0, y1 - py), min(W, x2 + px), min(H, y2 + py)))
        masked = comp.copy()
        from PIL import ImageDraw
        ImageDraw.Draw(masked).rectangle([dx, dy, dx + dw, dy + dh], fill=(128, 128, 128))
        ref_imgs.append(T); full_imgs.append(comp); crop_imgs.append(crop); mask_imgs.append(masked); gts.append(wg[i])

    def acc(imgs):
        X = torch.tensor(feats(imgs), dtype=torch.float32, device=dev)
        with torch.no_grad():
            pidx = lin(X).argmax(1).cpu().numpy()
        pred = [classes[k] for k in pidx]
        return np.mean([pred[k] == gts[k] for k in range(len(gts))])

    print(f"\n합성 평가 {len(gts)}장 (각 타겟에 다른음식 우상단 1/3 합성)")
    print("================= 방해음식 처리 전략별 타겟 분류 정확도 =================")
    print(f"  ref  원본(방해없음, 상한)        : {acc(ref_imgs):.3f}")
    print(f"  full 합성 그대로(방해 포함)      : {acc(full_imgs):.3f}")
    print(f"  crop 타겟박스 타이트크롭          : {acc(crop_imgs):.3f}")
    print(f"  mask 방해영역만 회색마스킹 ★정수님 : {acc(mask_imgs):.3f}")


if __name__ == "__main__":
    main()

# -*- coding: utf-8 -*-
"""DINOv3 라인어 프로브 학습 + 저장 (실전 파이프라인용).

CLIP/DINO 실험에서 검증된 최강 분류기(DINOv3-vitb16 + realworld 실데이터 선형학습, wild 0.842)를
한 번 학습해 디스크에 저장한다. 추론은 food_pipeline_dino.py가 이 가중치를 로드해 사용.
백본(DINOv3)은 HF 캐시에서 로드, 학습되는 건 선형층(768x40)뿐.
usage: python -u train_probe.py   (GPU, HF_TOKEN 설정 후)
출력: probe_head.pt (선형 가중치+클래스+설정)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import torch
import yaml
from PIL import Image
from transformers import AutoImageProcessor, AutoModel

sys.stdout.reconfigure(encoding="utf-8")
HERE = Path(__file__).resolve().parent
PLUSRW = Path(r"C:\Lemon-sin\data\food_images\processed\aihub_taxo50_plus_realworld")
DINO_ID = "facebook/dinov3-vitb16-pretrain-lvd1689m"
SEED = 42
MAX_PX = 896
EXCLUDE10 = {"seafood-jjim", "seafood-spicy-tang", "seafood-clear-tang", "squid-dish",
             "shrimp-dish", "grilled-beef", "jjamppong", "fried-rice", "dumplings", "rice-bowl"}
dev = "cuda" if torch.cuda.is_available() else "cpu"


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


def main():
    proc = AutoImageProcessor.from_pretrained(DINO_ID)
    model = AutoModel.from_pretrained(DINO_ID).to(dev).eval()

    rw_p, rw_y = collect(PLUSRW, "rw_*")
    print(f"학습 데이터: realworld {len(rw_p)}장 / {len(set(rw_y))}클래스 / DINOv3-vitb16 / seed {SEED}")

    @torch.no_grad()
    def feats(paths, bs=24):
        out = []
        for i in range(0, len(paths), bs):
            ims = []
            for p in paths[i:i + bs]:
                im = Image.open(p).convert("RGB"); im.thumbnail((MAX_PX, MAX_PX)); ims.append(im)
            inp = proc(images=ims, return_tensors="pt").to(dev)
            o = model(**inp)
            f = getattr(o, "pooler_output", None)
            if f is None:
                f = o.last_hidden_state[:, 0]
            f = f / f.norm(dim=-1, keepdim=True)
            out.append(f.cpu())
        return torch.cat(out)

    print("DINOv3 특징 추출중...")
    X = feats(rw_p).to(dev)
    classes = sorted(set(rw_y))
    cidx = {c: i for i, c in enumerate(classes)}
    y = torch.tensor([cidx[c] for c in rw_y], dtype=torch.long, device=dev)

    torch.manual_seed(SEED); np.random.seed(SEED)
    cnt = np.bincount([cidx[c] for c in rw_y], minlength=len(classes)).astype(float)
    w = torch.tensor(cnt.sum() / (len(classes) * np.maximum(cnt, 1)), dtype=torch.float32, device=dev)
    lin = torch.nn.Linear(X.shape[1], len(classes)).to(dev)
    opt = torch.optim.AdamW(lin.parameters(), lr=1e-3, weight_decay=1e-4)
    lossf = torch.nn.CrossEntropyLoss(weight=w)
    lin.train()
    for ep in range(300):
        opt.zero_grad(); loss = lossf(lin(X), y); loss.backward(); opt.step()
    print(f"학습 완료 (final loss {loss.item():.4f})")

    out = HERE / "probe_head.pt"
    torch.save({
        "state_dict": {k: v.cpu() for k, v in lin.state_dict().items()},
        "classes": classes,
        "dino_id": DINO_ID,
        "feat_dim": X.shape[1],
        "max_px": MAX_PX,
        "seed": SEED,
        "train_source": "realworld(plus_realworld rw_) full image",
        "note": "wild 545 단일요리 기준 약 0.842 (마스킹 파이프라인용)",
    }, out)
    (HERE / "probe_classes.json").write_text(json.dumps(classes, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"저장: {out.name} ({out.stat().st_size//1024}KB) + probe_classes.json ({len(classes)}클래스)")


if __name__ == "__main__":
    main()

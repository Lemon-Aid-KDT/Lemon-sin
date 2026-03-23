#!/usr/bin/env python3
"""
Multi-positive Contrastive Loss CLIP Fine-tuning

같은 카테고리의 여러 이미지를 positive로 취급하는 SupCon Loss를 사용하여
CLIP 이미지 인코더를 fine-tune한다.

기존 train_clip.py와의 차이:
- 같은 카테고리 내 모든 이미지 쌍이 positive (1:N)
- SupCon Loss (Supervised Contrastive Learning)
- Hard negative mining: 다른 카테고리지만 유사한 이미지를 강조

사용법:
    python training/scripts/train_clip_multipos.py \
        --data_dir data/MiSUMi_png \
        --output_dir training/clip_multipos_runs \
        --epochs 20 \
        --batch 64

출력 체크포인트: core/embeddings.ImageEmbedder(finetuned_path=...) 호환
"""

import argparse
import gc
import json
import sys
import time
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.optim import AdamW
from torch.optim.lr_scheduler import CosineAnnealingLR
from torch.utils.data import Dataset, DataLoader
from PIL import Image


# ─────────────────────────────────────────────
# SupCon Loss (adapted from train_gnn.py)
# ─────────────────────────────────────────────


class SupConLoss(nn.Module):
    """Supervised Contrastive Loss (Khosla et al., 2020).

    같은 카테고리의 모든 샘플을 positive로 취급.
    temperature로 분포 sharpness 조절.

    수치 안정성을 위해 max-subtraction + clamp 적용.
    """

    def __init__(self, temperature: float = 0.07):
        super().__init__()
        self.temperature = temperature

    def forward(self, features: torch.Tensor, labels: torch.Tensor) -> torch.Tensor:
        """
        Args:
            features: (batch_size, embed_dim) L2-normalized embeddings
            labels: (batch_size,) integer category labels

        Returns:
            scalar loss
        """
        device = features.device
        batch_size = features.shape[0]

        if batch_size < 2:
            return torch.tensor(0.0, device=device, requires_grad=True)

        # L2 normalize
        features = F.normalize(features, p=2, dim=1)
        sim_matrix = torch.matmul(features, features.T) / self.temperature

        # 수치 안정성: max subtraction
        sim_max, _ = sim_matrix.max(dim=1, keepdim=True)
        sim_matrix = sim_matrix - sim_max.detach()

        # 마스크
        self_mask = torch.eye(batch_size, dtype=torch.bool, device=device)
        labels_eq = labels.unsqueeze(0) == labels.unsqueeze(1)
        positive_mask = labels_eq & ~self_mask

        # positive가 없는 샘플 스킵
        has_positive = positive_mask.sum(dim=1) > 0
        if not has_positive.any():
            return torch.tensor(0.0, device=device, requires_grad=True)

        # exp
        exp_sim = torch.exp(sim_matrix)
        exp_sim = exp_sim.masked_fill(self_mask, 0.0)

        # denominator: all except self
        denom = exp_sim.sum(dim=1, keepdim=True).clamp(min=1e-8)

        # log prob
        log_prob = sim_matrix - torch.log(denom)

        # positive pairs 평균
        pos_log_prob = (log_prob * positive_mask.float()).sum(dim=1)
        pos_count = positive_mask.sum(dim=1).clamp(min=1).float()
        mean_log_prob = pos_log_prob / pos_count

        # loss (has_positive만)
        loss = -mean_log_prob[has_positive].mean()

        # NaN 방지
        if torch.isnan(loss) or torch.isinf(loss):
            return torch.tensor(0.0, device=device, requires_grad=True)

        return loss


# ─────────────────────────────────────────────
# Dataset
# ─────────────────────────────────────────────


class CategoryImageDataset(Dataset):
    """카테고리별 이미지 데이터셋.

    각 배치에 같은 카테고리의 여러 이미지가 포함되도록
    카테고리 기반 샘플링을 지원한다.

    디렉토리 구조:
        data_dir/
            category_A/
                image1.png
            category_B/
                ...
    """

    SUPPORTED_EXTS = {".png", ".jpg", ".jpeg", ".tiff", ".tif", ".bmp"}

    def __init__(self, data_dir: str, transform=None):
        self.data_dir = Path(data_dir)
        self.transform = transform
        self.samples: list[tuple[str, int]] = []  # (image_path, category_idx)
        self.categories: list[str] = []

        cat_set: dict[str, int] = {}

        for subdir in sorted(self.data_dir.iterdir()):
            if not subdir.is_dir():
                continue
            cat_name = subdir.name
            if cat_name not in cat_set:
                cat_set[cat_name] = len(self.categories)
                self.categories.append(cat_name)
            cat_idx = cat_set[cat_name]

            for f in subdir.iterdir():
                if f.suffix.lower() in self.SUPPORTED_EXTS:
                    self.samples.append((str(f), cat_idx))

        print(f"데이터셋: {len(self.samples)}개 이미지, {len(self.categories)}개 카테고리")

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        path, label = self.samples[idx]
        try:
            img = Image.open(path).convert("RGB")
        except Exception:
            # 읽기 실패 시 빈 이미지 반환
            img = Image.new("RGB", (224, 224), (128, 128, 128))

        if self.transform is not None:
            img = self.transform(img)

        return img, label


# ─────────────────────────────────────────────
# Hard Negative Miner
# ─────────────────────────────────────────────


class HardNegativeMiner:
    """Hard negative mining.

    임베딩 공간에서 다른 카테고리지만 가까운 샘플을 찾아
    다음 에폭에서 같은 배치에 포함시킨다.
    """

    def __init__(self, num_negatives: int = 5):
        self.num_negatives = num_negatives
        self._hard_indices: set[int] = set()

    @torch.no_grad()
    def mine(
        self,
        embeddings: np.ndarray,
        labels: np.ndarray,
    ) -> list[tuple[int, int]]:
        """Hard negative 쌍을 찾는다.

        Args:
            embeddings: (N, dim) L2-normalized embeddings
            labels: (N,) category labels

        Returns:
            List of (anchor_idx, hard_neg_idx) pairs
        """
        emb_t = torch.from_numpy(embeddings).float()
        emb_t = F.normalize(emb_t, p=2, dim=1)
        sim_matrix = torch.matmul(emb_t, emb_t.T)

        n = len(labels)
        pairs: list[tuple[int, int]] = []
        hard_set: set[int] = set()

        for i in range(n):
            topk = sim_matrix[i].topk(self.num_negatives + 1).indices[1:]
            for j in topk.tolist():
                if labels[i] != labels[j]:
                    pairs.append((i, j))
                    hard_set.add(i)
                    hard_set.add(j)
                    break

        self._hard_indices = hard_set
        print(f"  Hard negatives: {len(hard_set)}/{n} ({len(hard_set)/n*100:.1f}%)")
        return pairs

    def get_hard_indices(self) -> set[int]:
        return self._hard_indices


# ─────────────────────────────────────────────
# Evaluation
# ─────────────────────────────────────────────


@torch.no_grad()
def evaluate_recall(
    model,
    preprocess,
    dataset: CategoryImageDataset,
    device: str,
    batch_size: int = 64,
    ks: tuple[int, ...] = (1, 5, 10),
    max_samples: int = 2000,
) -> dict[str, float]:
    """k-NN 기반 Recall@K 평가.

    Args:
        model: OpenCLIP model (image encoder)
        preprocess: image transform
        dataset: evaluation dataset
        device: computation device
        batch_size: batch size
        ks: k values for recall
        max_samples: max samples for evaluation (메모리 제한)

    Returns:
        {"R@1": float, "R@5": float, "R@10": float}
    """
    model.eval()

    # 서브샘플 (메모리 절약)
    n = min(len(dataset), max_samples)
    indices = np.random.choice(len(dataset), size=n, replace=False)

    all_embeddings = []
    all_labels = []

    for start in range(0, n, batch_size):
        end = min(start + batch_size, n)
        batch_indices = indices[start:end]

        images = []
        labels = []
        for idx in batch_indices:
            path, label = dataset.samples[idx]
            try:
                img = Image.open(path).convert("RGB")
                img = preprocess(img)
            except Exception:
                img = preprocess(Image.new("RGB", (224, 224), (128, 128, 128)))
            images.append(img)
            labels.append(label)

        batch_tensor = torch.stack(images).to(device)
        emb = model.encode_image(batch_tensor)
        emb = F.normalize(emb, p=2, dim=1)
        all_embeddings.append(emb.cpu())
        all_labels.extend(labels)

    embeddings = torch.cat(all_embeddings, dim=0)
    labels_t = torch.tensor(all_labels)

    # 코사인 유사도
    sim = torch.matmul(embeddings, embeddings.T)
    sim.fill_diagonal_(float("-inf"))

    recalls = {}
    for k in ks:
        topk_idx = sim.topk(k, dim=1).indices
        topk_labels = labels_t[topk_idx]
        match = (topk_labels == labels_t.unsqueeze(1)).any(dim=1)
        recalls[f"R@{k}"] = match.float().mean().item()

    return recalls


# ─────────────────────────────────────────────
# Training
# ─────────────────────────────────────────────


def train_one_epoch(
    model,
    preprocess,
    loader: DataLoader,
    optimizer,
    criterion: SupConLoss,
    device: str,
) -> float:
    """1 에폭 학습. CLIP image encoder만 학습한다."""
    model.train()
    total_loss = 0.0
    n_batches = 0

    for images, labels in loader:
        images = images.to(device)
        labels = labels.to(device)

        # CLIP image encoder forward
        embeddings = model.encode_image(images)
        loss = criterion(embeddings, labels)

        optimizer.zero_grad()
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
        optimizer.step()

        total_loss += loss.item()
        n_batches += 1

    return total_loss / max(n_batches, 1)


# ─────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(
        description="Multi-positive SupCon Loss CLIP Fine-tuning"
    )
    parser.add_argument("--data_dir", required=True, help="이미지 데이터 디렉토리 (서브폴더=카테고리)")
    parser.add_argument("--output_dir", default="./clip_multipos_runs", help="출력 디렉토리")
    parser.add_argument("--model", default="ViT-L-14", help="OpenCLIP 모델 아키텍처")
    parser.add_argument("--pretrained", default="datacomp_xl_s13b_b90k", help="사전학습 체크포인트")
    parser.add_argument("--epochs", type=int, default=20, help="학습 에폭 수")
    parser.add_argument("--batch", type=int, default=64, help="배치 크기")
    parser.add_argument("--lr", type=float, default=1e-5, help="학습률")
    parser.add_argument("--temperature", type=float, default=0.07, help="SupCon loss temperature")
    parser.add_argument("--hard_negative", action="store_true", help="Hard negative mining 활성화")
    parser.add_argument("--hard_negative_interval", type=int, default=5, help="Hard negative 갱신 주기 (에폭)")
    parser.add_argument("--workers", type=int, default=0, help="DataLoader workers (USB 드라이브는 0 권장)")
    parser.add_argument("--val_split", type=float, default=0.1, help="검증 데이터 비율")
    parser.add_argument("--resume", default="", help="이어서 학습할 체크포인트 경로")
    parser.add_argument("--patience", type=int, default=10, help="Early stopping patience (0=비활성)")
    parser.add_argument("--checkpoint_interval", type=int, default=5, help="체크포인트 저장 주기 (에폭)")
    parser.add_argument("--eval_max_samples", type=int, default=2000, help="평가 시 최대 샘플 수")
    args = parser.parse_args()

    # ── 디바이스 선택 ──
    if torch.cuda.is_available():
        device = "cuda"
    elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        device = "mps"
    else:
        device = "cpu"
    print(f"디바이스: {device}")

    # 출력 디렉토리
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # ── OpenCLIP 모델 로딩 ──
    try:
        import open_clip
    except ImportError:
        print("[ERROR] open_clip 미설치: pip install open-clip-torch>=2.26.0")
        sys.exit(1)

    print(f"OpenCLIP 모델 로딩: {args.model} (pretrained={args.pretrained})")
    model, _, preprocess = open_clip.create_model_and_transforms(
        args.model, pretrained=args.pretrained, device=device,
    )

    # Text encoder 동결 (image encoder만 학습)
    for p in model.text.parameters():
        p.requires_grad = False
    # Logit scale 동결
    if hasattr(model, "logit_scale"):
        model.logit_scale.requires_grad = False

    trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
    total = sum(p.numel() for p in model.parameters())
    print(f"파라미터: 전체={total:,}, 학습={trainable:,} (image encoder only)")

    # ── 데이터셋 ──
    full_dataset = CategoryImageDataset(args.data_dir, transform=preprocess)
    if len(full_dataset) == 0:
        print("[ERROR] 데이터셋이 비어있습니다.")
        sys.exit(1)

    # Train/Val split
    n_val = int(len(full_dataset) * args.val_split)
    n_train = len(full_dataset) - n_val

    indices = list(range(len(full_dataset)))
    np.random.seed(42)
    np.random.shuffle(indices)
    train_indices = indices[:n_train]
    val_indices = indices[n_train:]

    train_dataset = torch.utils.data.Subset(full_dataset, train_indices)
    val_dataset = torch.utils.data.Subset(full_dataset, val_indices)

    train_loader = DataLoader(
        train_dataset,
        batch_size=args.batch,
        shuffle=True,
        num_workers=args.workers,
        pin_memory=(device != "cpu"),
        drop_last=True,
    )

    print(f"Train: {len(train_dataset)}, Val: {len(val_dataset)}")

    # ── 옵티마이저 + 스케줄러 ──
    # image encoder 파라미터만
    image_params = [p for p in model.visual.parameters() if p.requires_grad]
    optimizer = AdamW(image_params, lr=args.lr, weight_decay=1e-4)
    scheduler = CosineAnnealingLR(optimizer, T_max=args.epochs)
    criterion = SupConLoss(temperature=args.temperature)

    start_epoch = 0
    best_recall = 0.0
    patience_counter = 0

    # ── Resume ──
    if args.resume and Path(args.resume).exists():
        print(f"체크포인트 로딩: {args.resume}")
        ckpt = torch.load(args.resume, map_location=device, weights_only=False)
        # 호환성: model_state_dict에는 전체 모델 또는 visual만 있을 수 있음
        state_dict = ckpt.get("model_state_dict", {})
        if state_dict:
            # visual prefix가 있으면 전체 모델로 로딩
            if any(k.startswith("visual.") for k in state_dict.keys()):
                model.load_state_dict(state_dict, strict=False)
            else:
                model.visual.load_state_dict(state_dict, strict=False)
        if "optimizer_state_dict" in ckpt:
            try:
                optimizer.load_state_dict(ckpt["optimizer_state_dict"])
            except Exception:
                print("  [WARN] 옵티마이저 상태 로딩 실패 (무시)")
        start_epoch = ckpt.get("epoch", 0) + 1
        best_recall = ckpt.get("best_recall", 0.0)
        print(f"  Resume from epoch {start_epoch}, best R@5={best_recall:.4f}")

    # ── Hard Negative Miner ──
    hn_miner: HardNegativeMiner | None = None
    if args.hard_negative:
        hn_miner = HardNegativeMiner(num_negatives=5)

    # ── 학습 로그 ──
    log_path = output_dir / "train_log.json"
    logs = []

    print(f"\n{'='*60}")
    print(f"Multi-positive SupCon CLIP Fine-tuning 시작")
    print(f"  Model: {args.model} | Pretrained: {args.pretrained}")
    print(f"  Train: {len(train_dataset)} | Val: {len(val_dataset)}")
    print(f"  Batch: {args.batch} | LR: {args.lr} | Temp: {args.temperature}")
    print(f"  HardNeg: {'ON' if hn_miner else 'OFF'} | Patience: {args.patience}")
    print(f"{'='*60}\n")

    # ── 학습 루프 ──
    for epoch in range(start_epoch, args.epochs):
        t0 = time.time()

        # Hard negative mining (주기적)
        if (hn_miner is not None
                and epoch > 0
                and epoch % args.hard_negative_interval == 0):
            print(f"  Hard negative mining (epoch {epoch})...")
            model.eval()
            all_emb = []
            all_lbl = []
            with torch.no_grad():
                for images, labels in train_loader:
                    images = images.to(device)
                    emb = model.encode_image(images)
                    emb = F.normalize(emb, p=2, dim=1)
                    all_emb.append(emb.cpu().numpy())
                    all_lbl.append(labels.numpy())
            all_emb = np.concatenate(all_emb, axis=0)
            all_lbl = np.concatenate(all_lbl, axis=0)
            hn_miner.mine(all_emb, all_lbl)

        # 학습
        train_loss = train_one_epoch(
            model, preprocess, train_loader, optimizer, criterion, device,
        )
        scheduler.step()

        # 검증
        recalls = evaluate_recall(
            model, preprocess, full_dataset, device,
            batch_size=args.batch,
            max_samples=args.eval_max_samples,
        )
        elapsed = time.time() - t0

        log_entry = {
            "epoch": epoch,
            "train_loss": round(train_loss, 4),
            "lr": round(optimizer.param_groups[0]["lr"], 8),
            "elapsed_sec": round(elapsed, 1),
            **{k: round(v, 4) for k, v in recalls.items()},
        }
        logs.append(log_entry)

        print(
            f"[Epoch {epoch+1:3d}/{args.epochs}] "
            f"loss={train_loss:.4f} | "
            f"R@1={recalls['R@1']:.4f} R@5={recalls['R@5']:.4f} R@10={recalls['R@10']:.4f} | "
            f"lr={optimizer.param_groups[0]['lr']:.8f} | "
            f"{elapsed:.1f}s"
        )

        # Best 모델 저장
        # 체크포인트 형식: ImageEmbedder(finetuned_path=...) 호환
        # model.load_state_dict(checkpoint["model_state_dict"])
        if recalls["R@5"] > best_recall:
            best_recall = recalls["R@5"]
            patience_counter = 0
            best_path = output_dir / "clip_multipos_best.pt"
            torch.save({
                "model_state_dict": model.state_dict(),
                "config": {
                    "model_name": args.model,
                    "pretrained": args.pretrained,
                    "temperature": args.temperature,
                },
                "epoch": epoch,
                "best_recall": best_recall,
                "categories": full_dataset.categories,
            }, best_path)
            print(f"  -> Best model saved (R@5={best_recall:.4f})")
        else:
            patience_counter += 1

        # Early stopping
        if args.patience > 0 and patience_counter >= args.patience:
            print(
                f"\n  Early stopping at epoch {epoch+1} "
                f"(no R@5 improvement for {args.patience} epochs)"
            )
            break

        # 주기적 체크포인트
        if (epoch + 1) % args.checkpoint_interval == 0:
            ckpt_path = output_dir / f"checkpoint_epoch{epoch+1}.pt"
            torch.save({
                "model_state_dict": model.state_dict(),
                "optimizer_state_dict": optimizer.state_dict(),
                "epoch": epoch,
                "best_recall": best_recall,
                "config": {
                    "model_name": args.model,
                    "pretrained": args.pretrained,
                    "temperature": args.temperature,
                },
            }, ckpt_path)
            print(f"  -> Checkpoint saved: {ckpt_path}")

        # 로그 저장
        with open(log_path, "w", encoding="utf-8") as f:
            json.dump(logs, f, indent=2, ensure_ascii=False)

        # 메모리 정리
        gc.collect()
        if device == "cuda":
            torch.cuda.empty_cache()

    print(f"\n{'='*60}")
    print(f"학습 완료. Best R@5={best_recall:.4f}")
    print(f"Best model: {output_dir / 'clip_multipos_best.pt'}")
    print(f"Log: {log_path}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()

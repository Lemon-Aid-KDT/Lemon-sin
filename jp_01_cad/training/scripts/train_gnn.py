#!/usr/bin/env python3
"""
GNN (GIN) 구조 임베딩 학습 스크립트 v2

v1 대비 개선:
  - InMemoryDataset: 시작 시 전체 그래프를 RAM에 로드 (에폭당 I/O 0)
  - CPU 전용: MPS 메모리 오버헤드 제거, 스왑 방지
  - 에폭당 서브샘플링 (30%): 빠른 에폭, 다양한 배치 구성
  - SupConLoss 수치 안정성 개선 (loss=nan 수정)
  - gc.collect() 매 에폭

Usage:
    python train_gnn.py \
        --dxf_dirs /path/to/MiSUMi_data /path/to/Unit_bearing_dxf \
        --output_dir ./gnn_runs \
        --epochs 50 \
        --batch 256

카테고리 라벨: DXF 파일이 위치한 디렉토리명을 카테고리로 사용한다.
"""

import argparse
import gc
import hashlib
import json
import os
import sys
import time
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.optim import AdamW
from torch.optim.lr_scheduler import CosineAnnealingLR

# 프로젝트 루트를 path에 추가 (app/core 모듈 참조용)
_project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_project_root / "app"))

from core.gnn import DXFGraphBuilder, GINEncoder, NODE_FEATURE_DIM


# ─────────────────────────────────────────────
# InMemory Dataset
# ─────────────────────────────────────────────

class InMemoryDXFDataset:
    """전체 DXF → PyG 그래프를 시작 시 RAM에 로드.

    에폭당 I/O가 0이 되어 학습 속도가 극적으로 개선된다.

    디렉토리 구조:
        dxf_dir/
            category_A/
                file1.dxf
            category_B/
                ...
    """

    def __init__(
        self,
        dxf_dirs: list[str],
        builder: DXFGraphBuilder,
        cache_dir: str = "",
    ):
        self.builder = builder
        self.cache_dir = Path(cache_dir) if cache_dir else None
        self.graphs: list[object] = []  # PyG Data objects
        self.labels: list[int] = []
        self.categories: list[str] = []

        # DXF 파일 수집
        samples: list[tuple[Path, int]] = []
        cat_set: dict[str, int] = {}

        for dxf_dir in dxf_dirs:
            dxf_dir = Path(dxf_dir)
            if not dxf_dir.exists():
                print(f"[WARN] 디렉토리 없음: {dxf_dir}")
                continue
            for subdir in sorted(dxf_dir.iterdir()):
                if not subdir.is_dir():
                    continue
                cat_name = subdir.name
                if cat_name not in cat_set:
                    cat_set[cat_name] = len(self.categories)
                    self.categories.append(cat_name)
                cat_idx = cat_set[cat_name]
                for f in subdir.iterdir():
                    if f.suffix.lower() == ".dxf":
                        samples.append((f, cat_idx))

        print(f"데이터셋: {len(samples)}개 DXF, {len(self.categories)}개 카테고리")

        if self.cache_dir:
            self.cache_dir.mkdir(parents=True, exist_ok=True)

        # ── 전체 로드 ──
        from torch_geometric.data import Data

        dummy = Data(
            x=torch.zeros(1, NODE_FEATURE_DIM),
            edge_index=torch.zeros(2, 0, dtype=torch.long),
            edge_attr=torch.zeros(0, 3),
        )

        t0 = time.time()
        n_cached = 0
        n_built = 0
        n_failed = 0

        for i, (path, label) in enumerate(samples):
            data = None

            # 캐시에서 로드
            cache_path = None
            if self.cache_dir:
                path_hash = hashlib.md5(str(path).encode()).hexdigest()[:8]
                cache_path = self.cache_dir / f"{path.stem}_{path_hash}.pt"
                if cache_path.exists():
                    try:
                        data = torch.load(cache_path, weights_only=False)
                        n_cached += 1
                    except Exception:
                        data = None

            # 캐시 미스 → DXF 빌드
            if data is None:
                try:
                    data = self.builder.build_graph(path)
                    n_built += 1
                    # 캐시 저장
                    if cache_path is not None:
                        try:
                            torch.save(data, cache_path)
                        except Exception:
                            pass
                except Exception as e:
                    if n_failed < 20:
                        print(f"[WARN] 그래프 빌드 실패 ({path.name}): {e}")
                    data = dummy.clone()
                    n_failed += 1

            data.y = torch.tensor(label, dtype=torch.long)
            self.graphs.append(data)
            self.labels.append(label)

            # 진행률 (10000건마다)
            if (i + 1) % 10000 == 0:
                elapsed = time.time() - t0
                print(f"  로딩: {i+1}/{len(samples)} ({elapsed:.0f}s) "
                      f"cached={n_cached} built={n_built} failed={n_failed}")

        elapsed = time.time() - t0
        print(f"전체 로딩 완료: {len(self.graphs)}개 ({elapsed:.0f}s)")
        print(f"  캐시 히트: {n_cached}, 빌드: {n_built}, 실패: {n_failed}")

        # 메모리 사용량 추정
        gc.collect()

    def __len__(self):
        return len(self.graphs)

    def __getitem__(self, idx):
        return self.graphs[idx]


# ─────────────────────────────────────────────
# SupCon Loss (수치 안정성 개선)
# ─────────────────────────────────────────────

class SupConLoss(nn.Module):
    """Supervised Contrastive Loss (Khosla et al., 2020).

    v2: 수치 안정성을 위해 max-subtraction + clamp 적용.
    """

    def __init__(self, temperature: float = 0.07):
        super().__init__()
        self.temperature = temperature

    def forward(self, embeddings: torch.Tensor, labels: torch.Tensor) -> torch.Tensor:
        device = embeddings.device
        batch_size = embeddings.shape[0]

        if batch_size < 2:
            return torch.tensor(0.0, device=device, requires_grad=True)

        # 유사도 행렬 (L2-norm 보장)
        embeddings = F.normalize(embeddings, p=2, dim=1)
        sim_matrix = torch.matmul(embeddings, embeddings.T) / self.temperature

        # 수치 안정성: max subtraction
        sim_max, _ = sim_matrix.max(dim=1, keepdim=True)
        sim_matrix = sim_matrix - sim_max.detach()

        # 마스크
        self_mask = torch.eye(batch_size, dtype=torch.bool, device=device)
        labels_eq = labels.unsqueeze(0) == labels.unsqueeze(1)
        positive_mask = labels_eq & ~self_mask
        negative_mask = ~labels_eq & ~self_mask

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
# Hard Negative Mining
# ─────────────────────────────────────────────

class HardNegativeMiner:
    """임베딩 공간에서 가까운 다른 카테고리 샘플을 hard negative로 식별.

    매 N 에폭마다 전체 train 임베딩을 계산하고,
    각 샘플의 k-NN 중 다른 카테고리인 것을 hard negative로 마킹.
    서브샘플링 시 hard negative 비율을 높여 학습 효과 극대화.
    """

    def __init__(self, k: int = 32, ratio: float = 0.3):
        self.k = k
        self.ratio = ratio  # 서브샘플에서 hard negative 비율
        self._hard_indices: set[int] = set()

    @torch.no_grad()
    def refresh(self, model, graphs: list, labels: np.ndarray, device: str = "cpu"):
        """전체 임베딩 계산 후 hard negative 인덱스 갱신."""
        from torch_geometric.loader import DataLoader as PyGLoader

        model.eval()
        loader = PyGLoader(graphs, batch_size=256, shuffle=False)
        all_emb = []
        for batch in loader:
            batch = batch.to(device)
            emb = model(batch.x, batch.edge_index, batch.batch)
            all_emb.append(emb.cpu())

        all_emb = torch.cat(all_emb, dim=0)
        all_emb = F.normalize(all_emb, p=2, dim=1)

        # 코사인 유사도 기반 k-NN
        sim_matrix = torch.matmul(all_emb, all_emb.T)
        n = len(labels)
        hard_set: set[int] = set()

        for i in range(n):
            topk_indices = sim_matrix[i].topk(self.k + 1).indices[1:]  # self 제외
            for j in topk_indices.tolist():
                if labels[i] != labels[j]:
                    hard_set.add(i)
                    hard_set.add(j)
                    break  # 가장 가까운 hard negative만

        self._hard_indices = hard_set
        print(f"  Hard negatives: {len(hard_set)}/{n} ({len(hard_set)/n*100:.1f}%)")

    def subsample_with_hard(
        self, n_total: int, n_subsample: int, rng: np.random.Generator,
    ) -> np.ndarray:
        """hard negative를 우선 포함하는 서브샘플 인덱스 반환."""
        if not self._hard_indices:
            return rng.choice(n_total, size=n_subsample, replace=False)

        hard_list = np.array(list(self._hard_indices))
        n_hard = min(int(n_subsample * self.ratio), len(hard_list))
        n_random = n_subsample - n_hard

        hard_chosen = rng.choice(hard_list, size=n_hard, replace=False)
        remaining = np.setdiff1d(np.arange(n_total), hard_chosen)
        random_chosen = rng.choice(remaining, size=min(n_random, len(remaining)), replace=False)

        return np.concatenate([hard_chosen, random_chosen])


# ─────────────────────────────────────────────
# Graph Augmentation
# ─────────────────────────────────────────────

def augment_batch(batch, noise_std=0.01):
    """배치 전체에 가우시안 노이즈 (간소화 증강)."""
    noise = torch.randn_like(batch.x) * noise_std
    noise[:, :8] = 0  # one-hot 부분은 노이즈 안 줌
    batch.x = batch.x + noise
    return batch


# ─────────────────────────────────────────────
# Evaluation
# ─────────────────────────────────────────────

@torch.no_grad()
def evaluate_recall(model, loader, ks=(1, 5, 10)):
    """k-NN 기반 Recall@K 평가 (CPU)."""
    model.eval()
    all_embeddings = []
    all_labels = []

    for batch in loader:
        emb = model(batch.x, batch.edge_index, batch.batch)
        all_embeddings.append(emb)
        all_labels.append(batch.y)

    embeddings = torch.cat(all_embeddings, dim=0)
    labels = torch.cat(all_labels, dim=0)

    # 코사인 유사도 행렬
    sim = torch.matmul(embeddings, embeddings.T)
    sim.fill_diagonal_(float("-inf"))

    recalls = {}
    for k in ks:
        topk_idx = sim.topk(k, dim=1).indices
        topk_labels = labels[topk_idx]
        match = (topk_labels == labels.unsqueeze(1)).any(dim=1)
        recalls[f"R@{k}"] = match.float().mean().item()

    return recalls


# ─────────────────────────────────────────────
# Training
# ─────────────────────────────────────────────

def train_one_epoch(model, loader, optimizer, criterion, augment=True):
    """1 에폭 학습 (CPU)."""
    model.train()
    total_loss = 0.0
    n_batches = 0

    for batch in loader:
        if augment:
            batch = augment_batch(batch)

        embeddings = model(batch.x, batch.edge_index, batch.batch)
        loss = criterion(embeddings, batch.y)

        optimizer.zero_grad()
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
        optimizer.step()

        total_loss += loss.item()
        n_batches += 1

    return total_loss / max(n_batches, 1)


def main():
    parser = argparse.ArgumentParser(description="GNN (GIN) SupCon 학습 v2")
    parser.add_argument("--dxf_dirs", nargs="+", required=True)
    parser.add_argument("--output_dir", default="./gnn_runs")
    parser.add_argument("--cache_dir", default="")
    parser.add_argument("--epochs", type=int, default=50)
    parser.add_argument("--batch", type=int, default=256)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--hidden", type=int, default=128)
    parser.add_argument("--out_dim", type=int, default=256)
    parser.add_argument("--num_layers", type=int, default=4)
    parser.add_argument("--temperature", type=float, default=0.07)
    parser.add_argument("--k_neighbors", type=int, default=8)
    parser.add_argument("--max_nodes", type=int, default=5000)
    parser.add_argument("--workers", type=int, default=0)
    parser.add_argument("--val_split", type=float, default=0.1)
    parser.add_argument("--subsample_ratio", type=float, default=0.3,
                        help="에폭당 train 데이터 사용 비율 (기본 30%%)")
    parser.add_argument("--checkpoint_interval", type=int, default=5)
    parser.add_argument("--resume", default="")
    parser.add_argument("--hard_negative_ratio", type=float, default=0.3,
                        help="Hard negative 샘플 비율 (0이면 비활성)")
    parser.add_argument("--hard_negative_start_epoch", type=int, default=5,
                        help="Hard negative mining 시작 에폭")
    parser.add_argument("--hard_negative_refresh", type=int, default=5,
                        help="Hard negative 인덱스 갱신 주기 (에폭)")
    parser.add_argument("--patience", type=int, default=10,
                        help="R@5 개선 없으면 조기 종료 (0=비활성)")
    args = parser.parse_args()

    # ── CPU 강제 ──
    device = "cpu"
    print(f"디바이스: {device}")
    print(f"서브샘플링: {args.subsample_ratio*100:.0f}% / 에폭")

    # 출력 디렉토리
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # ── InMemory 데이터셋 로딩 ──
    builder = DXFGraphBuilder(k_neighbors=args.k_neighbors, max_nodes=args.max_nodes)
    dataset = InMemoryDXFDataset(args.dxf_dirs, builder, cache_dir=args.cache_dir)

    if len(dataset) == 0:
        print("[ERROR] 데이터셋이 비어있습니다.")
        sys.exit(1)

    # Train/Val split
    from torch_geometric.loader import DataLoader

    n_val = int(len(dataset) * args.val_split)
    n_train = len(dataset) - n_val

    indices = list(range(len(dataset)))
    np.random.seed(42)
    np.random.shuffle(indices)
    train_indices = indices[:n_train]
    val_indices = indices[n_train:]

    train_graphs = [dataset[i] for i in train_indices]
    val_graphs = [dataset[i] for i in val_indices]
    train_labels = np.array([g.y.item() for g in train_graphs])

    print(f"Train: {len(train_graphs)}, Val: {len(val_graphs)}")

    # Val loader는 고정
    val_loader = DataLoader(val_graphs, batch_size=args.batch, shuffle=False)

    # RAM 사용량 체크
    import psutil
    process = psutil.Process()
    mem_mb = process.memory_info().rss / 1024 / 1024
    print(f"메모리 사용: {mem_mb:.0f} MB")

    # 모델
    model = GINEncoder(
        in_channels=NODE_FEATURE_DIM,
        hidden_channels=args.hidden,
        out_channels=args.out_dim,
        num_layers=args.num_layers,
    )
    print(f"모델 파라미터: {sum(p.numel() for p in model.parameters()):,}")

    # 옵티마이저 + 스케줄러
    optimizer = AdamW(model.parameters(), lr=args.lr, weight_decay=1e-4)
    scheduler = CosineAnnealingLR(optimizer, T_max=args.epochs)
    criterion = SupConLoss(temperature=args.temperature)

    start_epoch = 0
    best_recall = 0.0
    patience_counter = 0

    # Resume
    if args.resume and Path(args.resume).exists():
        ckpt = torch.load(args.resume, map_location=device, weights_only=True)
        model.load_state_dict(ckpt["model_state_dict"])
        optimizer.load_state_dict(ckpt["optimizer_state_dict"])
        start_epoch = ckpt.get("epoch", 0) + 1
        best_recall = ckpt.get("best_recall", 0.0)
        print(f"Resume from epoch {start_epoch}, best R@5={best_recall:.4f}")

    # 학습 로그
    log_path = output_dir / "train_log.json"
    logs = []

    print(f"\n{'='*60}")
    print(f"GNN (GIN) SupCon 학습 v2 시작")
    print(f"  InMemory={len(dataset)} | Train={len(train_graphs)} | Val={len(val_graphs)}")
    print(f"  Subsample={args.subsample_ratio*100:.0f}% ({int(len(train_graphs)*args.subsample_ratio)}/epoch)")
    # Hard Negative Miner
    hn_miner: HardNegativeMiner | None = None
    if args.hard_negative_ratio > 0:
        hn_miner = HardNegativeMiner(k=32, ratio=args.hard_negative_ratio)
        print(f"  HardNeg={args.hard_negative_ratio*100:.0f}% (start={args.hard_negative_start_epoch}, refresh={args.hard_negative_refresh})")

    print(f"  Batch={args.batch} | LR={args.lr} | Patience={args.patience}")
    print(f"{'='*60}\n")

    rng = np.random.default_rng(42)

    for epoch in range(start_epoch, args.epochs):
        t0 = time.time()

        # Hard negative 인덱스 갱신
        if (hn_miner and epoch >= args.hard_negative_start_epoch
                and (epoch - args.hard_negative_start_epoch) % args.hard_negative_refresh == 0):
            hn_miner.refresh(model, train_graphs, train_labels, device)

        # ── 에폭당 서브샘플링 (hard negative 우선 포함) ──
        n_subsample = max(args.batch * 2, int(len(train_graphs) * args.subsample_ratio))
        if hn_miner and epoch >= args.hard_negative_start_epoch:
            sub_indices = hn_miner.subsample_with_hard(len(train_graphs), n_subsample, rng)
        else:
            sub_indices = rng.choice(len(train_graphs), size=n_subsample, replace=False)
        sub_graphs = [train_graphs[i] for i in sub_indices]
        train_loader = DataLoader(sub_graphs, batch_size=args.batch, shuffle=True)

        train_loss = train_one_epoch(model, train_loader, optimizer, criterion)
        scheduler.step()

        # 검증
        recalls = evaluate_recall(model, val_loader, ks=(1, 5, 10))
        elapsed = time.time() - t0

        log_entry = {
            "epoch": epoch,
            "train_loss": round(train_loss, 4),
            "lr": round(optimizer.param_groups[0]["lr"], 6),
            "elapsed_sec": round(elapsed, 1),
            **{k: round(v, 4) for k, v in recalls.items()},
        }
        logs.append(log_entry)

        print(
            f"[Epoch {epoch+1:3d}/{args.epochs}] "
            f"loss={train_loss:.4f} | "
            f"R@1={recalls['R@1']:.4f} R@5={recalls['R@5']:.4f} R@10={recalls['R@10']:.4f} | "
            f"lr={optimizer.param_groups[0]['lr']:.6f} | "
            f"{elapsed:.1f}s"
        )

        # Best 모델 저장
        if recalls["R@5"] > best_recall:
            best_recall = recalls["R@5"]
            patience_counter = 0
            best_path = output_dir / "gnn_encoder_best.pt"
            torch.save({
                "model_state_dict": model.state_dict(),
                "config": {
                    "in_channels": NODE_FEATURE_DIM,
                    "hidden_channels": args.hidden,
                    "out_channels": args.out_dim,
                    "num_layers": args.num_layers,
                },
                "epoch": epoch,
                "best_recall": best_recall,
                "categories": dataset.categories,
            }, best_path)
            print(f"  -> Best model saved (R@5={best_recall:.4f})")
        else:
            patience_counter += 1

        # Early stopping
        if args.patience > 0 and patience_counter >= args.patience:
            print(f"\n  Early stopping at epoch {epoch+1} (no R@5 improvement for {args.patience} epochs)")
            break

        # 주기적 체크포인트
        if (epoch + 1) % args.checkpoint_interval == 0:
            ckpt_path = output_dir / f"checkpoint_epoch{epoch+1}.pt"
            torch.save({
                "model_state_dict": model.state_dict(),
                "optimizer_state_dict": optimizer.state_dict(),
                "epoch": epoch,
                "best_recall": best_recall,
            }, ckpt_path)

        # 로그 저장
        with open(log_path, "w", encoding="utf-8") as f:
            json.dump(logs, f, indent=2, ensure_ascii=False)

        # 메모리 정리
        gc.collect()

    print(f"\n{'='*60}")
    print(f"학습 완료. Best R@5={best_recall:.4f}")
    print(f"Best model: {output_dir / 'gnn_encoder_best.pt'}")
    print(f"Log: {log_path}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()

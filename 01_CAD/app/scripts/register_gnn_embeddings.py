#!/usr/bin/env python3
"""
GNN 임베딩 전용 등록 스크립트 (방안 E)

기존 ChromaDB의 image/text 컬렉션을 건드리지 않고,
gnn 컬렉션에만 DXF 구조 임베딩을 등록한다.

1. records.json의 drawing_id ↔ DXF 파일명 매핑
2. SSD 캐시 활용 (train_gnn에서 생성한 그래프 캐시)
3. GNN 모델로 임베딩 생성 → gnn 컬렉션 직접 등록
4. 배치 처리 + resume 지원

사용법:
  python scripts/register_gnn_embeddings.py
  python scripts/register_gnn_embeddings.py --cache-dir /tmp/gnn_cache_ssd
  python scripts/register_gnn_embeddings.py --reset  # 기존 gnn 컬렉션 초기화
"""

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np
import torch

sys.path.insert(0, str(Path(__file__).parent.parent))


def main():
    parser = argparse.ArgumentParser(description="GNN 임베딩 전용 등록")
    parser.add_argument("--data", default="./data/vector_store")
    parser.add_argument("--dxf-dirs", nargs="+", default=[
        "../data/MiSUMi_data",
        "../data/Unit_bearing_dxf",
    ])
    parser.add_argument("--gnn-model", default="./models/gnn_encoder.pt")
    parser.add_argument("--cache-dir", default="/tmp/gnn_cache_ssd",
                        help="train_gnn에서 생성한 그래프 캐시 디렉토리")
    parser.add_argument("--batch-size", type=int, default=128)
    parser.add_argument("--reset", action="store_true")
    args = parser.parse_args()

    print("=" * 60)
    print("  GNN 임베딩 전용 등록 (gnn 컬렉션만)")
    print("=" * 60)

    # ── 1. records.json 로드 ──
    records_path = Path(args.data) / "records.json"
    with open(records_path, "r", encoding="utf-8") as f:
        records = json.load(f)
    print(f"\n  레코드: {len(records):,}건")

    # ── 2. DXF 파일 인덱스 (stem → path) ──
    dxf_index: dict[str, str] = {}
    for dxf_dir in args.dxf_dirs:
        dxf_path = Path(dxf_dir)
        if not dxf_path.exists():
            print(f"  [WARN] DXF 디렉토리 없음: {dxf_dir}")
            continue
        for f in dxf_path.rglob("*.dxf"):
            dxf_index[f.stem.lower()] = str(f)
    print(f"  DXF 인덱스: {len(dxf_index):,}개")

    # ── 3. drawing_id ↔ DXF 매핑 ──
    id_to_dxf: list[tuple[str, str]] = []
    for did, rdata in records.items():
        fname = rdata.get("file_name", "")
        stem = Path(fname).stem.lower()
        if stem in dxf_index:
            id_to_dxf.append((did, dxf_index[stem]))
    print(f"  DXF 매칭: {len(id_to_dxf):,}건 ({len(id_to_dxf)/len(records)*100:.1f}%)")

    if not id_to_dxf:
        print("  [ERROR] 매칭된 DXF 없음. 종료.")
        return

    # ── 4. ChromaDB gnn 컬렉션 접근 ──
    import chromadb
    client = chromadb.PersistentClient(path=args.data)

    if args.reset:
        try:
            client.delete_collection("drawings_gnn")
            print("  [RESET] gnn 컬렉션 삭제")
        except Exception:
            pass

    gnn_col = client.get_or_create_collection(
        name="drawings_gnn",
        metadata={"hnsw:space": "cosine"},
    )
    existing_count = gnn_col.count()
    print(f"  gnn 컬렉션 기존: {existing_count:,}건")

    # ── 5. 진행 상태 (resume) ──
    progress_path = Path(args.data) / "gnn_register_progress.json"
    start_idx = 0
    if progress_path.exists() and not args.reset:
        with open(progress_path) as f:
            prog = json.load(f)
        start_idx = prog.get("last_index", 0) + 1
        if start_idx >= len(id_to_dxf):
            print(f"  이미 완료됨. --reset으로 재시작하세요.")
            return
        print(f"  Resume: {start_idx}/{len(id_to_dxf)}")

    # ── 6. GNN 모델 로딩 ──
    print(f"\n  GNN 모델 로딩: {args.gnn_model}")
    from core.gnn import GINEncoder, DXFGraphBuilder, NODE_FEATURE_DIM

    builder = DXFGraphBuilder(k_neighbors=8)
    device = torch.device("cpu")

    model = GINEncoder(NODE_FEATURE_DIM, hidden_channels=128, out_channels=256, num_layers=4)
    ckpt = torch.load(args.gnn_model, map_location=device, weights_only=True)
    state = ckpt.get("model_state_dict", ckpt)
    model.load_state_dict(state)
    model.eval()
    print("  GNN 모델 로딩 완료")

    # ── 7. 캐시 인덱스 (DXF path → cache file) ──
    # train_gnn.py는 프로젝트 루트에서 실행 → 경로가 "data/MiSUMi_data/..." 형식
    # 등록 스크립트는 app/ 에서 실행 → 경로가 "../data/MiSUMi_data/..." 형식
    # 캐시 조회 시 학습 때와 동일한 경로로 해시해야 매칭됨
    cache_dir = Path(args.cache_dir) if args.cache_dir else None
    cache_index: dict[str, Path] = {}
    dxf_to_train_path: dict[str, str] = {}  # 등록경로 → 학습경로 매핑
    if cache_dir and cache_dir.exists():
        for did, dxf_path in id_to_dxf:
            # "../data/X" → "data/X" (학습 시 경로)
            train_path = dxf_path
            if "../data/" in train_path:
                train_path = train_path.replace("../data/", "data/", 1)
            path_hash = hashlib.md5(str(train_path).encode()).hexdigest()[:8]
            cache_file = cache_dir / f"{Path(dxf_path).stem}_{path_hash}.pt"
            if cache_file.exists():
                cache_index[dxf_path] = cache_file
                dxf_to_train_path[dxf_path] = train_path
        print(f"  캐시 히트: {len(cache_index):,}/{len(id_to_dxf):,}")

    # ── 8. 배치 임베딩 + 등록 ──
    print(f"\n  등록 시작 (batch={args.batch_size}, from={start_idx})...")
    t_start = time.time()
    success = 0
    errors = 0
    batch_ids: list[str] = []
    batch_embs: list[list[float]] = []
    batch_metas: list[dict] = []

    def flush_batch():
        nonlocal batch_ids, batch_embs, batch_metas
        if not batch_ids:
            return
        gnn_col.upsert(
            ids=batch_ids,
            embeddings=batch_embs,
            metadatas=batch_metas,
        )
        batch_ids, batch_embs, batch_metas = [], [], []

    for i in range(start_idx, len(id_to_dxf)):
        did, dxf_path = id_to_dxf[i]

        try:
            # 캐시에서 그래프 로드 or DXF 파싱
            if dxf_path in cache_index:
                data = torch.load(cache_index[dxf_path], weights_only=False)
            else:
                data = builder.build_graph(dxf_path)

            if data is None or data.x.shape[0] == 0:
                errors += 1
                continue

            # Forward
            with torch.no_grad():
                emb = model(data.x, data.edge_index, data.batch if hasattr(data, 'batch') and data.batch is not None else torch.zeros(data.x.shape[0], dtype=torch.long))
            emb_np = emb.squeeze(0).cpu().numpy().tolist()

            rdata = records.get(did, {})
            meta = {
                "file_name": rdata.get("file_name", ""),
                "category": rdata.get("category", ""),
                "dxf_path": dxf_path,
            }

            batch_ids.append(did)
            batch_embs.append(emb_np)
            batch_metas.append(meta)
            success += 1

            # 배치 flush
            if len(batch_ids) >= args.batch_size:
                flush_batch()

        except Exception as e:
            errors += 1
            if errors <= 10:
                print(f"    [ERROR] {did}: {e}")

        # 진행 저장 (500건마다)
        if (i + 1) % 500 == 0 or i == len(id_to_dxf) - 1:
            flush_batch()
            elapsed = time.time() - t_start
            rate = (i - start_idx + 1) / elapsed if elapsed > 0 else 0
            remaining = (len(id_to_dxf) - i - 1) / rate if rate > 0 else 0
            with open(progress_path, "w") as f:
                json.dump({"last_index": i, "total": len(id_to_dxf), "success": success, "errors": errors}, f)
            print(f"    [{i+1:,}/{len(id_to_dxf):,}] 성공={success:,} 실패={errors} | {rate:.1f}건/초 | 남은: {remaining/60:.1f}분")

    flush_batch()
    elapsed = time.time() - t_start

    # ── 9. 결과 ──
    print(f"\n{'=' * 60}")
    print(f"  GNN 임베딩 등록 완료")
    print(f"{'=' * 60}")
    print(f"  성공: {success:,}건 / 실패: {errors}건")
    print(f"  소요: {elapsed/60:.1f}분 ({success/elapsed:.1f}건/초)")
    print(f"  gnn 컬렉션: {gnn_col.count():,}건")

    if progress_path.exists():
        progress_path.unlink()
    print("  완료!")


if __name__ == "__main__":
    main()

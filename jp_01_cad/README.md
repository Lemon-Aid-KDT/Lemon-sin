# CAD Vision v4.0 — AI Drawing Search Engine

산업용 CAD 도면을 AI로 분류 · 검색 · 분석하는 풀스택 시스템

## Overview

| 항목 | 내용 |
|------|------|
| **데이터** | 9개 소스, 68,649건 산업용 도면 (PNG/DXF) |
| **분류** | YOLO-cls v2 — 81 카테고리, Top-1 **93.87%** |
| **검색** | 3채널 하이브리드: OpenCLIP(0.1) + E5(0.6) + GNN(0.3) |
| **GNN** | GIN 구조 검색 — DXF 그래프 임베딩, R@5 = **0.765** |
| **벡터DB** | ChromaDB 3채널 — image 61,475 / text 68,649 / gnn 61,454 |
| **탐지** | YOLO-det mAP50 = 0.552 |
| **분석** | Ollama Qwen3.5 (RAM 기반 자동 선택) + 스트리밍 응답 |
| **Reranker** | Cross-encoder 2차 정밀 정렬 |
| **Backend** | FastAPI REST API (15 엔드포인트) + Streamlit UI |
| **배포** | Docker Compose (app + Ollama) |
| **테스트** | 573 tests passing |

## Architecture

```
                        ┌─────────────────────────────────┐
                        │         CAD Vision v4.0          │
                        └─────────────┬───────────────────┘
                                      │
        ┌─────────────┬───────────────┼───────────────┬─────────────┐
        ▼             ▼               ▼               ▼             ▼
   YOLO-cls      OpenCLIP        PaddleOCR       GNN (GIN)     YOLO-det
   (81 cat)    ViT-L/14 768d    텍스트 추출    DXF→Graph→256d   영역 탐지
        │             │               │               │             │
        └─────────────┴───────┬───────┴───────────────┘             │
                              ▼                                     │
                    ChromaDB 3채널 벡터 DB                           │
                  (image + text + gnn)                              │
                              │                                     │
                              ▼                                     │
                   Reranker (Cross-Encoder)                         │
                              │                                     │
                              ▼                                     ▼
                    Ollama Qwen3.5 LLM  ◄──────────── 컨텍스트 주입
                    (스트리밍 응답)         (YOLO/OCR/탐지 결과)
                              │
                    ┌─────────┴─────────┐
                    ▼                   ▼
              Streamlit UI        FastAPI REST
              :8501               :8000/docs
```

## v4.0 New Features

### Phase 1-4: Core Upgrades
- **YOLO26 + Qwen3.5**: RAM 기반 자동 모델 선택 (48GB→27b, 16GB→9b, <16GB→4b)
- **OpenCLIP ViT-L/14**: 512→768차원 이미지 임베딩 업그레이드
- **GNN 구조 검색**: DXF→Graph→GIN 임베딩, 3채널 하이브리드 검색
- **DXF 네이티브**: DXF 파일 업로드→PNG 렌더링→파이프라인 자동 연결

### Tier 1: Practical Value
- **REST API**: FastAPI 15개 엔드포인트 (CORS, Rate Limiting, Magic bytes)
- **유사도면 알림**: 등록 시 유사도 85%+ 자동 경고
- **증분 임베딩**: scan-only + watch 모드
- **Docker**: Streamlit + FastAPI + Ollama 동시 실행

### Tier 2: Search Quality
- **Reranker**: Cross-encoder ms-marco-MiniLM-L-6-v2 2차 정렬
- **OCR 병렬화**: ProcessPoolExecutor 배치 처리

### Tier 3: Feature Extensions
- **BOM 자동 추출**: regex + LLM 2단계 부품표 추출
- **DXF diff**: 2개 DXF 구조 비교 시각화
- **치수 자동 비교**: 6패턴 파싱 + diff

### Tier 4: Strategic
- **SQLite 마이그레이션**: records.json → SQLite (WAL mode, 동시 접근)
- **사용자 피드백 루프**: 검색 관련/무관 → JSONL 학습 데이터 내보내기
- **Multi-positive contrastive loss**: CLIP fine-tuning 학습 스크립트

## Project Structure

```
jp_01_cad/
├── app/                        # 메인 애플리케이션
│   ├── app/                    # Streamlit UI + FastAPI
│   │   ├── streamlit_app.py    # Streamlit 풀스택 UI
│   │   └── api/                # FastAPI REST API
│   ├── config/settings.py      # 전역 설정 (Pydantic)
│   ├── core/                   # 핵심 엔진 (14개 모듈)
│   │   ├── pipeline.py         # 통합 파이프라인
│   │   ├── classifier.py       # YOLO-cls 분류기
│   │   ├── detector.py         # YOLO-det 탐지기
│   │   ├── embeddings.py       # OpenCLIP/E5 임베딩
│   │   ├── gnn.py              # GNN (GIN) DXF 구조 임베딩
│   │   ├── vector_store.py     # ChromaDB 3채널
│   │   ├── reranker.py         # Cross-encoder reranker
│   │   ├── llm.py              # Ollama LLM (스트리밍)
│   │   ├── ocr.py              # PaddleOCR
│   │   ├── dxf_renderer.py     # DXF→PNG 렌더링
│   │   ├── dxf_diff.py         # DXF 구조 비교
│   │   ├── bom_extractor.py    # BOM 자동 추출
│   │   ├── dimension_parser.py # 치수 파싱/비교
│   │   ├── record_store.py     # SQLite 레코드 저장소
│   │   └── feedback_store.py   # 사용자 피드백 DB
│   ├── scripts/                # 유틸리티 스크립트
│   ├── tests/                  # 573 테스트
│   ├── docs/                   # 가이드 문서
│   ├── Dockerfile              # Docker 빌드
│   ├── docker-compose.yml      # Docker Compose
│   └── run_api.py              # FastAPI 서버 실행
├── training/                   # 학습 파이프라인
│   ├── scripts/
│   │   ├── train_gnn.py        # GNN SupCon 학습 (InMemoryDataset)
│   │   └── train_clip_multipos.py  # CLIP Multi-positive 학습
│   └── PROJECT_GUIDE.md
└── data/                       # 카테고리 매핑 메타데이터
```

## Key Results

### YOLO-cls v2
- 81 카테고리, Test Top-1 **93.87%** / Top-5 **98.04%**

### GNN Structural Search (v2)
- 54,722 DXF, 72 카테고리, 50 에폭
- R@1 = **0.614** / R@5 = **0.765** / R@10 = **0.827**

### CLIP Fine-tuning
- OpenCLIP ViT-L/14 (768-dim)
- Image→Text R@5: 0.7% → **11.6%** (16x)

### Metadata Enrichment
- 부품번호 추출: 60,456건 (파일명 기반)
- 재질 매핑: 60,721건 (카테고리-재질 자동 매핑, 75 항목)

## Tech Stack

| 영역 | 기술 |
|------|------|
| Language | Python 3.11 |
| Deep Learning | PyTorch, YOLO, OpenCLIP ViT-L/14, E5-multilingual-small |
| GNN | PyTorch Geometric, GIN (Graph Isomorphism Network) |
| Vector DB | ChromaDB (3-channel: image/text/gnn) |
| OCR | PaddleOCR |
| LLM | Ollama + Qwen3.5 (RAM auto-selection) |
| Reranker | Cross-encoder (ms-marco-MiniLM-L-6-v2) |
| Backend | FastAPI + Streamlit |
| Deploy | Docker Compose |
| Testing | pytest (573 tests) |

## Quick Start

```bash
# 로컬 실행
cd app
pip install -r requirements.txt

# Streamlit + FastAPI 동시 실행
python run_api.py &                                      # API → http://localhost:8000/docs
streamlit run app/streamlit_app.py --server.port 8501 &  # UI  → http://localhost:8501

# 종료
kill $(lsof -t -i:8000) $(lsof -t -i:8501) 2>/dev/null

# Docker 실행
cd app
./docker-start.sh            # 빌드 + 시작
./docker-start.sh --down     # 종료
```

## Documentation

- [`app/README.md`](app/README.md) — 메인 앱 상세 README
- [`app/PROJECT_SPEC.md`](app/PROJECT_SPEC.md) — 프로젝트 기능 명세 (v4.0)
- [`app/docs/GUIDE_DEVELOPER.md`](app/docs/GUIDE_DEVELOPER.md) — 개발자 가이드
- [`app/docs/GUIDE_USER.md`](app/docs/GUIDE_USER.md) — 사용자 가이드
- [`training/PROJECT_GUIDE.md`](training/PROJECT_GUIDE.md) — 학습 파이프라인 가이드

## Note

> 이미지 데이터, 모델 가중치(`.pt`), 벡터DB는 저작권 및 용량 문제로 포함되지 않습니다.
> 모델과 데이터는 별도 준비가 필요합니다.

---

**v4.0** | 2026-03-23

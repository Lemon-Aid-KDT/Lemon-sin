# ============================================================
#  CAD Vision v4.0 — Dockerfile
#  Python 3.11 + Streamlit + FastAPI + ML Models
#  (OpenCLIP ViT-L/14, E5, GNN, PaddleOCR, YOLO, Reranker)
#
#  보안 강화:
#    - 비루트 사용자(appuser)로 실행
#    - 경로를 환경 변수로 설정 (하드코딩 제거)
#    - PYTHONDONTWRITEBYTECODE로 .pyc 파일 생성 방지
# ============================================================

FROM python:3.11-slim AS base

# 시스템 의존성
RUN apt-get update && apt-get install -y --no-install-recommends \
        poppler-utils \
        libgomp1 \
        libglib2.0-0 \
        libgl1 \
        libsm6 \
        libxext6 \
        libxrender1 \
        git \
        curl \
        supervisor \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# --- Python 의존성 (캐시 레이어) ---
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip "setuptools<81" wheel \
    && pip install --no-cache-dir -r requirements.txt

# --- 모델 프리로드 (빌드 시 다운로드 → 런타임 대기 제거) ---
COPY scripts/preload_models.py scripts/preload_models.py
RUN python scripts/preload_models.py

# --- 앱 소스 복사 ---
COPY . .

# --- 데이터/모델/로그 디렉토리 (볼륨 마운트 포인트) ---
RUN mkdir -p /app/models /app/data/sample_drawings /app/data/vector_store /app/data/feedback /app/logs

# --- 비루트 사용자 생성 (보안: 컨테이너 내 최소 권한) ---
RUN groupadd --gid 1000 appuser \
    && useradd --uid 1000 --gid appuser --shell /bin/bash --create-home appuser \
    && chown -R appuser:appuser /app

USER appuser

# --- 환경 변수 설정 ---
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV STREAMLIT_SERVER_PORT=8501
ENV STREAMLIT_SERVER_ADDRESS=0.0.0.0
ENV STREAMLIT_SERVER_HEADLESS=true
ENV STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

# 경로를 환경 변수로 설정 (docker-compose.yml에서 오버라이드 가능)
ENV UPLOAD_DIR=/app/data/sample_drawings
ENV CHROMA_PERSIST_DIR=/app/data/vector_store
ENV YOLO_CLS_MODEL_PATH=/app/models/yolo_cls_v2_best.pt
ENV YOLO_DET_MODEL_PATH=/app/models/yolo_det_best.pt
ENV GNN_MODEL_PATH=/app/models/gnn_encoder.pt
ENV SQLITE_DB_PATH=/app/data/vector_store/records.db
ENV FEEDBACK_DB_PATH=/app/data/feedback/feedback.db
ENV LOG_FILE=/app/logs/drawingllm.log

EXPOSE 8501 8000

# --- supervisord 설정 ---
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# --- 헬스체크 (Streamlit + FastAPI) ---
HEALTHCHECK --interval=30s --timeout=10s --start-period=90s --retries=3 \
    CMD curl -f http://localhost:8501/_stcore/health && curl -f http://localhost:8000/api/v1/stats || exit 1

# --- 실행 (supervisord로 Streamlit + FastAPI 동시 실행) ---
CMD ["supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]

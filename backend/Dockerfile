FROM python:3.13-slim

ARG INSTALL_LOCAL_OCR=true
ARG INSTALL_VISION=false
ARG PRELOAD_PADDLEOCR=false
ARG PRELOAD_PADDLEOCR_LANGUAGE=korean

ENV PATH="/opt/venv/bin:${PATH}" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/Nutrition-backend \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK=true

WORKDIR /app

RUN apt-get update \
    && apt-get install --no-install-recommends -y \
        ca-certificates \
        curl \
        libgl1 \
        libglib2.0-0 \
        libgomp1 \
    && rm -rf /var/lib/apt/lists/* \
    && python -m venv /opt/venv \
    && groupadd --system lemon \
    && useradd --system --gid lemon --create-home --home-dir /home/lemon lemon

COPY requirements.txt pyproject.toml ./

RUN pip install --upgrade pip \
    && pip install -r requirements.txt \
    && if [ "${INSTALL_LOCAL_OCR}" = "true" ]; then \
        pip install "paddlepaddle==3.2.0" "paddleocr>=3.0"; \
    fi \
    && if [ "${INSTALL_VISION}" = "true" ]; then \
        pip install "torch>=2.2" "ultralytics>=8.1"; \
    fi

COPY alembic.ini ./
COPY alembic ./alembic
COPY Nutrition-backend ./Nutrition-backend
COPY scripts ./scripts

RUN if [ "${PRELOAD_PADDLEOCR}" = "true" ]; then \
        LOCAL_OCR_LANGUAGE="${PRELOAD_PADDLEOCR_LANGUAGE}" python scripts/preload_paddleocr.py; \
    fi \
    && mkdir -p /home/lemon/.paddlex \
    && chown -R lemon:lemon /app /home/lemon /opt/venv

USER lemon

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -fsS http://localhost:8000/health || exit 1

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]

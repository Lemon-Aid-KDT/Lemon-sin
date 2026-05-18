# syntax=docker/dockerfile:1.7
#
# Lemon Healthcare backend image.
#
# Multi-stage build:
#   - ``builder`` resolves the Python dependency graph including the
#     ``[ocr-local]`` extras so PaddleOCR is present in the runtime venv.
#   - ``runtime`` carries only the libraries the FastAPI process needs
#     plus the PaddleOCR model cache produced by ``preload_paddleocr.py``.
#
# The runtime stage sets ``PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK=true`` so
# the first /supplements/analyze call never reaches an external model
# hoster — this matches the closed-network policy (docs/32 §6 + PR-L).

ARG PYTHON_VERSION=3.13-slim-bookworm

# ---------------------------------------------------------------------------
# Stage 1 — builder
# ---------------------------------------------------------------------------
FROM python:${PYTHON_VERSION} AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

# System packages required to build PaddleOCR + Pillow wheels on slim.
RUN apt-get update \
    && apt-get install --no-install-recommends -y \
        build-essential \
        libgomp1 \
        libgl1 \
        libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build

# Copy only the metadata first so dependency installs cache cleanly.
COPY pyproject.toml requirements.txt ./
COPY Nutrition-backend/src/__init__.py Nutrition-backend/src/__init__.py

# Resolve a private venv. The runtime stage copies this directory verbatim.
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

RUN pip install --upgrade pip wheel \
    && pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir "paddleocr>=3.0"

# Bring in the rest of the source so editable layout helpers work in tests.
COPY . /build

# ---------------------------------------------------------------------------
# Stage 2 — runtime
# ---------------------------------------------------------------------------
FROM python:${PYTHON_VERSION} AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PATH="/opt/venv/bin:$PATH" \
    PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK=true \
    PYTHONPATH=/app/Nutrition-backend

RUN apt-get update \
    && apt-get install --no-install-recommends -y \
        libgomp1 \
        libgl1 \
        libglib2.0-0 \
        curl \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --system lemon \
    && useradd --system --gid lemon --create-home --home-dir /home/lemon lemon

COPY --from=builder /opt/venv /opt/venv
COPY --from=builder /build /app

WORKDIR /app

# Pre-warm the PaddleOCR model cache so first request is offline-friendly.
RUN python scripts/preload_paddleocr.py \
    && chown -R lemon:lemon /home/lemon /app /opt/venv

USER lemon

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -fsS http://localhost:8000/health || exit 1

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]

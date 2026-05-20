FROM python:3.13-slim

ARG INSTALL_PADDLEOCR=false

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app/Nutrition-backend

WORKDIR /app

COPY requirements.txt ./requirements.txt
RUN python -m pip install --upgrade pip \
    && python -m pip install -r requirements.txt
RUN if [ "$INSTALL_PADDLEOCR" = "true" ]; then \
      python -m pip install paddlepaddle==3.2.0 -i https://www.paddlepaddle.org.cn/packages/stable/cpu/ \
      && python -m pip install "paddleocr[all]>=3.0"; \
    fi

COPY Nutrition-backend ./Nutrition-backend
COPY alembic ./alembic
COPY alembic.ini ./alembic.ini

EXPOSE 8080

CMD ["sh", "-c", "python -m uvicorn src.main:app --host 0.0.0.0 --port ${PORT:-8080}"]

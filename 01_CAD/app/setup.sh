#!/bin/bash
# DrawingLLM 설치 및 실행 스크립트

set -e

echo "=========================================="
echo "  DrawingLLM — 설치 스크립트"
echo "=========================================="

# 1. Python 가상환경 생성
echo ""
echo "[1/5] Python 가상환경 생성..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "  ✅ 가상환경 생성 완료"
else
    echo "  ✅ 가상환경 이미 존재"
fi

source venv/bin/activate

# 2. 의존성 설치
echo ""
echo "[2/5] 의존성 설치..."
pip install --upgrade pip
pip install -r requirements.txt
echo "  ✅ 의존성 설치 완료"

# 3. Ollama 확인
echo ""
echo "[3/5] Ollama 서버 확인..."
if command -v ollama &> /dev/null; then
    echo "  ✅ Ollama 설치됨"
    echo "  모델 다운로드 (최초 1회):"
    echo "    ollama pull llava:7b"
else
    echo "  ⚠️  Ollama 미설치"
    echo "  설치: https://ollama.ai/download"
    echo "  설치 후: ollama pull llava:7b"
fi

# 4. 디렉토리 구조 확인
echo ""
echo "[4/5] 디렉토리 구조 확인..."
mkdir -p data/sample_drawings
mkdir -p data/vector_store
echo "  ✅ 디렉토리 준비 완료"

# 5. 환경 설정
echo ""
echo "[5/5] 환경 설정..."
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo "  ✅ .env 파일 생성 (.env.example 복사)"
else
    echo "  ✅ .env 파일 이미 존재"
fi

echo ""
echo "=========================================="
echo "  설치 완료!"
echo "=========================================="
echo ""
echo "실행 방법:"
echo "  1. Ollama 서버 시작:  ollama serve"
echo "  2. 모델 다운로드:     ollama pull llava:7b"
echo "  3. 앱 실행:           streamlit run app/streamlit_app.py"
echo ""

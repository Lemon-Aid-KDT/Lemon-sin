#!/bin/bash
# ============================================================
#  CAD Vision v4.0 — Docker 시작 스크립트
#
#  사용법:
#    chmod +x docker-start.sh
#    ./docker-start.sh            # 빌드 + 시작
#    ./docker-start.sh --build    # 강제 재빌드 (캐시 없이)
#    ./docker-start.sh --down     # 중지 + 제거
#    ./docker-start.sh --reset    # 데이터 볼륨 초기화 + 재시작
# ============================================================

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo -e "${GREEN}=== CAD Vision v4.0 Docker ===${NC}"
echo ""

# --- 중지 ---
if [ "$1" = "--down" ]; then
    echo -e "${YELLOW}[*] Docker Compose 중지...${NC}"
    docker compose down
    echo -e "${GREEN}[✓] 중지 완료${NC}"
    exit 0
fi

# --- 리셋 ---
if [ "$1" = "--reset" ]; then
    echo -e "${RED}[*] 데이터 볼륨 초기화...${NC}"
    docker compose down
    docker volume rm cad-vision-data 2>/dev/null || true
    echo -e "${GREEN}[✓] 볼륨 삭제 완료${NC}"
    echo ""
fi

# --- 1. 빌드 ---
echo -e "${YELLOW}[1/3] Docker 이미지 빌드...${NC}"
if [ "$1" = "--build" ]; then
    docker compose build --no-cache
else
    docker compose build
fi
echo ""

# --- 2. 정리 ---
echo -e "${YELLOW}[2/3] 기존 컨테이너 정리...${NC}"
docker compose down 2>/dev/null || true
echo ""

# --- 3. 시작 ---
echo -e "${YELLOW}[3/3] 컨테이너 시작...${NC}"
docker compose up -d
echo ""

# --- 상태 ---
echo -e "${GREEN}=== 시작 완료 ===${NC}"
echo ""
echo -e "   🌐 웹 UI:       ${CYAN}http://localhost:8501${NC}"
echo -e "   📡 REST API:    ${CYAN}http://localhost:8000/docs${NC}"
echo -e "   🤖 Ollama:      ${CYAN}http://localhost:11434${NC}"
echo ""
echo "   📋 로그:        docker compose logs -f app"
echo "   🛑 중지:        ./docker-start.sh --down"
echo "   🔄 리셋:        ./docker-start.sh --reset"
echo ""

# --- 헬스체크 ---
echo -e "${YELLOW}[*] 컨테이너 상태 확인 (10초 대기)...${NC}"
sleep 10
if docker ps --filter "name=cad-vision-app" --format '{{.Status}}' | grep -q "Up"; then
    echo -e "   ${GREEN}✓ cad-vision-app: 실행 중${NC}"
else
    echo -e "   ${RED}✗ cad-vision-app: 시작 실패${NC}"
    echo "     로그: docker compose logs app"
fi

if docker ps --filter "name=cad-vision-ollama" --format '{{.Status}}' | grep -q "Up"; then
    echo -e "   ${GREEN}✓ cad-vision-ollama: 실행 중${NC}"
else
    echo -e "   ${RED}✗ cad-vision-ollama: 시작 실패${NC}"
fi

echo ""
echo -e "${YELLOW}📌 v4.0 기능:${NC}"
echo "   • 3채널 검색: Image(CLIP) + Text(E5) + GNN(DXF 구조)"
echo "   • YOLO-cls 81카테고리 / YOLO-det 영역 탐지"
echo "   • Reranker (cross-encoder 2차 정렬)"
echo "   • REST API (Swagger: http://localhost:8000/docs)"
echo "   • Ollama 모델 선택 + 스트리밍 응답"
echo "   • SQLite 레코드 + 사용자 피드백"
echo ""

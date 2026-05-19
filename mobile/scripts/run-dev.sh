#!/usr/bin/env bash
# mobile/scripts/run-dev.sh
#
# macOS / Linux 용 — 환경변수에서 키 읽어서 dart-define 으로 자동 주입.
# 환경변수 등록 (한 번만, ~/.zshrc 또는 ~/.bashrc):
#   export KAKAO_NATIVE_APP_KEY="xxxx"
#   export GOOGLE_SERVER_CLIENT_ID="xxxx.apps.googleusercontent.com"
#   export LEMON_API_BASE_URL="http://localhost:8000"   # iOS 시뮬: localhost OK
#                                                       # Android 에뮬: 10.0.2.2
#
# 사용:
#   chmod +x mobile/scripts/run-dev.sh    (한 번만)
#   ./mobile/scripts/run-dev.sh
#
# 또는 특정 디바이스 지정:
#   ./mobile/scripts/run-dev.sh -d "iPhone 17 Pro"

set -e

KAKAO="${KAKAO_NATIVE_APP_KEY:-}"
GOOGLE="${GOOGLE_SERVER_CLIENT_ID:-}"
API_BASE="${LEMON_API_BASE_URL:-}"

if [ -z "$KAKAO" ]; then
  echo "[WARN] KAKAO_NATIVE_APP_KEY 환경변수 없음 — 카카오 로그인 비활성으로 빌드됩니다."
fi
if [ -z "$GOOGLE" ]; then
  echo "[WARN] GOOGLE_SERVER_CLIENT_ID 환경변수 없음 — 구글 로그인 비활성으로 빌드됩니다."
fi

# dart-define 인자 조립
ARGS=("run")
[ -n "$API_BASE" ] && ARGS+=("--dart-define=API_BASE_URL=$API_BASE")
[ -n "$KAKAO" ]    && ARGS+=("--dart-define=KAKAO_NATIVE_APP_KEY=$KAKAO")
[ -n "$KAKAO" ]    && ARGS+=("-Pkakao.nativeAppKey=$KAKAO")
[ -n "$GOOGLE" ]   && ARGS+=("--dart-define=GOOGLE_SERVER_CLIENT_ID=$GOOGLE")

# 사용자가 넘긴 추가 인자 (예: -d "iPhone 17 Pro")
ARGS+=("$@")

# 프로젝트 루트로 이동
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR/.."

echo "[run] flutter ${ARGS[*]}"
flutter "${ARGS[@]}"

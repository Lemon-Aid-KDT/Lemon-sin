#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

export DEVELOPER_DIR="${DEVELOPER_DIR:-/Applications/Xcode.app/Contents/Developer}"

api_base_url="${LEMON_API_BASE_URL:-http://127.0.0.1:8000/api/v1}"

build_args=(
  build
  ios
  --simulator
  --debug
  --dart-define=LEMON_API_BASE_URL="${api_base_url}"
)

if [[ -n "${LEMON_API_TOKEN:-}" ]]; then
  build_args+=(--dart-define=LEMON_API_TOKEN="${LEMON_API_TOKEN}")
fi

if [[ -n "${LEMON_DEV_GATEWAY_TOKEN:-}" ]]; then
  build_args+=(--dart-define=LEMON_DEV_GATEWAY_TOKEN="${LEMON_DEV_GATEWAY_TOKEN}")
fi

if [[ -n "${LEMON_CERTIFICATE_PINS:-}" ]]; then
  build_args+=(--dart-define=LEMON_CERTIFICATE_PINS="${LEMON_CERTIFICATE_PINS}")
fi

flutter pub get
flutter "${build_args[@]}"

cat <<'EOF'
Prepared Flutter iOS Runner for Xcode.
Open mobile/ios/Runner.xcworkspace and run the Runner scheme.
Do not open mobile/Lemon-Aid-ios/Lemon-Aid.xcodeproj for Flutter UIUX parity.
EOF

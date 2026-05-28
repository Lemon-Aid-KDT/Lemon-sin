#!/usr/bin/env bash
set -euo pipefail

export DEVELOPER_DIR="${DEVELOPER_DIR:-/Applications/Xcode.app/Contents/Developer}"

api_base_url="${LEMON_API_BASE_URL:-http://127.0.0.1:8000/api/v1}"
dart_defines=(
  "--dart-define=LEMON_API_BASE_URL=${api_base_url}"
)

if [[ -n "${LEMON_API_TOKEN:-}" ]]; then
  dart_defines+=("--dart-define=LEMON_API_TOKEN=${LEMON_API_TOKEN}")
fi

if [[ -n "${LEMON_DEV_GATEWAY_TOKEN:-}" ]]; then
  dart_defines+=("--dart-define=LEMON_DEV_GATEWAY_TOKEN=${LEMON_DEV_GATEWAY_TOKEN}")
fi

if [[ -n "${LEMON_CERTIFICATE_PINS:-}" ]]; then
  dart_defines+=("--dart-define=LEMON_CERTIFICATE_PINS=${LEMON_CERTIFICATE_PINS}")
fi

flutter pub get
flutter build ios --simulator --debug "${dart_defines[@]}"

printf '%s\n' "Prepared Flutter iOS Runner workspace for Xcode."
printf '%s\n' "Open mobile/ios/Runner.xcworkspace and run the Runner scheme."

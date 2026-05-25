#!/usr/bin/env bash
set -euo pipefail

DEVICE_ID="${1:-emulator-5554}"
API_BASE_URL="${LEMON_API_BASE_URL:-http://10.0.2.2:8000/api/v1}"

flutter run -d "${DEVICE_ID}" --flavor dev \
  --dart-define="LEMON_API_BASE_URL=${API_BASE_URL}"

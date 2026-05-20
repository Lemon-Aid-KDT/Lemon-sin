#!/usr/bin/env bash
# extract_spki_pin.sh — production TLS 인증서에서 SPKI SHA-256 핀(Base64)을 추출.
#
# Brand-New-update 감사(2026-05-18) H3 (인증서 핀닝) 대응을 위한 보조 스크립트.
# 결과 값은 다음에 사용:
#   - mobile/android/app/src/main/res/xml/network_security_config.xml
#     <pin digest="SHA-256">...</pin>
#   - iOS Info.plist / PinnedURLSessionDelegate (옵션 B 구현)
#
# 사용법:
#   ./scripts/extract_spki_pin.sh <host> [port]
#
# 예시:
#   ./scripts/extract_spki_pin.sh api.lemonhealthcare.example.com
#   ./scripts/extract_spki_pin.sh api.lemonhealthcare.example.com 443
#
# 의존성:
#   - openssl (대부분의 시스템에 기본 설치)
#   - base64 (coreutils)
#
# 출력:
#   1. Leaf certificate SPKI hash (Primary pin)
#   2. Intermediate CA certificate SPKI hash (Backup pin) — 발견 시
#
# References:
#   https://datatracker.ietf.org/doc/html/rfc7469
#   https://developer.android.com/training/articles/security-ssl#Pinning

set -euo pipefail

if [[ $# -lt 1 || $# -gt 2 ]]; then
    echo "사용법: $0 <host> [port]" >&2
    echo "예시:   $0 api.lemonhealthcare.example.com 443" >&2
    exit 64
fi

HOST="$1"
PORT="${2:-443}"

if ! command -v openssl >/dev/null 2>&1; then
    echo "오류: openssl 이 설치되어 있지 않습니다." >&2
    exit 127
fi

# TLS 핸드셰이크에서 인증서 체인 전체를 받는다.
# SNI 를 명시(-servername)해 멀티-도메인 서버에서도 올바른 leaf 인증서 획득.
CHAIN_PEM="$(
    openssl s_client \
        -servername "$HOST" \
        -connect "${HOST}:${PORT}" \
        -showcerts \
        </dev/null 2>/dev/null
)"

if [[ -z "$CHAIN_PEM" ]]; then
    echo "오류: ${HOST}:${PORT} 에서 인증서 체인을 가져오지 못했습니다." >&2
    exit 1
fi

# 체인의 모든 PEM 인증서 블록을 개별 파일로 분리한다.
TMP_DIR="$(mktemp -d -t spki-pins.XXXXXX)"
trap 'rm -rf "$TMP_DIR"' EXIT

echo "$CHAIN_PEM" | awk -v outdir="$TMP_DIR" '
    /-----BEGIN CERTIFICATE-----/ { idx++; out = sprintf("%s/cert-%02d.pem", outdir, idx); in_cert = 1 }
    in_cert { print > out }
    /-----END CERTIFICATE-----/ { in_cert = 0; close(out) }
'

CERT_COUNT=$(find "$TMP_DIR" -maxdepth 1 -name 'cert-*.pem' | wc -l | tr -d ' ')
if [[ "$CERT_COUNT" -eq 0 ]]; then
    echo "오류: 체인에서 인증서를 발견하지 못했습니다." >&2
    exit 1
fi

# SPKI 추출 함수: 단일 PEM 인증서 파일 → Base64(SHA-256(SubjectPublicKeyInfo)).
spki_hash() {
    local pem_file="$1"
    openssl x509 -in "$pem_file" -pubkey -noout \
        | openssl pkey -pubin -outform DER \
        | openssl dgst -sha256 -binary \
        | base64
}

echo "===== SPKI Pin 추출 결과 (${HOST}:${PORT}) ====="
echo "체인 인증서 수: ${CERT_COUNT}"
echo

idx=0
for pem in $(ls -1 "$TMP_DIR"/cert-*.pem | sort); do
    if [[ $idx -eq 0 ]]; then
        label="Primary (leaf)"
    else
        label="Backup #${idx} (chain)"
    fi
    if ! PIN="$(spki_hash "$pem")"; then
        echo "[$idx] $label : 추출 실패" >&2
        idx=$((idx + 1))
        continue
    fi
    echo "[$idx] $label SPKI SHA-256 (Base64):"
    echo "    $PIN"
    echo "    XML 형식: <pin digest=\"SHA-256\">${PIN}</pin>"
    echo
    idx=$((idx + 1))
done

echo "사용 예: 위 핀 중 두 개를 network_security_config.xml 의 <pin-set> 에 교체"

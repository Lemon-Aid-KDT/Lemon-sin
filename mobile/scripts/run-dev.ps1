# mobile/scripts/run-dev.ps1
#
# 개발 빌드 실행 헬퍼. 키는 로컬 환경변수에서만 읽음.
# 환경변수 설정 (한 번만):
#   [System.Environment]::SetEnvironmentVariable("KAKAO_NATIVE_APP_KEY", "xxxx", "User")
#   [System.Environment]::SetEnvironmentVariable("GOOGLE_SERVER_CLIENT_ID", "xxxx", "User")
#   (또는 일회용: $env:KAKAO_NATIVE_APP_KEY = "xxxx")
#
# 보안:
#   - 이 스크립트는 깃에 올라감 — 키 절대 박지 말 것.
#   - 환경변수에 키 저장한 PC 만 빌드 가능. PC 분실 시 키 회전.

$ErrorActionPreference = "Stop"

# 현재 세션 env 비어있으면 User scope 에서 fallback. 부모 셸이 env 등록 이전에
# 시작된 경우 (예: Claude Code Bash 에서 child PowerShell 띄울 때) 도 안전.
$kakao = $env:KAKAO_NATIVE_APP_KEY
if (-not $kakao) {
    $kakao = [System.Environment]::GetEnvironmentVariable("KAKAO_NATIVE_APP_KEY", "User")
    if ($kakao) { $env:KAKAO_NATIVE_APP_KEY = $kakao }
}
$google = $env:GOOGLE_SERVER_CLIENT_ID
if (-not $google) {
    $google = [System.Environment]::GetEnvironmentVariable("GOOGLE_SERVER_CLIENT_ID", "User")
    if ($google) { $env:GOOGLE_SERVER_CLIENT_ID = $google }
}
$apiBase = if ($env:LEMON_API_BASE_URL) { $env:LEMON_API_BASE_URL } else { "" }

if (-not $kakao) {
    Write-Host "[WARN] KAKAO_NATIVE_APP_KEY 환경변수 없음 — 카카오 로그인 비활성으로 빌드됩니다."
}
if (-not $google) {
    Write-Host "[WARN] GOOGLE_SERVER_CLIENT_ID 환경변수 없음 — 구글 로그인 비활성으로 빌드됩니다."
}

$args = @("run")

if ($apiBase)  { $args += "--dart-define=API_BASE_URL=$apiBase" }
if ($kakao)    { $args += "--dart-define=KAKAO_NATIVE_APP_KEY=$kakao" }
if ($kakao)    { $args += "-Pkakao.nativeAppKey=$kakao" }
if ($google)   { $args += "--dart-define=GOOGLE_SERVER_CLIENT_ID=$google" }

Push-Location (Join-Path $PSScriptRoot "..")
try {
    Write-Host "[run] flutter $($args -join ' ')"
    & flutter @args
} finally {
    Pop-Location
}

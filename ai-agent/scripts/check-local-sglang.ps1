param(
    [string]$BaseUrl = "http://localhost:30000/v1",
    [string]$Model = "Qwen/Qwen2.5-0.5B-Instruct",
    [string]$ApiKey = "EMPTY",
    [int]$TimeoutSec = 10,
    [switch]$RunLiveSmoke
)

$ErrorActionPreference = "Stop"

$AiAgentRoot = Split-Path -Parent $PSScriptRoot
$WorktreeRoot = Split-Path -Parent $AiAgentRoot
$BaseUrl = $BaseUrl.TrimEnd("/")
$ModelsUrl = "$BaseUrl/models"

Write-Host "Checking local SGLang server..."
Write-Host "Base URL: $BaseUrl"

try {
    $models = Invoke-RestMethod -Uri $ModelsUrl -Method Get -TimeoutSec $TimeoutSec
} catch {
    Write-Host "SGLang server is not reachable at $ModelsUrl"
    Write-Host "Start it with:"
    Write-Host "  .\ai-agent\scripts\start-local-sglang.ps1"
    throw
}

Write-Host "SGLang /v1/models responded."
if ($models.data) {
    $modelIds = $models.data | ForEach-Object { $_.id }
    Write-Host "Models: $($modelIds -join ', ')"
}

if (-not $RunLiveSmoke) {
    Write-Host ""
    Write-Host "To run the ai-agent live smoke test:"
    Write-Host "  .\ai-agent\scripts\check-local-sglang.ps1 -RunLiveSmoke"
    return
}

Write-Host ""
Write-Host "Running ai-agent SGLang live smoke test..."

$previousRunSmoke = $env:RUN_SGLANG_SMOKE
$previousBaseUrl = $env:SGLANG_BASE_URL
$previousModel = $env:SGLANG_MODEL
$previousApiKey = $env:SGLANG_API_KEY

try {
    $env:RUN_SGLANG_SMOKE = "1"
    $env:SGLANG_BASE_URL = $BaseUrl
    $env:SGLANG_MODEL = $Model
    $env:SGLANG_API_KEY = $ApiKey

    Push-Location $WorktreeRoot
    try {
        & python -m unittest ai-agent.tests.test_sglang_live_smoke
        if ($LASTEXITCODE -ne 0) {
            throw "SGLang live smoke failed with exit code $LASTEXITCODE"
        }
    } finally {
        Pop-Location
    }
} finally {
    $env:RUN_SGLANG_SMOKE = $previousRunSmoke
    $env:SGLANG_BASE_URL = $previousBaseUrl
    $env:SGLANG_MODEL = $previousModel
    $env:SGLANG_API_KEY = $previousApiKey
}

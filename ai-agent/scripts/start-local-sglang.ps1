param(
    [string]$Distro = "Ubuntu-Dev",
    [string]$Image = "lmsysorg/sglang:latest-cu129-runtime",
    [string]$Model = "Qwen/Qwen2.5-0.5B-Instruct",
    [int]$Port = 30000,
    [string]$ShmSize = "8g"
)

$ErrorActionPreference = "Stop"

Write-Host "Starting local SGLang server through WSL2/Docker..."
Write-Host "Distro: $Distro"
Write-Host "Image:  $Image"
Write-Host "Model:  $Model"
Write-Host "URL:    http://localhost:$Port/v1"
Write-Host ""
Write-Host "Keep this terminal open while using the local LLM API."
Write-Host "Stop the server with Ctrl+C."
Write-Host ""

$serverCommand = "python3 -m pip install --no-cache-dir distro && python3 -m sglang.launch_server --model-path $Model --host 0.0.0.0 --port $Port"
$dockerCommand = "docker run --rm -it --gpus=all --shm-size $ShmSize -p ${Port}:${Port} -v `$HOME/.cache/huggingface:/root/.cache/huggingface $Image bash -lc '$serverCommand'"

& wsl.exe -d $Distro -- bash -lc $dockerCommand

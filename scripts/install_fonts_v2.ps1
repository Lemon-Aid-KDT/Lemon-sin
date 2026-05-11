# scripts/install_fonts_v2.ps1 - Lemon Aid font installer (Gmarket + Jakarta retry)
#
# Usage:
#   powershell -ExecutionPolicy Bypass -File scripts/install_fonts_v2.ps1
#
# v2 differences:
#   - Multiple mirror URLs per font (fallback chain)
#   - File validation (font binary signature check)
#   - HTML page detection (< 5KB or starts with '<')
#   - Auto un-comment pubspec.yaml font blocks on success
#   - Auto runs `flutter pub get` at the end

$ErrorActionPreference = 'Continue'
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

$RepoRoot = Split-Path -Parent $PSScriptRoot
$FontsDir = Join-Path $RepoRoot 'mobile\assets\fonts'
$Pubspec  = Join-Path $RepoRoot 'mobile\pubspec.yaml'

Write-Host ""
Write-Host "=================================================="
Write-Host " Lemon Aid Font Installer v2 (retry + validate)"
Write-Host "=================================================="
Write-Host ""

New-Item -ItemType Directory -Force -Path $FontsDir | Out-Null

# Validate downloaded file is a real font binary
function Test-FontFile {
    param([string]$Path)
    if (-not (Test-Path $Path)) { return $false }
    $size = (Get-Item $Path).Length
    if ($size -lt 10000) {
        Write-Host "    INVALID: only $size bytes (likely HTML error page)" -ForegroundColor Red
        return $false
    }
    # Check magic bytes — TTF: 0x00 0x01 0x00 0x00 / OTF: 'OTTO' / WOFF: 'wOFF' / collection: 'true' or 'ttcf'
    $bytes = [System.IO.File]::ReadAllBytes($Path) | Select-Object -First 4
    $magic = [System.Text.Encoding]::ASCII.GetString($bytes[0..3])
    $isTTF  = ($bytes[0] -eq 0 -and $bytes[1] -eq 1 -and $bytes[2] -eq 0 -and $bytes[3] -eq 0)
    $isOTF  = ($magic -eq 'OTTO')
    $isWOFF = ($magic -eq 'wOFF')
    $isTTC  = ($magic -eq 'ttcf' -or $magic -eq 'true')
    if (-not ($isTTF -or $isOTF -or $isWOFF -or $isTTC)) {
        Write-Host "    INVALID: not a font binary (magic: $magic)" -ForegroundColor Red
        return $false
    }
    return $true
}

# Try downloading from multiple URLs until one succeeds + validates
function Try-Download {
    param([string[]]$Urls, [string]$DestPath, [string]$Display)
    foreach ($url in $Urls) {
        Write-Host "  Try: $url"
        try {
            Invoke-WebRequest -Uri $url -OutFile $DestPath -UseBasicParsing -ErrorAction Stop
            if (Test-FontFile -Path $DestPath) {
                $sizeKB = [math]::Round((Get-Item $DestPath).Length / 1KB, 1)
                Write-Host "  OK [$Display] -> $sizeKB KB" -ForegroundColor Green
                return $true
            } else {
                Remove-Item -Force $DestPath -ErrorAction SilentlyContinue
            }
        } catch {
            Write-Host "    FAIL: $($_.Exception.Message)" -ForegroundColor DarkGray
        }
    }
    Write-Host "  All mirrors failed for [$Display]" -ForegroundColor Red
    return $false
}

# --- Gmarket Sans (3 weights) ---
Write-Host "[1/2] Gmarket Sans"
Write-Host "------------------------------------"

$gmarketResult = @{}

$gmarketLightUrls = @(
    'https://github.com/Joungkyun/font-archive/raw/main/GmarketSans/GmarketSansTTFLight.ttf'
    'https://cdn.jsdelivr.net/gh/Joungkyun/font-archive@main/GmarketSans/GmarketSansTTFLight.ttf'
    'https://raw.githubusercontent.com/projectnoonnu/noonfonts_2105_2/main/GmarketSansTTFLight.ttf'
)
$gmarketMediumUrls = @(
    'https://github.com/Joungkyun/font-archive/raw/main/GmarketSans/GmarketSansTTFMedium.ttf'
    'https://cdn.jsdelivr.net/gh/Joungkyun/font-archive@main/GmarketSans/GmarketSansTTFMedium.ttf'
    'https://raw.githubusercontent.com/projectnoonnu/noonfonts_2105_2/main/GmarketSansTTFMedium.ttf'
)
$gmarketBoldUrls = @(
    'https://github.com/Joungkyun/font-archive/raw/main/GmarketSans/GmarketSansTTFBold.ttf'
    'https://cdn.jsdelivr.net/gh/Joungkyun/font-archive@main/GmarketSans/GmarketSansTTFBold.ttf'
    'https://raw.githubusercontent.com/projectnoonnu/noonfonts_2105_2/main/GmarketSansTTFBold.ttf'
)

$gmarketResult.Light  = Try-Download -Urls $gmarketLightUrls  -DestPath (Join-Path $FontsDir 'GmarketSansLight.ttf')  -Display 'Light'
$gmarketResult.Medium = Try-Download -Urls $gmarketMediumUrls -DestPath (Join-Path $FontsDir 'GmarketSansMedium.ttf') -Display 'Medium'
$gmarketResult.Bold   = Try-Download -Urls $gmarketBoldUrls   -DestPath (Join-Path $FontsDir 'GmarketSansBold.ttf')   -Display 'Bold'

$gmarketAllOK = ($gmarketResult.Light -and $gmarketResult.Medium -and $gmarketResult.Bold)

# --- Plus Jakarta Sans ---
Write-Host ""
Write-Host "[2/2] Plus Jakarta Sans"
Write-Host "------------------------------------"

$jakartaUrls = @(
    'https://github.com/google/fonts/raw/main/ofl/plusjakartasans/PlusJakartaSans%5Bwght%5D.ttf'
    'https://cdn.jsdelivr.net/gh/google/fonts@main/ofl/plusjakartasans/PlusJakartaSans%5Bwght%5D.ttf'
)
$jakartaOK = Try-Download -Urls $jakartaUrls -DestPath (Join-Path $FontsDir 'PlusJakartaSans-VariableFont_wght.ttf') -Display 'PJS Variable'

# OFL license
if ($jakartaOK) {
    try {
        Invoke-WebRequest -Uri 'https://github.com/google/fonts/raw/main/ofl/plusjakartasans/OFL.txt' `
            -OutFile (Join-Path $FontsDir 'LICENSE-PlusJakartaSans.txt') -UseBasicParsing -ErrorAction Stop
        Write-Host "  LICENSE-PlusJakartaSans.txt OK"
    } catch {
        Write-Host "  LICENSE fetch failed (non-critical)" -ForegroundColor DarkGray
    }
}

# --- pubspec.yaml uncomment based on results ---
Write-Host ""
Write-Host "[pubspec] updating fonts section"
Write-Host "------------------------------------"

$pubspecContent = Get-Content -Path $Pubspec -Raw

if ($gmarketAllOK) {
    $pubspecContent = $pubspecContent -replace '(?m)^    # - family: GmarketSans\r?\n    #   fonts:\r?\n    #     - asset: assets/fonts/GmarketSansLight\.ttf\r?\n    #       weight: 300\r?\n    #     - asset: assets/fonts/GmarketSansMedium\.ttf\r?\n    #       weight: 500\r?\n    #     - asset: assets/fonts/GmarketSansBold\.ttf\r?\n    #       weight: 700', @"
    - family: GmarketSans
      fonts:
        - asset: assets/fonts/GmarketSansLight.ttf
          weight: 300
        - asset: assets/fonts/GmarketSansMedium.ttf
          weight: 500
        - asset: assets/fonts/GmarketSansBold.ttf
          weight: 700
"@
    Write-Host "  GmarketSans block uncommented" -ForegroundColor Green
} else {
    Write-Host "  GmarketSans block kept commented (incomplete download)" -ForegroundColor Yellow
}

if ($jakartaOK) {
    $pubspecContent = $pubspecContent -replace '(?m)^    # - family: PlusJakartaSans\r?\n    #   fonts:\r?\n    #     - asset: assets/fonts/PlusJakartaSans-VariableFont_wght\.ttf', @"
    - family: PlusJakartaSans
      fonts:
        - asset: assets/fonts/PlusJakartaSans-VariableFont_wght.ttf
"@
    Write-Host "  PlusJakartaSans block uncommented" -ForegroundColor Green
} else {
    Write-Host "  PlusJakartaSans block kept commented" -ForegroundColor Yellow
}

Set-Content -Path $Pubspec -Value $pubspecContent -NoNewline

# --- flutter pub get ---
Write-Host ""
Write-Host "[flutter] pub get"
Write-Host "------------------------------------"

Push-Location (Join-Path $RepoRoot 'mobile')
try {
    flutter pub get
} catch {
    Write-Host "flutter pub get failed: $_" -ForegroundColor Red
}
Pop-Location

# --- Summary ---
Write-Host ""
Write-Host "=================================================="
Write-Host " Summary"
Write-Host "=================================================="
Get-ChildItem $FontsDir | Sort-Object Name | ForEach-Object {
    $sizeKB = [math]::Round($_.Length / 1KB, 1)
    Write-Host ("  {0,-50} {1,10} KB" -f $_.Name, $sizeKB)
}

Write-Host ""
if ($gmarketAllOK -and $jakartaOK) {
    Write-Host "All fonts installed. Run: cd mobile && flutter run" -ForegroundColor Green
} else {
    Write-Host "Some fonts missing. Manual fallback:" -ForegroundColor Yellow
    if (-not $gmarketAllOK) {
        Write-Host "  Gmarket Sans: https://corp.gmarket.com/fonts"
        Write-Host "    Place GmarketSans{Light,Medium,Bold}.ttf in $FontsDir"
        Write-Host "    Then uncomment GmarketSans block in mobile/pubspec.yaml"
    }
    if (-not $jakartaOK) {
        Write-Host "  Plus Jakarta Sans: https://fonts.google.com/specimen/Plus+Jakarta+Sans"
        Write-Host "    Place PlusJakartaSans-VariableFont_wght.ttf in $FontsDir"
    }
}
Write-Host ""

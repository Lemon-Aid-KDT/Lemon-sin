# scripts/install_fonts.ps1 - Lemon Aid font auto-installer (Windows)
#
# Usage:
#   powershell -ExecutionPolicy Bypass -File scripts/install_fonts.ps1
#
# Targets (diary section 4.5a):
#   1. Pretendard         - orioncactus GitHub Release (OFL)
#   2. Gmarket Sans       - GitHub mirror
#   3. Plus Jakarta Sans  - Google Fonts (OFL)
#
# Result:
#   mobile/assets/fonts/ contains font files + LICENSE notes
#   mobile/assets/fonts/LICENSES.md lists sources

$ErrorActionPreference = 'Stop'

# Force TLS 1.2 (some hosts reject older)
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

$RepoRoot = Split-Path -Parent $PSScriptRoot
$FontsDir = Join-Path $RepoRoot 'mobile\assets\fonts'
$TempDir  = Join-Path $env:TEMP 'lemon_aid_fonts'

Write-Host ""
Write-Host "=================================================="
Write-Host " Lemon Aid Font Installer"
Write-Host "=================================================="
Write-Host ""
Write-Host "Target folder: $FontsDir"
Write-Host ""

New-Item -ItemType Directory -Force -Path $FontsDir | Out-Null
New-Item -ItemType Directory -Force -Path $TempDir  | Out-Null

function Get-AndExtract {
    param([string]$Url, [string]$ZipName, [string]$Display)

    $zipPath = Join-Path $TempDir $ZipName
    $extractPath = Join-Path $TempDir ([System.IO.Path]::GetFileNameWithoutExtension($ZipName))

    Write-Host "[$Display] downloading..."
    Write-Host "  URL: $Url"

    try {
        Invoke-WebRequest -Uri $Url -OutFile $zipPath -UseBasicParsing
    } catch {
        Write-Host "  FAIL: $_"
        return $null
    }

    $sizeMB = [math]::Round((Get-Item $zipPath).Length / 1MB, 2)
    Write-Host "  OK ($sizeMB MB)"

    if (Test-Path $extractPath) { Remove-Item -Recurse -Force $extractPath }
    try {
        Expand-Archive -Path $zipPath -DestinationPath $extractPath -Force
        Write-Host "  Extracted"
    } catch {
        Write-Host "  Extract FAIL: $_"
        return $null
    }

    return $extractPath
}

function Copy-Font {
    param([string]$From, [string]$ToName, [string]$Display)
    if (-not (Test-Path $From)) {
        Write-Host "  Missing source: $From"
        return $false
    }
    $dest = Join-Path $FontsDir $ToName
    Copy-Item -Path $From -Destination $dest -Force
    Write-Host "  Saved -> assets/fonts/$ToName"
    return $true
}

# --- 1. Pretendard ---
Write-Host ""
Write-Host "[1/3] Pretendard"
Write-Host "------------------------------------"

$pretendardUrl = 'https://github.com/orioncactus/pretendard/releases/latest/download/Pretendard-1.3.9.zip'
$pretendardExtract = Get-AndExtract -Url $pretendardUrl -ZipName 'pretendard.zip' -Display 'Pretendard'

if ($pretendardExtract) {
    $files = Get-ChildItem -Recurse -Path $pretendardExtract -Filter 'Pretendard-*.otf' |
        Where-Object { $_.Name -match '^Pretendard-(Regular|Medium|SemiBold|Bold|ExtraBold)\.otf$' }

    foreach ($f in $files) {
        Copy-Font -From $f.FullName -ToName $f.Name -Display $f.Name
    }

    $license = Get-ChildItem -Recurse -Path $pretendardExtract -Filter 'LICENSE' | Select-Object -First 1
    if ($license) {
        Copy-Item -Path $license.FullName -Destination (Join-Path $FontsDir 'LICENSE-Pretendard.txt') -Force
        Write-Host "  LICENSE-Pretendard.txt copied"
    }
}

# --- 2. Gmarket Sans ---
Write-Host ""
Write-Host "[2/3] Gmarket Sans"
Write-Host "------------------------------------"
Write-Host "Note: official site is dynamic, using GitHub mirror"

$gmarketCandidates = @(
    @{ Url='https://github.com/Joungkyun/font-archive/raw/main/GmarketSans/GmarketSansTTFBold.ttf';   FileName='GmarketSansBold.ttf';   Display='Bold' },
    @{ Url='https://github.com/Joungkyun/font-archive/raw/main/GmarketSans/GmarketSansTTFMedium.ttf'; FileName='GmarketSansMedium.ttf'; Display='Medium' },
    @{ Url='https://github.com/Joungkyun/font-archive/raw/main/GmarketSans/GmarketSansTTFLight.ttf';  FileName='GmarketSansLight.ttf';  Display='Light' }
)

$gmarketOK = $true
foreach ($g in $gmarketCandidates) {
    $dest = Join-Path $FontsDir $g.FileName
    Write-Host "Gmarket Sans $($g.Display) downloading..."
    try {
        Invoke-WebRequest -Uri $g.Url -OutFile $dest -UseBasicParsing
        $sizeKB = [math]::Round((Get-Item $dest).Length / 1KB, 1)
        Write-Host "  Saved -> assets/fonts/$($g.FileName) ($sizeKB KB)"
    } catch {
        Write-Host "  FAIL: $_"
        $gmarketOK = $false
    }
}

if (-not $gmarketOK) {
    Write-Host ""
    Write-Host "  WARN: Gmarket Sans auto-download failed."
    Write-Host "        Manual: https://corp.gmarket.com/fonts"
    Write-Host "        Place GmarketSansBold/Medium/Light.ttf in $FontsDir"
}

# --- 3. Plus Jakarta Sans ---
Write-Host ""
Write-Host "[3/3] Plus Jakarta Sans"
Write-Host "------------------------------------"

$jakartaUrl = 'https://fonts.google.com/download?family=Plus+Jakarta+Sans'
$jakartaExtract = Get-AndExtract -Url $jakartaUrl -ZipName 'jakarta.zip' -Display 'Plus Jakarta Sans'

if ($jakartaExtract) {
    $variable = Get-ChildItem -Recurse -Path $jakartaExtract -Filter '*VariableFont*.ttf' | Select-Object -First 1
    if ($variable) {
        Copy-Font -From $variable.FullName -ToName 'PlusJakartaSans-VariableFont_wght.ttf' -Display 'PJS Variable'
    } else {
        $bold    = Get-ChildItem -Recurse -Path $jakartaExtract -Filter '*Bold.ttf'    | Select-Object -First 1
        $regular = Get-ChildItem -Recurse -Path $jakartaExtract -Filter '*Regular.ttf' | Select-Object -First 1
        if ($bold)    { Copy-Font -From $bold.FullName    -ToName 'PlusJakartaSans-Bold.ttf'    -Display 'PJS Bold' }
        if ($regular) { Copy-Font -From $regular.FullName -ToName 'PlusJakartaSans-Regular.ttf' -Display 'PJS Regular' }
    }

    $license = Get-ChildItem -Recurse -Path $jakartaExtract -Filter 'OFL.txt' | Select-Object -First 1
    if ($license) {
        Copy-Item -Path $license.FullName -Destination (Join-Path $FontsDir 'LICENSE-PlusJakartaSans.txt') -Force
        Write-Host "  LICENSE-PlusJakartaSans.txt copied"
    }
}

# --- LICENSES.md ---
$licensesMd = @"
# Lemon Aid Fonts - Licenses

Fonts in this folder follow the licenses below.
The app's Settings > Open Source Licenses must show the same notice.

## Pretendard
- Author: orioncactus (Sungsoo Kim)
- License: SIL Open Font License 1.1
- Source: https://github.com/orioncactus/pretendard
- File: LICENSE-Pretendard.txt
- Weights used: 400 / 500 / 600 / 700 / 800

## Gmarket Sans
- Author: G-market (eBay Korea)
- License: G-market Font License - free for commercial use (no resale or modification)
- Source: https://corp.gmarket.com/fonts
- Weights used: 300 (Light) / 500 (Medium) / 700 (Bold)
- Note: font modification or resale prohibited; in-app use allowed

## Plus Jakarta Sans
- Author: Tokotype
- License: SIL Open Font License 1.1
- Source: https://fonts.google.com/specimen/Plus+Jakarta+Sans
- File: LICENSE-PlusJakartaSans.txt
- Usage: Variable font (all weights)

---
Installer: scripts/install_fonts.ps1
"@

$licensesPath = Join-Path $FontsDir 'LICENSES.md'
$licensesMd | Out-File -FilePath $licensesPath -Encoding utf8
Write-Host ""
Write-Host "LICENSES.md saved"

# --- cleanup ---
if (Test-Path $TempDir) {
    Remove-Item -Recurse -Force $TempDir -ErrorAction SilentlyContinue
}

# --- results ---
Write-Host ""
Write-Host "=================================================="
Write-Host " Installed files in assets/fonts/"
Write-Host "=================================================="
Get-ChildItem $FontsDir | Sort-Object Name | ForEach-Object {
    $sizeKB = [math]::Round($_.Length / 1KB, 1)
    Write-Host ("  {0,-50} {1,8} KB" -f $_.Name, $sizeKB)
}

Write-Host ""
Write-Host "=================================================="
Write-Host " Next steps"
Write-Host "=================================================="
Write-Host ""
Write-Host "  cd mobile"
Write-Host "  flutter pub get"
Write-Host "  flutter run"
Write-Host ""
Write-Host "Or if the emulator is already running, press R (Hot Restart)."
Write-Host ""

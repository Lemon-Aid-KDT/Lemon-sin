# scripts/install_app_icon.ps1 - Lemon Aid app icon installer
#
# Usage:
#   powershell -ExecutionPolicy Bypass -File scripts/install_app_icon.ps1
#
# Steps:
#   1. Convert assets/app_icon/app_icon.svg to 1024x1024 PNG
#   2. Add flutter_launcher_icons to pubspec.yaml (dev_dependencies)
#   3. Add flutter_icons config
#   4. Run flutter pub get + dart run flutter_launcher_icons
#
# Requirements:
#   - ImageMagick or rsvg-convert or Inkscape (one of them) for SVG -> PNG
#   - Fallback: use Python's cairosvg if available

$ErrorActionPreference = 'Stop'

$RepoRoot = Split-Path -Parent $PSScriptRoot
$MobileDir = Join-Path $RepoRoot 'mobile'
$AssetDir = Join-Path $MobileDir 'assets\app_icon'
$SvgPath = Join-Path $AssetDir 'app_icon.svg'
$PngPath = Join-Path $AssetDir 'app_icon.png'

Write-Host ""
Write-Host "=================================================="
Write-Host " Lemon Aid App Icon Installer"
Write-Host "=================================================="
Write-Host ""

if (-not (Test-Path $SvgPath)) {
    Write-Host "FAIL: SVG not found at $SvgPath"
    exit 1
}

# --- Try SVG -> PNG conversion ---
$converted = $false

# Try ImageMagick
$magick = Get-Command magick -ErrorAction SilentlyContinue
if ($magick) {
    Write-Host "Using ImageMagick to convert SVG..."
    & magick -background none -density 300 $SvgPath -resize 1024x1024 $PngPath
    if (Test-Path $PngPath) { $converted = $true; Write-Host "  OK -> $PngPath" }
}

# Try Inkscape
if (-not $converted) {
    $inkscape = Get-Command inkscape -ErrorAction SilentlyContinue
    if ($inkscape) {
        Write-Host "Using Inkscape to convert SVG..."
        & inkscape --export-type=png --export-filename=$PngPath --export-width=1024 --export-height=1024 $SvgPath
        if (Test-Path $PngPath) { $converted = $true; Write-Host "  OK -> $PngPath" }
    }
}

# Try Python cairosvg
if (-not $converted) {
    $python = Get-Command python -ErrorAction SilentlyContinue
    if ($python) {
        Write-Host "Trying Python cairosvg..."
        $pyScript = @"
try:
    import cairosvg
    cairosvg.svg2png(url=r'$SvgPath', write_to=r'$PngPath', output_width=1024, output_height=1024)
    print('OK')
except ImportError:
    print('cairosvg not installed. Run: pip install cairosvg --break-system-packages')
    raise SystemExit(1)
"@
        $pyScript | & python -
        if (Test-Path $PngPath) { $converted = $true; Write-Host "  OK -> $PngPath" }
    }
}

if (-not $converted) {
    Write-Host ""
    Write-Host "ERROR: No SVG converter found." -ForegroundColor Red
    Write-Host "Install ONE of:"
    Write-Host "  - ImageMagick: https://imagemagick.org/script/download.php#windows"
    Write-Host "  - Inkscape: https://inkscape.org/release/"
    Write-Host "  - Python + cairosvg: pip install cairosvg --break-system-packages"
    Write-Host ""
    Write-Host "Or manually export $SvgPath as 1024x1024 PNG to $PngPath"
    exit 1
}

# --- Update pubspec.yaml ---
$pubspec = Join-Path $MobileDir 'pubspec.yaml'
$content = Get-Content -Path $pubspec -Raw

if ($content -notmatch 'flutter_launcher_icons:') {
    Write-Host ""
    Write-Host "Adding flutter_launcher_icons to dev_dependencies..."
    $content = $content -replace '(dev_dependencies:\s*\r?\n  flutter_test:\s*\r?\n    sdk: flutter)', "`$1`r`n  flutter_launcher_icons: ^0.13.1"
}

if ($content -notmatch 'flutter_icons:') {
    Write-Host "Adding flutter_icons config..."
    $iconConfig = @'

flutter_icons:
  android: true
  ios: true
  image_path: "assets/app_icon/app_icon.png"
  adaptive_icon_background: "#FFFFFF"
  adaptive_icon_foreground: "assets/app_icon/app_icon.png"
  min_sdk_android: 26
  remove_alpha_ios: true
'@
    $content = $content.TrimEnd() + "`r`n" + $iconConfig + "`r`n"
}

Set-Content -Path $pubspec -Value $content -NoNewline
Write-Host "  pubspec.yaml updated"

# --- flutter pub get ---
Write-Host ""
Write-Host "Running flutter pub get..."
Push-Location $MobileDir
try {
    flutter pub get
    Write-Host ""
    Write-Host "Running flutter_launcher_icons..."
    dart run flutter_launcher_icons
} catch {
    Write-Host "ERROR: $_" -ForegroundColor Red
}
Pop-Location

Write-Host ""
Write-Host "=================================================="
Write-Host " Done. Restart 'flutter run' to see new app icon."
Write-Host "=================================================="
Write-Host ""

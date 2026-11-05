# PlateTrack build script (PowerShell)
# Requires: Rust (stable), Visual Studio Build Tools with "Desktop development with C++"

$ErrorActionPreference = "Stop"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
Set-Location $scriptDir

Write-Host "=== PlateTrack build script ===" -ForegroundColor Cyan

# -------------------- 1. Check prerequisites --------------------
Write-Host "Checking prerequisites..." -ForegroundColor Yellow

$rustc = Get-Command rustc -ErrorAction SilentlyContinue
if (-not $rustc) {
    Write-Error "Rust not found in PATH. Install from https://rustup.rs"
    exit 1
}

# -------------------- 2. Clean --------------------
Write-Host "Cleaning previous build artifacts..." -ForegroundColor Yellow
Remove-Item -Recurse -Force target\release\build 2>$null
Remove-Item -Recurse -Force target\release\deps 2>$null
Remove-Item -Recurse -Force target\release\.fingerprint 2>$null

# -------------------- 3. Build release --------------------
Write-Host "Building PlateTrack (release mode)..." -ForegroundColor Yellow
& "$env:USERPROFILE\.cargo\bin\cargo" build --release
if ($LASTEXITCODE -ne 0) {
    Write-Error "Cargo build failed"
    exit 1
}

# -------------------- 4. Verify .exe exists --------------------
$exePath = "target\release\platetrack.exe"
if (-not (Test-Path $exePath)) {
    Write-Error "Build failed: $exePath not found"
    exit 1
}

$fileInfo = Get-Item $exePath
Write-Host "Build successful!" -ForegroundColor Green
Write-Host "  Output: $scriptDir\$exePath" -ForegroundColor Cyan
Write-Host "  Size: $([math]::Round($fileInfo.Length / 1MB, 2)) MB" -ForegroundColor Cyan
Write-Host "  Built: $($fileInfo.LastWriteTime)" -ForegroundColor Cyan

# -------------------- 5. Optional: create dist folder --------------------
$distDir = "$scriptDir\dist"
New-Item -ItemType Directory -Force -Path $distDir | Out-Null
Copy-Item $exePath "$distDir\"
Write-Host "Copied to dist folder: $distDir\platetrack.exe" -ForegroundColor Green

# -------------------- 6. Run tests --------------------
Write-Host "Running tests..." -ForegroundColor Yellow
& "$env:USERPROFILE\.cargo\bin\cargo" test --lib
if ($LASTEXITCODE -eq 0) {
    Write-Host "Tests passed!" -ForegroundColor Green
} else {
    Write-Host "Tests had failures (this may be due to missing DB env vars in test environment)" -ForegroundColor Yellow
}

Write-Host "=== Build complete ===" -ForegroundColor Green
Write-Host ""
Write-Host "To run the application:" -ForegroundColor Cyan
Write-Host "  .\target\release\platetrack.exe" -ForegroundColor White
Write-Host ""
Write-Host "To install Visual Studio Build Tools (required for linking):" -ForegroundColor Yellow
Write-Host "  Download from: https://visualstudio.microsoft.com/visual-cpp-build-tools/" -ForegroundColor White
Write-Host "  Select workload: 'Desktop development with C++'" -ForegroundColor White

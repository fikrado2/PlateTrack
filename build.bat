@echo off
REM PlateTrack build batch file – delegates to PowerShell script
REM Requires: PowerShell, PyInstaller, Inno Setup (ISCC in PATH)

setlocal
set SCRIPT_DIR=%~dp0
pushd "%SCRIPT_DIR%"

echo.
echo ===== PlateTrack build batch started =====
echo.

if NOT exist "%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe" (
    echo ERROR: PowerShell not found. Please install Windows PowerShell.
    goto :eof
)

REM Set execution policy to allow the script to run (only for this process)
powershell -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT_DIR%\build.ps1"
if errorlevel 1 (
    echo.
    echo Build failed. See messages above.
    goto :eof
)

echo.
echo ===== Build completed successfully =====
echo.

popd
endlocal
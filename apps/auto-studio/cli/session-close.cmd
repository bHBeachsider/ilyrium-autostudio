@echo off
REM Ilyrium studio session CLOSE -- closes SSH tunnels and STOPS the box (ends billing).
REM Double-clickable; also the target of the "Ilyrium Close" desktop shortcut.
cd /d "%~dp0"
title Ilyrium Studio - Closing
set "PS=powershell"
where pwsh >nul 2>&1 && set "PS=pwsh"
%PS% -ExecutionPolicy Bypass -NoProfile -Command "& { .\box.ps1 tunnel-down; .\box.ps1 stop; Write-Host ''; Write-Host 'Session closed. Billing ends once the box reaches stopped.' -ForegroundColor Green }"
echo.
echo Closing in 6 seconds...
timeout /t 6 >nul

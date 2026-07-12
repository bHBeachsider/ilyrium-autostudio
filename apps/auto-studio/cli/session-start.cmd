@echo off
REM Ilyrium studio session START -- boots the box, starts ComfyUI, opens the REPL.
REM Double-clickable; also the target of the "Ilyrium Start" desktop shortcut.
cd /d "%~dp0"
title Ilyrium Studio
REM Prefer PowerShell 7 (pwsh); fall back to Windows PowerShell 5.1.
where pwsh >nul 2>&1 && (
    pwsh -NoExit -ExecutionPolicy Bypass -File "%~dp0ilyrium.ps1"
) || (
    powershell -NoExit -ExecutionPolicy Bypass -File "%~dp0ilyrium.ps1"
)

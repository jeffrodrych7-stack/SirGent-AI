@echo off
:: =====================================================================
::  SIRGENT-AI — Windows one-click setup (self-elevates to Administrator)
::  Run: double-click setup.bat  →  UAC prompt  →  done in a few minutes
:: =====================================================================
setlocal EnableDelayedExpansion
title SIRGENT-AI Setup

:: ---------- self-elevate ----------
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo Requesting Administrator rights ^(UAC^)...
    powershell -NoProfile -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
    exit /b
)

echo.
echo  ==========================================
echo   SIRGENT-AI // MASTER CONTROL SETUP
echo   Preparing powers for Sir Rodrych...
echo  ==========================================
echo.

:: ---------- locate repo root (parent of desktop\) ----------
set "ROOT=%~dp0.."
cd /d "%ROOT%"

:: ---------- Python check ----------
set "PY=python"
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [1/5] Python not found - installing via winget...
    winget install -e --id Python.Python.3.12 --accept-source-agreements --accept-package-agreements
    if !errorlevel! neq 0 (
        echo Could not install Python automatically.
        echo Install Python 3.10+ from python.org, then re-run this file.
        pause
        exit /b 1
    )
    :: refresh PATH for this session
    set "PY=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
)
echo [1/5] Python ready.

:: ---------- virtualenv + deps ----------
echo [2/5] Creating workspace...
if not exist ".venv" (
    "%PY%" -m venv .venv
)
call ".venv\Scripts\activate.bat"

echo [3/5] Installing core powers ^(this can take a few minutes^)...
python -m pip install --upgrade pip -q
pip install -r desktop\requirements.txt -q
if !errorlevel! neq 0 (
    echo pip reported errors - continuing with what installed.
)

echo [4/5] Installing browser engine for WhatsApp ^(one-time^)...
python -m playwright install chromium >nul 2>&1

:: ---------- .env ----------
if not exist ".env" (
    copy "desktop\env.example" ".env" >nul
    echo       Created .env - paste your free GOOGLE_API_KEY into it.
)

:: ---------- desktop shortcut ----------
echo [5/5] Creating desktop shortcut...
set "BAT=%~dp0start_sirgent.bat"
powershell -NoProfile -Command ^
  "$ws = New-Object -ComObject WScript.Shell;" ^
  "$s = $ws.CreateShortcut([Environment]::GetFolderPath('Desktop') + '\SIRGENT-AI.lnk');" ^
  "$s.TargetPath = '%BAT%';" ^
  "$s.WorkingDirectory = '%~dp0';" ^
  "$s.IconLocation = '%SystemRoot%\System32\SHELL32.dll,44';" ^
  "$s.Save()"

echo.
echo  ==========================================
echo   SETUP COMPLETE
echo   Double-click "SIRGENT-AI" on your Desktop.
echo   Say  "Hey Sergent"  or  "Hey SirGent".
echo   Open the console at  http://localhost:5173
echo  ==========================================
echo.
pause

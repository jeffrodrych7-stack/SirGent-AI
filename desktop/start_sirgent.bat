@echo off
title SIRGENT-AI // MASTER CONTROL
cd /d "%~dp0.."

if not exist ".venv\Scripts\python.exe" (
    echo SirGent is not installed yet. Run setup.bat first.
    pause
    exit /b 1
)

call ".venv\Scripts\activate.bat"
echo.
echo   SIRGENT-AI waking up...
echo   - Voice: say "Hey Sergent" or "Hey SirGent"
echo   - Console: open http://localhost:5173 in your browser
echo.
python -m sirgent
pause

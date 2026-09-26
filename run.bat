@echo off
:: ============================================================
:: Embedded Debugging Copilot — launcher
:: ============================================================
cd /d "%~dp0"
python main.py
if %errorlevel% neq 0 (
    echo.
    echo  ERROR: Application exited with error code %errorlevel%.
    echo  Run install.bat if you have not already done so.
    pause
)

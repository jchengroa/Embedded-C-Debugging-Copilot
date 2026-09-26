@echo off
:: ============================================================
:: Embedded Debugging Copilot — Windows installer
:: ============================================================
echo.
echo  Embedded Debugging Copilot - Installation
echo  ==========================================

:: Check Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo  ERROR: Python is not installed or not on PATH.
    echo  Download from https://www.python.org/downloads/
    echo  Make sure to check "Add Python to PATH" during install.
    pause
    exit /b 1
)

python --version
echo.

:: Check tkinter (ships with Python on Windows - should always work)
python -c "import tkinter" >nul 2>&1
if %errorlevel% neq 0 (
    echo  ERROR: tkinter is not available.
    echo  Reinstall Python from python.org with the tcl/tk option enabled.
    pause
    exit /b 1
)
echo  [OK] tkinter available

:: Install Python dependencies
echo.
echo  Installing dependencies...
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo  WARNING: Some dependencies failed to install.
    echo  The application can still run without the AI backend.
)

echo.
echo  ============================================================
echo  Installation complete.
echo.
echo  To configure AI (optional):
echo    Edit config\settings.json and add your OpenAI API key.
echo    OR set environment variable: OPENAI_API_KEY=your-key-here
echo.
echo  To launch:
echo    run.bat
echo  ============================================================
echo.
pause

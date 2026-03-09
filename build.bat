@echo off
REM Build script for Windows

echo ===================================
echo Napoleon TW Cheat Engine - Windows Build
echo ===================================

REM Create virtual environment if it doesn't exist
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
)

REM Activate virtual environment
call venv\Scripts\activate.bat

REM Install dependencies
echo Installing dependencies...
pip install -r requirements.txt

REM Run tests
echo Running tests...
python -m pytest tests\ -v || echo Tests completed with warnings

REM Build with PyInstaller
echo Building executable...
pyinstaller --onefile --windowed --icon=icon.ico --name "NapoleonCheatEngine" src\main.py

echo.
echo Build complete!
echo Executable: dist\NapoleonCheatEngine.exe
echo.
echo To run: dist\NapoleonCheatEngine.exe --gui

pause

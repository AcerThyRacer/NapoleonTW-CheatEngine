@echo off
REM ============================================================================
REM Napoleon Total War Trainer - Hotkey Launcher (Windows)
REM Runs in background and activates cheats with F-keys while game is running
REM ============================================================================

echo ============================================================================
echo Napoleon Total War Trainer - Hotkey Mode
echo ============================================================================
echo.
echo [INFO] Starting trainer with hotkey support...
echo.
echo The trainer will run in the background and listen for hotkeys.
echo.
echo HOTKEYS (Press these WHILE in the game):
echo ============================================================================
echo.
echo CAMPAIGN MODE (Shift + F-key):
echo   Shift+F1  - God Mode
echo   Shift+F2  - Infinite Gold
echo   Shift+F3  - Unlimited Movement
echo   Shift+F4  - Instant Construction
echo   Shift+F5  - Fast Research
echo.
echo BATTLE MODE (Ctrl + F-key):
echo   Ctrl+F1   - God Mode
echo   Ctrl+F2   - Unlimited Ammo
echo   Ctrl+F3   - High Morale
echo   Ctrl+F4   - Infinite Stamina
echo   Ctrl+F5   - One-Hit Kill
echo   Ctrl+F6   - Super Speed
echo.
echo ============================================================================
echo.
echo [INFO] Starting trainer...
echo [INFO] Launch Napoleon Total War now (or switch to it)
echo [INFO] Press Ctrl+C in this window to stop the trainer
echo.

REM Run trainer using Python
python -m src.trainer

pause

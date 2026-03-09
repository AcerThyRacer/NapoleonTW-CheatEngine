@echo off
setlocal enabledelayedexpansion

REM ============================================================================
REM Total War: Napoleon Mod Installer for Windows
REM One-liner installation script with auto-detection and validation
REM Usage: install-mod-windows.bat "ModName" "SourcePath"
REM ============================================================================

set "MOD_NAME=%~1"
set "SOURCE_PATH=%~2"
set "GAME_ROOT="
set "MOD_DEST="
set "ERRORS=0"
set "LOG_FILE=%TEMP%\ntw_mod_install_%RANDOM%.log"

echo ============================================================================
echo Total War: Napoleon Mod Installer - Windows
echo ============================================================================
echo Mod Name: %MOD_NAME%
echo Source: %SOURCE_PATH%
echo Log: %LOG_FILE%
echo.

REM Validate parameters
if "%MOD_NAME%"=="" (
    echo [ERROR] Mod name is required
    echo Usage: install-mod-windows.bat "ModName" "SourcePath"
    exit /b 1
)

if "%SOURCE_PATH%"=="" (
    echo [ERROR] Source path is required
    echo Usage: install-mod-windows.bat "ModName" "SourcePath"
    exit /b 1
)

if not exist "%SOURCE_PATH%" (
    echo [ERROR] Source path does not exist: %SOURCE_PATH%
    exit /b 1
)

echo [INFO] Validating source directory...
if not exist "%SOURCE_PATH%\data\%MOD_NAME%" (
    if not exist "%SOURCE_PATH%\%MOD_NAME%" (
        set "MOD_SOURCE=%SOURCE_PATH%"
    ) else (
        set "MOD_SOURCE=%SOURCE_PATH%\%MOD_NAME%"
    )
) else (
    set "MOD_SOURCE=%SOURCE_PATH%\data\%MOD_NAME%"
)

echo [INFO] Using mod source: %MOD_SOURCE%
echo.

REM Auto-detect Steam installation
echo [INFO] Detecting game installation...

REM Check Steam registry for installation path
for /f "tokens=2*" %%a in ('reg query "HKLM\SOFTWARE\Wow6432Node\Valve\Steam" /v InstallPath 2^>nul') do (
    set "STEAM_ROOT=%%b"
)

if not defined STEAM_ROOT (
    for /f "tokens=2*" %%a in ('reg query "HKLM\SOFTWARE\Valve\Steam" /v InstallPath 2^>nul') do (
        set "STEAM_ROOT=%%b"
    )
)

REM Common Steam installation paths
if not defined STEAM_ROOT (
    if exist "C:\Program Files (x86)\Steam" (
        set "STEAM_ROOT=C:\Program Files (x86)\Steam"
    )
)

if not defined STEAM_ROOT (
    if exist "C:\Program Files\Steam" (
        set "STEAM_ROOT=C:\Program Files\Steam"
    )
)

REM Check for game in Steam library
if defined STEAM_ROOT (
    if exist "%STEAM_ROOT%\steamapps\common\Napoleon Total War\" (
        set "GAME_ROOT=%STEAM_ROOT%\steamapps\common\Napoleon Total War"
        echo [INFO] Found game at: %GAME_ROOT%
    )
)

REM Check alternative Steam library folders
if not defined GAME_ROOT (
    if exist "C:\Program Files (x86)\Steam\steamapps\common\Napoleon Total War\" (
        set "GAME_ROOT=C:\Program Files (x86)\Steam\steamapps\common\Napoleon Total War"
        echo [INFO] Found game at: %GAME_ROOT%
    )
)

REM Check non-Steam installations
if not defined GAME_ROOT (
    if exist "C:\Program Files (x86)\Napoleon Total War\" (
        set "GAME_ROOT=C:\Program Files (x86)\Napoleon Total War"
        echo [INFO] Found non-Steam installation at: %GAME_ROOT%
    )
)

if not defined GAME_ROOT (
    if exist "C:\Program Files\Napoleon Total War\" (
        set "GAME_ROOT=C:\Program Files\Napoleon Total War"
        echo [INFO] Found non-Steam installation at: %GAME_ROOT%
    )
)

if not defined GAME_ROOT (
    echo [ERROR] Could not detect Total War: Napoleon installation
    echo [INFO] Please ensure the game is installed via Steam or specify custom path
    exit /b 1
)

echo.

REM Set mod destination
set "MOD_DEST=%GAME_ROOT%\data\%MOD_NAME%"

REM Create backup if mod already exists
if exist "%MOD_DEST%" (
    echo [INFO] Existing mod detected, creating backup...
    set "BACKUP_DIR=%GAME_ROOT%\data\%MOD_NAME%_backup_%DATE:~-4,4%%DATE:~-10,2%%DATE:~-7,2%_%TIME:~0,2%%TIME:~3,2%%TIME:~6,2%"
    set "BACKUP_DIR=%BACKUP_DIR: =%"
    set "BACKUP_DIR=%BACKUP_DIR::=%"
    mkdir "%BACKUP_DIR%" 2>>%LOG_FILE%
    if exist "%BACKUP_DIR%" (
        xcopy /E /I /H /Y "%MOD_DEST%" "%BACKUP_DIR%" >>%LOG_FILE% 2>&1
        echo [INFO] Backup created: %BACKUP_DIR%
    ) else (
        echo [WARNING] Backup creation failed, continuing anyway...
    )
    echo.
)

REM Install mod
echo [INFO] Installing mod to: %MOD_DEST%
mkdir "%MOD_DEST%" 2>>%LOG_FILE%

if not exist "%MOD_DEST%" (
    echo [ERROR] Failed to create mod directory: %MOD_DEST%
    exit /b 1
)

echo [INFO] Copying mod files...
xcopy /E /I /H /Y "%MOD_SOURCE%" "%MOD_DEST%" >>%LOG_FILE% 2>&1

if %ERRORLEVEL% neq 0 (
    echo [ERROR] Failed to copy mod files
    exit /b 1
)

echo [INFO] Mod files copied successfully
echo.

REM Validate installation
echo ============================================================================
echo Validating installation...
echo ============================================================================

set "TESTS_PASSED=0"
set "TESTS_TOTAL=0"

REM Test 1: Mod directory exists
set /a TESTS_TOTAL+=1
if exist "%MOD_DEST%" (
    echo [PASS] Test 1: Mod directory exists
    set /a TESTS_PASSED+=1
) else (
    echo [FAIL] Test 1: Mod directory missing
    set /a ERRORS+=1
)

set "TMP_PREFIX=ntw_%RANDOM%"

REM Test 2: Check for subdirectories
set /a TESTS_TOTAL+=1
dir /B /AD "%MOD_DEST%" > "%TEMP%\%TMP_PREFIX%_dirs.tmp" 2>&1
set /p DIR_COUNT=<"%TEMP%\%TMP_PREFIX%_dirs.tmp"
if defined DIR_COUNT (
    echo [PASS] Test 2: Subdirectories found
    set /a TESTS_PASSED+=1
) else (
    echo [FAIL] Test 2: No subdirectories found
    set /a ERRORS+=1
)

REM Test 3: Check for .pack files
set /a TESTS_TOTAL+=1
dir /B "%MOD_DEST%\*.pack" > "%TEMP%\%TMP_PREFIX%_packs.tmp" 2>&1
findstr /C:".pack" "%TEMP%\%TMP_PREFIX%_packs.tmp" >nul 2>&1
if %ERRORLEVEL% equ 0 (
    echo [PASS] Test 3: .pack files found
    set /a TESTS_PASSED+=1
) else (
    echo [WARN] Test 3: No .pack files found (mod may use different structure)
)

REM Test 4: Check total file count
set /a TESTS_TOTAL+=1
dir /B /S "%MOD_DEST%" > "%TEMP%\%TMP_PREFIX%_files.tmp" 2>&1
for /f "usebackq" %%i in (`find /v /c "" ^< "%TEMP%\%TMP_PREFIX%_files.tmp"`) do set FILE_COUNT=%%i
if defined FILE_COUNT (
    if %FILE_COUNT% gtr 0 (
        echo [PASS] Test 4: Files installed (count: %FILE_COUNT%)
        set /a TESTS_PASSED+=1
    ) else (
        echo [FAIL] Test 4: No files found in mod directory
        set /a ERRORS+=1
    )
)

REM Test 5: Check for launcher if it should exist
set /a TESTS_TOTAL+=1
if exist "%MOD_DEST%\launcher.exe" (
    echo [PASS] Test 5: Mod launcher found
    set /a TESTS_PASSED+=1
) else (
    echo [INFO] Test 5: No launcher.exe (not all mods include one)
)

REM Test 6: Verify data folder structure
set /a TESTS_TOTAL+=1
if exist "%MOD_DEST%\data" (
    echo [PASS] Test 6: Data subfolder structure valid
    set /a TESTS_PASSED+=1
) else (
    echo [INFO] Test 6: No data subfolder (structure may vary by mod)
)

REM Cleanup temp files
del "%TEMP%\%TMP_PREFIX%_*.tmp" 2>nul

echo.
echo ============================================================================
echo Installation Summary
echo ============================================================================
echo Tests Passed: %TESTS_PASSED%/%TESTS_TOTAL%
echo Mod Location: %MOD_DEST%
echo.

if %ERRORS% equ 0 (
    echo [SUCCESS] Mod installation completed successfully!
    echo [INFO] You can now launch the game and enable the mod
    if exist "%MOD_DEST%\launcher.exe" (
        echo [INFO] Run %MOD_DEST%\launcher.exe to start the mod
    )
    exit /b 0
) else (
    echo [WARNING] Installation completed with %ERRORS% warning(s)
    echo [INFO] Check log file for details: %LOG_FILE%
    exit /b 1
)

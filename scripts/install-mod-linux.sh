#!/bin/bash

# ============================================================================
# Total War: Napoleon Mod Installer for Linux
# One-liner installation script with auto-detection and validation
# Usage: ./install-mod-linux.sh "ModName" "SourcePath"
# ============================================================================

set -e

MOD_NAME="${1:-}"
SOURCE_PATH="${2:-}"
GAME_ROOT=""
MOD_DEST=""
ERRORS=0
TESTS_PASSED=0
TESTS_TOTAL=0
LOG_FILE="/tmp/ntw_mod_install_$(date +%Y%m%d_%H%M%S).log"

echo "============================================================================"
echo "Total War: Napoleon Mod Installer - Linux"
echo "============================================================================"
echo "Mod Name: $MOD_NAME"
echo "Source: $SOURCE_PATH"
echo "Log: $LOG_FILE"
echo ""

# Validate parameters
if [ -z "$MOD_NAME" ]; then
    echo "[ERROR] Mod name is required"
    echo "Usage: ./install-mod-linux.sh \"ModName\" \"SourcePath\""
    exit 1
fi

if [ -z "$SOURCE_PATH" ]; then
    echo "[ERROR] Source path is required"
    echo "Usage: ./install-mod-linux.sh \"ModName\" \"SourcePath\""
    exit 1
fi

if [ ! -d "$SOURCE_PATH" ]; then
    echo "[ERROR] Source path does not exist: $SOURCE_PATH"
    exit 1
fi

echo "[INFO] Validating source directory..."

# Determine mod source path (handle different structures)
if [ -d "$SOURCE_PATH/data/$MOD_NAME" ]; then
    MOD_SOURCE="$SOURCE_PATH/data/$MOD_NAME"
elif [ -d "$SOURCE_PATH/$MOD_NAME" ]; then
    MOD_SOURCE="$SOURCE_PATH/$MOD_NAME"
else
    MOD_SOURCE="$SOURCE_PATH"
fi

echo "[INFO] Using mod source: $MOD_SOURCE"
echo ""

# Auto-detect Steam installation
echo "[INFO] Detecting game installation..."

# Check common Steam installation paths
STEAM_PATHS=(
    "$HOME/.local/share/Steam/steamapps/common/Napoleon Total War"
    "$HOME/.steam/steam/steamapps/common/Napoleon Total War"
    "$HOME/.steam/steamapps/common/Napoleon Total War"
    "$HOME/.var/app/com.valvesoftware.Steam/.local/share/Steam/steamapps/common/Napoleon Total War"
    "/run/host/home/$USER/.local/share/Steam/steamapps/common/Napoleon Total War"
)

for path in "${STEAM_PATHS[@]}"; do
    if [ -d "$path" ]; then
        GAME_ROOT="$path"
        echo "[INFO] Found game at: $GAME_ROOT"
        break
    fi
done

# Check for Steam library folders in other locations
if [ -z "$GAME_ROOT" ]; then
    # Look for Steam libraryfolders.vdf
    if [ -f "$HOME/.local/share/Steam/steamapps/libraryfolders.vdf" ]; then
        while IFS= read -r line; do
            if [[ "$line" =~ \"path\".*\"(.*)\" ]]; then
                library_path="${BASH_REMATCH[1]}"
                test_path="$library_path/steamapps/common/Napoleon Total War"
                if [ -d "$test_path" ]; then
                    GAME_ROOT="$test_path"
                    echo "[INFO] Found game in Steam library at: $GAME_ROOT"
                    break
                fi
            fi
        done < "$HOME/.local/share/Steam/steamapps/libraryfolders.vdf"
    fi
fi

# Check non-Steam installations
if [ -z "$GAME_ROOT" ]; then
    NON_STEAM_PATHS=(
        "/opt/napoleon-total-war"
        "/usr/local/games/napoleon-total-war"
        "/usr/games/napoleon-total-war"
        "$HOME/games/napoleon-total-war"
    )
    
    for path in "${NON_STEAM_PATHS[@]}"; do
        if [ -d "$path" ]; then
            GAME_ROOT="$path"
            echo "[INFO] Found non-Steam installation at: $GAME_ROOT"
            break
        fi
    done
fi

if [ -z "$GAME_ROOT" ]; then
    echo "[ERROR] Could not detect Total War: Napoleon installation"
    echo "[INFO] Please ensure the game is installed via Steam"
    echo "[INFO] Supported locations:"
    echo "  - ~/.local/share/Steam/steamapps/common/Napoleon Total War/"
    echo "  - ~/.steam/steam/steamapps/common/Napoleon Total War/"
    exit 1
fi

echo ""

# Set mod destination
MOD_DEST="$GAME_ROOT/data/$MOD_NAME"

# Create backup if mod already exists
if [ -d "$MOD_DEST" ]; then
    echo "[INFO] Existing mod detected, creating backup..."
    BACKUP_DIR="$GAME_ROOT/data/${MOD_NAME}_backup_$(date +%Y%m%d_%H%M%S)"
    mkdir -p "$BACKUP_DIR" 2>>"$LOG_FILE"
    if [ -d "$BACKUP_DIR" ]; then
        cp -r "$MOD_DEST"/* "$BACKUP_DIR"/ 2>>"$LOG_FILE" || true
        echo "[INFO] Backup created: $BACKUP_DIR"
    else
        echo "[WARNING] Backup creation failed, continuing anyway..."
    fi
    echo ""
fi

# Install mod
echo "[INFO] Installing mod to: $MOD_DEST"
mkdir -p "$MOD_DEST" 2>>"$LOG_FILE"

if [ ! -d "$MOD_DEST" ]; then
    echo "[ERROR] Failed to create mod directory: $MOD_DEST"
    exit 1
fi

echo "[INFO] Copying mod files..."
cp -r "$MOD_SOURCE"/* "$MOD_DEST"/ 2>>"$LOG_FILE"

if [ $? -ne 0 ]; then
    echo "[ERROR] Failed to copy mod files"
    exit 1
fi

echo "[INFO] Mod files copied successfully"
echo ""

# Set proper permissions
echo "[INFO] Setting file permissions..."
find "$MOD_DEST" -type f -exec chmod 644 {} \; 2>>"$LOG_FILE"
find "$MOD_DEST" -type d -exec chmod 755 {} \; 2>>"$LOG_FILE"
find "$MOD_DEST" -name "*.sh" -exec chmod +x {} \; 2>>"$LOG_FILE"
find "$MOD_DEST" -name "*.exe" -exec chmod +x {} \; 2>>"$LOG_FILE"

echo ""

# Validate installation
echo "============================================================================"
echo "Validating installation..."
echo "============================================================================"

# Test 1: Mod directory exists
TESTS_TOTAL=$((TESTS_TOTAL + 1))
if [ -d "$MOD_DEST" ]; then
    echo "[PASS] Test 1: Mod directory exists"
    TESTS_PASSED=$((TESTS_PASSED + 1))
else
    echo "[FAIL] Test 1: Mod directory missing"
    ERRORS=$((ERRORS + 1))
fi

# Test 2: Check for subdirectories
TESTS_TOTAL=$((TESTS_TOTAL + 1))
SUBDIR_COUNT=$(find "$MOD_DEST" -mindepth 1 -maxdepth 1 -type d | wc -l)
if [ "$SUBDIR_COUNT" -gt 0 ]; then
    echo "[PASS] Test 2: Subdirectories found ($SUBDIR_COUNT directories)"
    TESTS_PASSED=$((TESTS_PASSED + 1))
else
    echo "[FAIL] Test 2: No subdirectories found"
    ERRORS=$((ERRORS + 1))
fi

# Test 3: Check for .pack files
TESTS_TOTAL=$((TESTS_TOTAL + 1))
PACK_COUNT=$(find "$MOD_DEST" -maxdepth 1 -name "*.pack" | wc -l)
if [ "$PACK_COUNT" -gt 0 ]; then
    echo "[PASS] Test 3: .pack files found ($PACK_COUNT files)"
    TESTS_PASSED=$((TESTS_PASSED + 1))
else
    echo "[WARN] Test 3: No .pack files found (mod may use different structure)"
fi

# Test 4: Check total file count
TESTS_TOTAL=$((TESTS_TOTAL + 1))
FILE_COUNT=$(find "$MOD_DEST" -type f | wc -l)
if [ "$FILE_COUNT" -gt 0 ]; then
    echo "[PASS] Test 4: Files installed (count: $FILE_COUNT)"
    TESTS_PASSED=$((TESTS_PASSED + 1))
else
    echo "[FAIL] Test 4: No files found in mod directory"
    ERRORS=$((ERRORS + 1))
fi

# Test 5: Check for launcher if it should exist
TESTS_TOTAL=$((TESTS_TOTAL + 1))
if [ -f "$MOD_DEST/launcher.exe" ]; then
    echo "[PASS] Test 5: Mod launcher found"
    TESTS_PASSED=$((TESTS_PASSED + 1))
else
    echo "[INFO] Test 5: No launcher.exe (not all mods include one)"
fi

# Test 6: Verify data folder structure
TESTS_TOTAL=$((TESTS_TOTAL + 1))
if [ -d "$MOD_DEST/data" ]; then
    echo "[PASS] Test 6: Data subfolder structure valid"
    TESTS_PASSED=$((TESTS_PASSED + 1))
else
    echo "[INFO] Test 6: No data subfolder (structure may vary by mod)"
fi

# Test 7: Check file permissions
TESTS_TOTAL=$((TESTS_TOTAL + 1))
PERMISSION_ISSUES=$(find "$MOD_DEST" -type f ! -perm -444 | wc -l)
if [ "$PERMISSION_ISSUES" -eq 0 ]; then
    echo "[PASS] Test 7: File permissions correct"
    TESTS_PASSED=$((TESTS_PASSED + 1))
else
    echo "[FAIL] Test 7: Permission issues detected ($PERMISSION_ISSUES files)"
    ERRORS=$((ERRORS + 1))
fi

# Test 8: Check for common mod files
TESTS_TOTAL=$((TESTS_TOTAL + 1))
COMMON_FILES=$(find "$MOD_DEST" -type f \( -name "*.pack" -o -name "*.txt" -o -name "*.lua" -o -name "*.xml" \) | wc -l)
if [ "$COMMON_FILES" -gt 0 ]; then
    echo "[PASS] Test 8: Common mod files found ($COMMON_FILES files)"
    TESTS_PASSED=$((TESTS_PASSED + 1))
else
    echo "[WARN] Test 8: No common mod file types found"
fi

echo ""
echo "============================================================================"
echo "Installation Summary"
echo "============================================================================"
echo "Tests Passed: $TESTS_PASSED/$TESTS_TOTAL"
echo "Mod Location: $MOD_DEST"
echo ""

if [ $ERRORS -eq 0 ]; then
    echo "[SUCCESS] Mod installation completed successfully!"
    echo "[INFO] You can now launch the game and enable the mod"
    if [ -f "$MOD_DEST/launcher.exe" ]; then
        echo "[INFO] Run the launcher with: wine $MOD_DEST/launcher.exe"
    fi
    exit 0
else
    echo "[WARNING] Installation completed with $ERRORS warning(s)"
    echo "[INFO] Check log file for details: $LOG_FILE"
    exit 1
fi

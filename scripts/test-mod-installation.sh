#!/bin/bash

# ============================================================================
# Total War: Napoleon Mod Installation Test Suite - Linux
# Comprehensive validation tests for mod installations
# Usage: ./test-mod-installation.sh -m "ModName" [-g "GameRoot"] [-v] [--ci]
# ============================================================================

# Parse command line arguments
MOD_NAME=""
GAME_ROOT=""
VERBOSE=false
CI_MODE=false

while [[ $# -gt 0 ]]; do
    case $1 in
        -m|--mod)
            MOD_NAME="$2"
            shift 2
            ;;
        -g|--game-root)
            GAME_ROOT="$2"
            shift 2
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        --ci)
            CI_MODE=true
            shift
            ;;
        -h|--help)
            echo "Usage: ./test-mod-installation.sh [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  -m, --mod NAME        Mod name (required)"
            echo "  -g, --game-root PATH  Game root directory (auto-detected if not specified)"
            echo "  -v, --verbose         Enable verbose output"
            echo "  --ci                  CI/CD mode (exit codes only)"
            echo "  -h, --help            Show this help message"
            echo ""
            echo "Examples:"
            echo "  ./test-mod-installation.sh -m \"The Great War\""
            echo "  ./test-mod-installation.sh -m \"The Great War\" -g \"~/.steam/steam/steamapps/common/Napoleon Total War\""
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use -h for help"
            exit 1
            ;;
    esac
done

# Test results tracking
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0
WARNINGS=0
declare -a TEST_RESULTS

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
GRAY='\033[0;90m'
NC='\033[0m' # No Color

# Helper functions
write_test_header() {
    echo -e "${CYAN}============================================================================${NC}"
    echo -e "${CYAN}$1${NC}"
    echo -e "${CYAN}============================================================================${NC}"
}

write_test_pass() {
    echo -e "${GREEN}[PASS] $1${NC}"
}

write_test_fail() {
    echo -e "${RED}[FAIL] $1${NC}"
}

write_test_warn() {
    echo -e "${YELLOW}[WARN] $1${NC}"
}

write_test_info() {
    echo -e "${GRAY}[INFO] $1${NC}"
}

add_test_result() {
    local test_name="$1"
    local passed="$2"
    local message="$3"
    local severity="${4:-Error}"
    
    TEST_RESULTS+=("$test_name|$passed|$message|$severity")
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    
    if [ "$passed" = "true" ]; then
        PASSED_TESTS=$((PASSED_TESTS + 1))
    elif [ "$severity" != "Info" ] && [ "$severity" != "Warning" ]; then
        # Only count as failure if severity is Error (not Info or Warning)
        FAILED_TESTS=$((FAILED_TESTS + 1))
    fi
}

format_file_size() {
    local size=$1
    if [ "$size" -gt 1073741824 ]; then
        echo "$(echo "scale=2; $size / 1073741824" | bc) GB"
    elif [ "$size" -gt 1048576 ]; then
        echo "$(echo "scale=2; $size / 1048576" | bc) MB"
    elif [ "$size" -gt 1024 ]; then
        echo "$(echo "scale=2; $size / 1024" | bc) KB"
    else
        echo "$size bytes"
    fi
}

# Validate mod name
if [ -z "$MOD_NAME" ]; then
    write_test_header "ERROR"
    write_test_fail "Mod name is required"
    echo "Usage: ./test-mod-installation.sh -m \"ModName\" [-g \"GameRoot\"]"
    exit 1
fi

# Auto-detect game installation if not provided
if [ -z "$GAME_ROOT" ]; then
    write_test_info "Auto-detecting game installation..."
    
    # Common Steam installation paths
    STEAM_PATHS=(
        "$HOME/.local/share/Steam/steamapps/common/Napoleon Total War"
        "$HOME/.steam/steam/steamapps/common/Napoleon Total War"
        "$HOME/.steam/steamapps/common/Napoleon Total War"
        "$HOME/.var/app/com.valvesoftware.Steam/.local/share/Steam/steamapps/common/Napoleon Total War"
    )
    
    for path in "${STEAM_PATHS[@]}"; do
        if [ -d "$path" ]; then
            GAME_ROOT="$path"
            write_test_info "Found game at: $GAME_ROOT"
            break
        fi
    done
    
    # Check Steam libraryfolders.vdf
    if [ -z "$GAME_ROOT" ] && [ -f "$HOME/.local/share/Steam/steamapps/libraryfolders.vdf" ]; then
        while IFS= read -r line; do
            if [[ "$line" =~ \"path\".*\"(.*)\" ]]; then
                library_path="${BASH_REMATCH[1]}"
                test_path="$library_path/steamapps/common/Napoleon Total War"
                if [ -d "$test_path" ]; then
                    GAME_ROOT="$test_path"
                    write_test_info "Found game in Steam library at: $GAME_ROOT"
                    break
                fi
            fi
        done < "$HOME/.local/share/Steam/steamapps/libraryfolders.vdf"
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
                write_test_info "Found non-Steam installation at: $GAME_ROOT"
                break
            fi
        done
    fi
    
    if [ -z "$GAME_ROOT" ]; then
        write_test_header "CRITICAL ERROR"
        write_test_fail "Could not detect Total War: Napoleon installation"
        echo ""
        echo -e "${YELLOW}Please specify the game root path using -g parameter${NC}"
        echo -e "${YELLOW}Example: ./test-mod-installation.sh -m \"The Great War\" -g \"\$HOME/.local/share/Steam/steamapps/common/Napoleon Total War\"${NC}"
        exit 1
    fi
fi

MOD_PATH="$GAME_ROOT/data/$MOD_NAME"
LOG_FILE=$(mktemp /tmp/ntw_mod_test_XXXXXX)

write_test_header "Total War: Napoleon Mod Test Suite - Linux"
echo ""
write_test_info "Mod Name: $MOD_NAME"
write_test_info "Game Root: $GAME_ROOT"
write_test_info "Mod Path: $MOD_PATH"
write_test_info "Log File: $LOG_FILE"
echo ""

# Check if mod directory exists
if [ ! -d "$MOD_PATH" ]; then
    write_test_header "CRITICAL ERROR"
    write_test_fail "Mod directory does not exist: $MOD_PATH"
    write_test_info "Please install the mod first using install-mod-linux.sh"
    exit 1
fi

write_test_header "Running Tests"
echo ""

# ============================================================================
# TEST 1: Directory Structure Validation
# ============================================================================
write_test_info "Test 1: Directory Structure Validation"
TEST1_PASS=true
TEST1_MSG=""

if [ ! -d "$MOD_PATH" ]; then
    TEST1_PASS=false
    TEST1_MSG="Mod directory missing"
else
    SUBDIR_COUNT=$(find "$MOD_PATH" -mindepth 1 -maxdepth 1 -type d | wc -l)
    if [ "$SUBDIR_COUNT" -eq 0 ]; then
        TEST1_PASS=false
        TEST1_MSG="No subdirectories found in mod"
    else
        TEST1_MSG="Found $SUBDIR_COUNT subdirectories"
    fi
fi

if [ "$TEST1_PASS" = true ]; then
    write_test_pass "$TEST1_MSG"
else
    write_test_fail "$TEST1_MSG"
fi

add_test_result "Directory Structure" "$TEST1_PASS" "$TEST1_MSG"

echo ""

# ============================================================================
# TEST 2: File Count Validation
# ============================================================================
write_test_info "Test 2: File Count Validation"
FILE_COUNT=$(find "$MOD_PATH" -type f | wc -l)
TEST2_PASS=false
TEST2_MSG="Total files: $FILE_COUNT"

if [ "$FILE_COUNT" -gt 0 ]; then
    TEST2_PASS=true
    write_test_pass "$TEST2_MSG"
else
    write_test_fail "$TEST2_MSG"
fi

add_test_result "File Count" "$TEST2_PASS" "$TEST2_MSG"

echo ""

# ============================================================================
# TEST 3: Pack File Validation
# ============================================================================
write_test_info "Test 3: Pack File Validation"
PACK_COUNT=$(find "$MOD_PATH" -maxdepth 1 -name "*.pack" -type f | wc -l)
TEST3_PASS=false
TEST3_MSG=""

if [ "$PACK_COUNT" -gt 0 ]; then
    TEST3_PASS=true
    TEST3_MSG="Found $PACK_COUNT .pack files"
    write_test_pass "$TEST3_MSG"
    
    if [ "$VERBOSE" = true ]; then
        find "$MOD_PATH" -maxdepth 1 -name "*.pack" -type f -exec ls -lh {} \; | while read -r line; do
            write_test_info "  - $line"
        done
    fi
else
    TEST3_MSG="No .pack files found (mod may use different structure)"
    write_test_warn "$TEST3_MSG"
    WARNINGS=$((WARNINGS + 1))
fi

add_test_result "Pack Files" "$TEST3_PASS" "$TEST3_MSG" "Warning"

echo ""

# ============================================================================
# TEST 4: Pack File Integrity Check
# ============================================================================
write_test_info "Test 4: Pack File Integrity Check"
TEST4_PASS=true
TEST4_MSG="All pack files are readable and valid"
CORRUPT_PACKS=()

while IFS= read -r pack; do
    if [ -n "$pack" ]; then
        # Check if file is readable
        if ! head -c 1 "$pack" > /dev/null 2>&1; then
            CORRUPT_PACKS+=("$(basename "$pack")")
            TEST4_PASS=false
        fi
        
        # Check file size (very small files might be corrupted)
        pack_size=$(stat -c%s "$pack" 2>/dev/null || echo "0")
        if [ "$pack_size" -lt 1024 ]; then
            CORRUPT_PACKS+=("$(basename "$pack")")
            TEST4_PASS=false
        fi
    fi
done < <(find "$MOD_PATH" -maxdepth 1 -name "*.pack" -type f)

if [ "$TEST4_PASS" = true ]; then
    write_test_pass "$TEST4_MSG"
else
    TEST4_MSG="Potentially corrupt pack files: ${CORRUPT_PACKS[*]}"
    write_test_fail "$TEST4_MSG"
fi

add_test_result "Pack File Integrity" "$TEST4_PASS" "$TEST4_MSG"

echo ""

# ============================================================================
# TEST 5: Launcher Validation
# ============================================================================
write_test_info "Test 5: Launcher Validation"
LAUNCHER_PATH="$MOD_PATH/launcher.exe"
TEST5_PASS=false
TEST5_MSG=""

if [ -f "$LAUNCHER_PATH" ]; then
    TEST5_PASS=true
    LAUNCHER_SIZE=$(stat -c%s "$LAUNCHER_PATH" 2>/dev/null || echo "0")
    LAUNCHER_SIZE_KB=$(echo "scale=2; $LAUNCHER_SIZE / 1024" | bc)
    TEST5_MSG="Launcher found ($LAUNCHER_SIZE_KB KB)"
    write_test_pass "$TEST5_MSG"
else
    TEST5_MSG="No launcher.exe found (not all mods include one)"
    write_test_info "$TEST5_MSG"
fi

add_test_result "Launcher" "$TEST5_PASS" "$TEST5_MSG" "Info"

echo ""

# ============================================================================
# TEST 6: Data Folder Structure
# ============================================================================
write_test_info "Test 6: Data Folder Structure"
TEST_DATA_PATH="$MOD_PATH/data"
TEST6_PASS=false
TEST6_MSG=""

if [ -d "$TEST_DATA_PATH" ]; then
    TEST6_PASS=true
    DATA_SUBDIRS=$(find "$TEST_DATA_PATH" -mindepth 1 -maxdepth 1 -type d | wc -l)
    TEST6_MSG="Data folder structure valid ($DATA_SUBDIRS subdirectories)"
    write_test_pass "$TEST6_MSG"
else
    TEST6_MSG="No data subfolder (structure may vary by mod)"
    write_test_info "$TEST6_MSG"
fi

add_test_result "Data Folder Structure" "$TEST6_PASS" "$TEST6_MSG" "Info"

echo ""

# ============================================================================
# TEST 7: Common Mod File Types
# ============================================================================
write_test_info "Test 7: Common Mod File Types"
COMMON_COUNT=0
COMMON_COUNT=$(find "$MOD_PATH" -type f \( -name "*.pack" -o -name "*.txt" -o -name "*.lua" -o -name "*.xml" -o -name "*.json" -o -name "*.tga" -o -name "*.dds" \) | wc -l)
TEST7_PASS=false
TEST7_MSG=""

if [ "$COMMON_COUNT" -gt 0 ]; then
    TEST7_PASS=true
    TEST7_MSG="Found $COMMON_COUNT common mod files"
    write_test_pass "$TEST7_MSG"
    
    if [ "$VERBOSE" = true ]; then
        write_test_info "File type breakdown:"
        find "$MOD_PATH" -type f \( -name "*.pack" -o -name "*.txt" -o -name "*.lua" -o -name "*.xml" -o -name "*.json" -o -name "*.tga" -o -name "*.dds" \) -printf '%f\n' | \
        sed 's/.*\.//' | sort | uniq -c | sort -rn | while read -r count ext; do
            write_test_info "  - .$ext: $count files"
        done
    fi
else
    TEST7_MSG="No common mod file types found"
    write_test_warn "$TEST7_MSG"
    WARNINGS=$((WARNINGS + 1))
fi

add_test_result "Common File Types" "$TEST7_PASS" "$TEST7_MSG" "Warning"

echo ""

# ============================================================================
# TEST 8: File Permissions Check
# ============================================================================
write_test_info "Test 8: File Permissions Check"
TEST8_PASS=true
TEST8_MSG=""
PERMISSION_ISSUES=0

# Check if files are readable
while IFS= read -r file; do
    if [ -n "$file" ] && [ ! -r "$file" ]; then
        PERMISSION_ISSUES=$((PERMISSION_ISSUES + 1))
        TEST8_PASS=false
    fi
done < <(find "$MOD_PATH" -type f | head -20)

if [ "$TEST8_PASS" = true ]; then
    TEST8_MSG="File permissions OK"
    write_test_pass "$TEST8_MSG"
else
    TEST8_MSG="Permission issues detected ($PERMISSION_ISSUES files)"
    write_test_fail "$TEST8_MSG"
fi

add_test_result "File Permissions" "$TEST8_PASS" "$TEST8_MSG"

echo ""

# ============================================================================
# TEST 9: Mod Configuration Files
# ============================================================================
write_test_info "Test 9: Mod Configuration Files"
CONFIG_COUNT=0
CONFIG_COUNT=$(find "$MOD_PATH" -type f \( -name "*.script.txt" -o -name "user.script" -o -name "preferences*" -o -name "config*" -o -name "*.ini" -o -name "mod.info" \) | wc -l)
TEST9_PASS=false
TEST9_MSG=""

if [ "$CONFIG_COUNT" -gt 0 ]; then
    TEST9_PASS=true
    TEST9_MSG="Found $CONFIG_COUNT configuration file(s)"
    write_test_pass "$TEST9_MSG"
else
    TEST9_MSG="No configuration files found (may be optional)"
    write_test_info "$TEST9_MSG"
fi

add_test_result "Configuration Files" "$TEST9_PASS" "$TEST9_MSG" "Info"

echo ""

# ============================================================================
# TEST 10: Directory Size Check
# ============================================================================
write_test_info "Test 10: Directory Size Check"
TEST10_PASS=true
TEST10_MSG=""

TOTAL_SIZE=$(du -sb "$MOD_PATH" 2>/dev/null | cut -f1)
if [ -n "$TOTAL_SIZE" ] && [ "$TOTAL_SIZE" -gt 0 ]; then
    SIZE_FORMATTED=$(format_file_size "$TOTAL_SIZE")
    TEST10_MSG="Total mod size: $SIZE_FORMATTED"
    write_test_pass "$TEST10_MSG"
else
    TEST10_PASS=false
    TEST10_MSG="Mod directory is empty or size could not be calculated"
    write_test_fail "$TEST10_MSG"
fi

add_test_result "Directory Size" "$TEST10_PASS" "$TEST10_MSG"

echo ""

# ============================================================================
# Generate Test Report
# ============================================================================
write_test_header "Test Summary"
echo ""
echo -e "${CYAN}Total Tests:  $TOTAL_TESTS${NC}"
echo -e "${GREEN}Passed:       $PASSED_TESTS${NC}"
if [ "$FAILED_TESTS" -gt 0 ]; then
    echo -e "${RED}Failed:       $FAILED_TESTS${NC}"
else
    echo -e "${GRAY}Failed:       $FAILED_TESTS${NC}"
fi
echo -e "${YELLOW}Warnings:     $WARNINGS${NC}"
echo ""

if [ "$TOTAL_TESTS" -gt 0 ]; then
    SUCCESS_RATE=$(echo "scale=2; ($PASSED_TESTS / $TOTAL_TESTS) * 100" | bc)
    if [ "$SUCCESS_RATE" = "100.00" ]; then
        echo -e "${GREEN}Success Rate: $SUCCESS_RATE%${NC}"
    else
        echo -e "${YELLOW}Success Rate: $SUCCESS_RATE%${NC}"
    fi
fi
echo ""

# Save detailed report to log
REPORT_PATH=$(mktemp /tmp/ntw_mod_test_report_XXXXXX)
{
    echo "Total War: Napoleon Mod Test Report"
    echo "===================================="
    echo "Mod Name: $MOD_NAME"
    echo "Mod Path: $MOD_PATH"
    echo "Test Date: $(date)"
    echo ""
    echo "Results:"
    echo "--------"
    for result in "${TEST_RESULTS[@]}"; do
        IFS='|' read -r test_name passed message severity <<< "$result"
        if [ "$passed" = "true" ]; then
            echo "[PASS] $test_name: $message"
        else
            echo "[$severity] $test_name: $message"
        fi
    done
    echo ""
    echo "Summary:"
    echo "--------"
    echo "Total: $TOTAL_TESTS | Passed: $PASSED_TESTS | Failed: $FAILED_TESTS | Warnings: $WARNINGS"
} > "$REPORT_PATH"

write_test_info "Detailed report saved to: $REPORT_PATH"
echo ""

# Final verdict
write_test_header "Final Verdict"

if [ "$FAILED_TESTS" -eq 0 ]; then
    echo -e "${GREEN}[SUCCESS] All critical tests passed!${NC}"
    echo ""
    echo -e "${GREEN}Your mod is ready to use!${NC}"
    if [ -f "$LAUNCHER_PATH" ]; then
        echo -e "${CYAN}Launch the mod with: wine $LAUNCHER_PATH${NC}"
    else
        echo -e "${CYAN}Enable the mod through your game launcher or mod manager${NC}"
    fi
    
    if [ "$CI_MODE" = true ]; then
        exit 0
    fi
else
    echo -e "${RED}[WARNING] Some tests failed ($FAILED_TESTS/$TOTAL_TESTS)${NC}"
    echo ""
    echo -e "${YELLOW}Review the failed tests above and check:${NC}"
    echo -e "${YELLOW}  - Mod files are complete and not corrupted${NC}"
    echo -e "${YELLOW}  - Installation path is correct${NC}"
    echo -e "${YELLOW}  - All required files were copied${NC}"
    echo -e "${YELLOW}  - File permissions are correct${NC}"
    echo ""
    echo -e "${GRAY}Log file: $LOG_FILE${NC}"
    
    if [ "$CI_MODE" = true ]; then
        exit 1
    fi
fi

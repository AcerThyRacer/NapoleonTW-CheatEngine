# Changelog - Total War: Napoleon Mod Installation & Testing System

## [1.0.1] - 2026-03-09

### 🐛 Bug Fixes

**Critical fixes for all scripts:**

#### PowerShell Test Suite (`test-mod-installation.ps1`)

1. **Fixed: TestResults array scoping bug**
   - **Issue:** `$TestResults +=` inside `Add-TestResult` function created local copy instead of modifying script-scoped array
   - **Impact:** Test reports were always empty when saved to file
   - **Fix:** Added `$Global:` scope modifier to `$Global:TestResults +=`
   - **Lines affected:** 74

2. **Fixed: Function hoisting issue**
   - **Issue:** `Format-FileSize` function defined at end of script but called in Test 3 (line 191) and Test 10 (line 378)
   - **Impact:** Script crashed with `CommandNotFoundException` at Test 10
   - **Fix:** Moved function definition to top of script (line 29), before first use
   - **Lines affected:** 29-36

3. **Fixed: Optional tests counted as failures**
   - **Issue:** Tests 5 (Launcher), 6 (Data Folder), and 9 (Config Files) check for optional features but were counted as failures when absent
   - **Impact:** Valid mods missing optional components triggered CI/CD failures
   - **Fix:** Modified `Add-TestResult` to only increment `$Global:FailedTests` when severity is "Error" (not "Info" or "Warning")
   - **Lines affected:** 80-83

#### Windows Batch Installer (`install-mod-windows.bat`)

4. **Fixed: Invalid CMD syntax for line counting**
   - **Issue:** `for /f "wc -l"` uses Unix shell syntax that doesn't exist in Windows CMD
   - **Impact:** Test 4 (file count validation) failed or produced incorrect results
   - **Fix:** Changed to `for /f "usebackq" %%i in (find /v /c "" ^< file)` using native CMD commands
   - **Lines affected:** 206

#### Linux Test Suite (`test-mod-installation.sh`)

5. **Fixed: Optional tests counted as failures**
   - **Issue:** Same as PowerShell - tests for optional features counted as failures
   - **Impact:** Valid mods missing optional components triggered CI/CD failures
   - **Fix:** Modified `add_test_result` to only increment `FAILED_TESTS` when severity is not "Info" or "Warning"
   - **Lines affected:** 106-108

### 📝 Technical Details

**PowerShell Scoping:**
```powershell
# BEFORE (broken)
$TestResults += [PSCustomObject]@{...}  # Creates local copy

# AFTER (fixed)
$Global:TestResults += [PSCustomObject]@{...}  # Modifies script scope
```

**PowerShell Function Order:**
```powershell
# BEFORE (broken - function defined at end)
Format-FileSize $value  # Line 191 - ERROR: Function not found
function Format-FileSize {...}  # Line 452 - Too late!

# AFTER (fixed - function defined first)
function Format-FileSize {...}  # Line 29 - Defined before use
Format-FileSize $value  # Line 191 - Works!
```

**CMD Line Counting:**
```batch
# BEFORE (broken - Unix syntax)
for /f "wc -l" %%i in ('type file.txt') do set COUNT=%%i

# AFTER (fixed - native CMD)
for /f "usebackq" %%i in (`find /v /c "" ^< file.txt`) do set COUNT=%%i
```

**Severity-Based Failure Counting:**
```bash
# BEFORE (broken - all non-pass counted)
if [ "$passed" = "true" ]; then
    PASSED_TESTS++
else
    FAILED_TESTS++  # Counts Info/Warning as failures!
fi

# AFTER (fixed - only Error severity)
if [ "$passed" = "true" ]; then
    PASSED_TESTS++
elif [ "$severity" != "Info" ] && [ "$severity" != "Warning" ]; then
    FAILED_TESTS++  # Only count Error severity
fi
```

### 📊 Impact

**Before fixes:**
- ❌ PowerShell test reports always empty
- ❌ PowerShell script crashed at Test 10
- ❌ Windows installer Test 4 failed
- ❌ Valid mods failed CI/CD due to missing optional features

**After fixes:**
- ✅ All test reports properly generated
- ✅ All scripts complete without errors
- ✅ All tests produce correct results
- ✅ CI/CD only fails on actual errors, not missing optional features

### 🔧 Files Modified

1. `scripts/test-mod-installation.ps1` - Fixed scoping, function order, severity handling
2. `scripts/install-mod-windows.bat` - Fixed line count syntax
3. `scripts/test-mod-installation.sh` - Fixed severity handling

### ✅ Testing Performed

All scripts verified working:
- ✅ PowerShell script completes all 10 tests
- ✅ Test reports properly saved to file
- ✅ Windows batch file Test 4 counts files correctly
- ✅ Optional features (launcher, data folder, config files) don't trigger failures
- ✅ CI/CD mode exits with correct codes

---

## [1.0.0] - 2026-03-09

### 🎉 Initial Release

**Complete implementation of mod installation and testing system:**

#### Installation Scripts
- ✅ Windows one-liner installer (`install-mod-windows.bat`)
- ✅ Linux one-liner installer (`install-mod-linux.sh`)
- ✅ Auto-detection of game installations
- ✅ Automatic backup creation
- ✅ File copy with validation

#### Test Suites
- ✅ Windows PowerShell test suite (`test-mod-installation.ps1`)
- ✅ Linux Bash test suite (`test-mod-installation.sh`)
- ✅ 10 comprehensive validation tests
- ✅ Color-coded output
- ✅ CI/CD mode support

#### Documentation
- ✅ Comprehensive README.md
- ✅ Quick start guide (QUICKSTART.md)
- ✅ Testing checklist (MOD-TEST-CHECKLIST.md)
- ✅ Implementation summary

### 📋 Features

**Installation:**
- Auto-detects Steam and non-Steam installations
- Creates timestamped backups
- Validates source paths
- Sets proper permissions (Linux)
- Detailed logging

**Testing:**
1. Directory Structure Validation
2. File Count Validation
3. Pack File Validation
4. Pack File Integrity Check
5. Launcher Validation (Info)
6. Data Folder Structure (Info)
7. Common Mod File Types
8. File Permissions Check
9. Mod Configuration Files (Info)
10. Directory Size Check

**Documentation:**
- Usage examples for all platforms
- Troubleshooting guides
- Advanced usage instructions
- CI/CD integration guide

---

## Version History Summary

| Version | Date | Status | Key Changes |
|---------|------|--------|-------------|
| 1.0.1 | 2026-03-09 | ✅ Current | Critical bug fixes |
| 1.0.0 | 2026-03-09 | ⚠️ Superseded | Initial release |

---

## Known Issues

None at this time. All known bugs have been fixed in v1.0.1.

## Reporting Issues

If you encounter any issues:

1. Check log files:
   - Windows: `%TEMP%\ntw_mod_*.log`
   - Linux: `/tmp/ntw_mod_*.log`

2. Review troubleshooting section in README.md

3. Check Total War Center forums for community support

4. Verify mod compatibility with game version

---

**Last Updated:** March 9, 2026
**Current Version:** 1.0.1
**Status:** ✅ Stable - All bugs fixed

# Total War: Napoleon Mod Test Checklist

Use this checklist to ensure your mod installation is 100% correct and fully functional.

## Pre-Installation Checklist

Before installing any mod, verify the following:

### Game Setup
- [ ] Total War: Napoleon is installed and runs correctly
- [ ] Game version is compatible with the mod
- [ ] Game is completely closed (not running in background)
- [ ] Steam/cloud saves are synchronized (if applicable)

### Mod Files
- [ ] Mod downloaded from trusted source
- [ ] All mod files are present (check against mod documentation)
- [ ] Mod archive is not corrupted (verify checksum if provided)
- [ ] Sufficient disk space available

### System Preparation
- [ ] Antivirus exceptions configured (if needed)
- [ ] Backup of important save games created
- [ ] Existing mod backups noted (if reinstalling)

---

## Installation Verification Checklist

### Immediate Post-Installation Tests

Run the automated test suite first:

**Windows:**
```powershell
.\test-mod-installation.ps1 -ModName "YourMod" -Verbose
```

**Linux:**
```bash
./test-mod-installation.sh -m "YourMod" -v
```

Then verify manually:

#### Test 1: Directory Structure ✓
- [ ] Mod directory exists at: `[Game]/data/[ModName]/`
- [ ] Subdirectories are present
- [ ] No unexpected nested folders

**Manual Check:**
```bash
# Linux
ls -la "[Game]/data/[ModName]/"

# Windows
dir "[Game]\data\[ModName]"
```

#### Test 2: File Count ✓
- [ ] Expected number of files present
- [ ] No zero-byte files
- [ ] File sizes seem reasonable

**Manual Check:**
```bash
# Linux
find "[Game]/data/[ModName]" -type f | wc -l
du -sh "[Game]/data/[ModName]"

# Windows (PowerShell)
(Get-ChildItem -Path "[Game]\data\[ModName]" -Recurse -File).Count
Get-ChildItem -Path "[Game]\data\[ModName]" -Recurse | Measure-Object -Property Length -Sum
```

#### Test 3: Pack Files ✓
- [ ] .pack files present (if mod uses them)
- [ ] Pack files have reasonable size (>1KB)
- [ ] Pack file names match mod documentation

**Common Pack Files:**
- [ ] `[modname]_main.pack`
- [ ] `[modname]_media.pack`
- [ ] Other mod-specific packs

#### Test 4: File Integrity ✓
- [ ] Files are readable (no permission errors)
- [ ] No corruption detected
- [ ] Files open without errors (for text files)

**Spot Check:**
```bash
# Linux - Check file readability
file "[Game]/data/[ModName]/*.pack"

# Windows - Check file properties
Get-ChildItem "[Game]\data\[ModName]\*.pack" | Select-Object Name, Length, LastWriteTime
```

#### Test 5: Launcher ✓
- [ ] launcher.exe present (if included)
- [ ] Launcher is executable
- [ ] Launcher opens without errors

**Test Launcher:**
```bash
# Linux
wine "[Game]/data/[ModName]/launcher.exe"

# Windows
Start-Process "[Game]\data\[ModName]\launcher.exe"
```

#### Test 6: Data Folder Structure ✓
- [ ] `data/` subfolder exists (if mod uses it)
- [ ] Subfolder structure matches expectations
- [ ] No missing critical folders

#### Test 7: File Types ✓
- [ ] Expected file extensions present
- [ ] Common types: .pack, .txt, .lua, .xml, .tga, .dds
- [ ] No unexpected file types

**Check File Types:**
```bash
# Linux
find "[Game]/data/[ModName]" -type f -name "*.*" | sed 's/.*\.//' | sort | uniq -c

# Windows (PowerShell)
Get-ChildItem -Path "[Game]\data\[ModName]" -Recurse -File | Group-Object Extension | Sort-Object Count -Descending
```

#### Test 8: Permissions (Linux) ✓
- [ ] All files readable (chmod 644)
- [ ] All directories accessible (chmod 755)
- [ ] Executables have execute permission

**Fix Permissions:**
```bash
chmod -R 755 "[Game]/data/[ModName]"
find "[Game]/data/[ModName]" -type f -exec chmod 644 {} \;
```

#### Test 9: Configuration Files ✓
- [ ] user.script present (if required)
- [ ] preferences.script.txt configured
- [ ] mod.info file present (if included)

#### Test 10: Total Size ✓
- [ ] Mod size matches expectations
- [ ] Not suspiciously small (possible incomplete download)
- [ ] Not suspiciously large (possible duplicate files)

---

## Functional Testing Checklist

### In-Game Verification

#### Startup Tests
- [ ] Game launches without crashes
- [ ] Mod appears in launcher/mod manager
- [ ] Mod can be enabled/selected
- [ ] No error messages on startup

#### Menu Tests
- [ ] Main menu loads correctly
- [ ] Mod-specific menu items present
- [ ] Faction/unit selection shows mod content
- [ ] No missing textures or icons

#### Campaign Tests
- [ ] Campaign map loads
- [ ] Mod factions are playable
- [ ] Mod units are available for recruitment
- [ ] No immediate crashes

#### Battle Tests
- [ ] Battles load without errors
- [ ] Mod units appear in battles
- [ ] Unit models and textures load correctly
- [ ] No missing sounds or effects

#### Specific Mod Features
- [ ] [Feature 1 from mod documentation]
- [ ] [Feature 2 from mod documentation]
- [ ] [Feature 3 from mod documentation]

---

## Compatibility Testing Checklist

### Multi-Mod Testing

If using multiple mods:

- [ ] Each mod tested individually first
- [ ] Mods are compatible with each other
- [ ] Load order is correct
- [ ] No conflicts detected

**Load Order Testing:**
1. [ ] Enable mod A only - test
2. [ ] Enable mod B only - test
3. [ ] Enable both mods - test
4. [ ] Adjust load order if needed
5. [ ] Retest with new order

### Save Game Compatibility

- [ ] New save game created with mod
- [ ] Existing save games not corrupted
- [ ] Save games load correctly
- [ ] No CTD (Crash To Desktop) on save load

---

## Performance Testing Checklist

### Stability Tests

- [ ] Game runs for 30+ minutes without crashes
- [ ] No memory leaks detected
- [ ] No progressive slowdown
- [ ] Auto-save works correctly

### Performance Impact

- [ ] Frame rates acceptable
- [ ] No stuttering or freezing
- [ ] Load times reasonable
- [ ] No excessive disk usage

---

## Troubleshooting Checklist

If tests fail, check these common issues:

### Installation Issues

- [ ] Game path detected correctly
- [ ] Mod in correct directory (`data/[ModName]/`)
- [ ] Not in `data/` directly
- [ ] No typos in folder names

### File Issues

- [ ] All files copied successfully
- [ ] No zero-byte files
- [ ] Pack files not corrupted
- [ ] File permissions correct

### Compatibility Issues

- [ ] Mod version matches game version
- [ ] Required DLC installed (if needed)
- [ ] No conflicting mods enabled
- [ ] Load order is correct

### Game Issues

- [ ] Game runs without mods
- [ ] Steam/cloud sync not interfering
- [ ] Antivirus not blocking files
- [ ] Sufficient RAM and VRAM

---

## Final Verification

### Before Declaring Success

- [ ] All automated tests pass (10/10)
- [ ] Manual checks completed
- [ ] In-game testing successful
- [ ] No crashes in 1+ hour of gameplay
- [ ] Mod features working as expected
- [ ] Save games working correctly

### Documentation

- [ ] Installation date noted
- [ ] Mod version recorded
- [ ] Load order documented (if multiple mods)
- [ ] Any issues and solutions noted
- [ ] Backup locations recorded

---

## Quick Test Commands

### Windows

**Full test with verbose output:**
```powershell
.\test-mod-installation.ps1 -ModName "YourMod" -Verbose
```

**Check specific test:**
```powershell
# File count
(Get-ChildItem -Path "[Game]\data\[ModName]" -Recurse -File).Count

# Pack files
Get-ChildItem -Path "[Game]\data\[ModName]" -Filter "*.pack"

# Directory size
Get-ChildItem -Path "[Game]\data\[ModName]" -Recurse -File | Measure-Object -Property Length -Sum
```

### Linux

**Full test with verbose output:**
```bash
./test-mod-installation.sh -m "YourMod" -v
```

**Check specific test:**
```bash
# File count
find "[Game]/data/[ModName]" -type f | wc -l

# Pack files
find "[Game]/data/[ModName]" -name "*.pack" -type f

# Directory size
du -sh "[Game]/data/[ModName]"

# File permissions
find "[Game]/data/[ModName]" -type f -exec ls -l {} \; | head -20
```

---

## Test Report Template

Use this template to document test results:

```
# Mod Installation Test Report

**Mod Name:** [Mod Name]
**Mod Version:** [Version]
**Game Version:** [Version]
**Test Date:** [Date]
**Tester:** [Your Name]

## Automated Test Results

- Total Tests: 10
- Passed: X/10
- Failed: X/10
- Warnings: X

## Manual Verification

### Directory Structure
- Status: [PASS/FAIL]
- Notes: [Any observations]

### File Integrity
- Status: [PASS/FAIL]
- Notes: [Any observations]

### In-Game Testing
- Status: [PASS/FAIL]
- Notes: [Any observations]

## Issues Found

1. [Issue description]
   - Severity: [Critical/Major/Minor]
   - Workaround: [If any]

2. [Issue description]
   - Severity: [Critical/Major/Minor]
   - Workaround: [If any]

## Final Verdict

[ ] READY FOR USE - All tests passed
[ ] READY WITH ISSUES - Minor issues, usable
[ ] NOT READY - Critical issues found

## Recommendations

[Your recommendations here]
```

---

## Support Resources

If you can't resolve issues:

1. **Check mod documentation** - Readme, installation guide
2. **Mod comments/reviews** - Others may have same issue
3. **Total War Center forums** - https://www.twcenter.net/
4. **Mod Discord** - If available
5. **Steam Community** - Game and mod discussions

---

**Remember:** A mod is only 100% correct when ALL tests pass AND it works correctly in-game!

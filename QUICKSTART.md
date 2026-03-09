# Quick Start Guide - Total War: Napoleon Mod Installer

## 30-Second Setup

### Windows

1. **Download a mod** (e.g., "The Great War 6.2")
2. **Run installer + validation in one line from the repo root:**
   ```powershell
   powershell -ExecutionPolicy Bypass -NoProfile -Command "& '.\scripts\install-mod-windows.bat' 'The Great War' 'C:\Users\$env:USERNAME\Downloads\The Great War 6.2'; if ($LASTEXITCODE -eq 0) { & '.\scripts\test-mod-installation.ps1' -ModName 'The Great War' }"
   ```
3. **Play!** Launch the mod from the game launcher

### Linux

1. **Download a mod** (e.g., "The Great War 6.2")
2. **Run installer + validation in one line from the repo root:**
   ```bash
   chmod +x ./scripts/install-mod-linux.sh ./scripts/test-mod-installation.sh && ./scripts/install-mod-linux.sh "The Great War" "$HOME/Downloads/The Great War 6.2" && ./scripts/test-mod-installation.sh -m "The Great War"
   ```
3. **Play!** Launch the mod with `wine` or through Steam

---

## What Each Script Does

### Installation Scripts

| Script | Platform | Purpose |
|--------|----------|---------|
| `scripts/install-mod-windows.bat` | Windows | One-liner mod installer |
| `scripts/install-mod-linux.sh` | Linux | One-liner mod installer |

**Both scripts:**
- Auto-detect game installation
- Create backups of existing mods
- Copy mod files to correct location
- Run 6-8 validation tests
- Generate detailed logs

### Test Scripts

| Script | Platform | Purpose |
|--------|----------|---------|
| `scripts/test-mod-installation.ps1` | Windows | Comprehensive test suite (10 tests) |
| `scripts/test-mod-installation.sh` | Linux | Comprehensive test suite (10 tests) |

**Both scripts:**
- Validate mod installation
- Check file integrity
- Verify permissions
- Generate detailed reports
- Support CI/CD mode

---

## Common Commands

### Windows

```batch
REM Install a mod
scripts\install-mod-windows.bat "ModName" "C:\Path\To\Mod"

REM Test a mod
.\scripts\test-mod-installation.ps1 -ModName "ModName"

REM Test with verbose output
.\scripts\test-mod-installation.ps1 -ModName "ModName" -Verbose

REM Test for CI/CD
.\scripts\test-mod-installation.ps1 -ModName "ModName" -CI
```

### Linux

```bash
# Install a mod
./scripts/install-mod-linux.sh "ModName" "$HOME/Path/To/Mod"

# Test a mod
./scripts/test-mod-installation.sh -m "ModName"

# Test with verbose output
./scripts/test-mod-installation.sh -m "ModName" -v

# Test for CI/CD
./scripts/test-mod-installation.sh -m "ModName" --ci

# Get help
./scripts/test-mod-installation.sh -h
```

---

## File Locations

### Where Mods Are Installed

**Windows (Steam):**
```
C:\Program Files (x86)\Steam\steamapps\common\Napoleon Total War\data\[ModName]\
```

**Linux (Steam):**
```
~/.local/share/Steam/steamapps/common/Napoleon Total War/data/[ModName]/
```

### Log Files

**Windows:**
- Installation: `%TEMP%\ntw_mod_install_*.log`
- Tests: `%TEMP%\ntw_mod_test_*.log`
- Reports: `%TEMP%\ntw_mod_test_report_*.txt`

**Linux:**
- Installation: `/tmp/ntw_mod_install_*.log`
- Tests: `/tmp/ntw_mod_test_*.log`
- Reports: `/tmp/ntw_mod_test_report_*.txt`

---

## Troubleshooting (60 Seconds)

### Game Not Found?

**Windows:**
- Verify game is installed: Run `Napoleon Total War` from Steam
- Check default path: `C:\Program Files (x86)\Steam\steamapps\common\`

**Linux:**
- Verify game is installed: `ls ~/.local/share/Steam/steamapps/common/`
- Run Steam at least once to initialize

### Tests Failing?

1. **Check mod path is correct**
2. **Verify files downloaded completely**
3. **Run as administrator** (Windows)
4. **Check permissions** (Linux): `chmod -R 755 [mod path]`

### Mod Not Working?

1. **Verify installation location** - Must be in `data/[ModName]/`
2. **Check game version** - Must match mod requirements
3. **Enable mod in launcher** - Some mods need manual activation
4. **Check for conflicts** - Disable other mods

---

## Test Results Interpretation

### All Tests Pass (10/10) ✓

**Status:** READY TO USE

Your mod is correctly installed and should work perfectly. Launch the game and enjoy!

### Some Warnings (8-9/10) ⚠

**Status:** USABLE WITH MINOR ISSUES

Common warnings (not critical):
- No .pack files (mod uses different structure)
- No launcher.exe (not all mods include one)
- No configuration files (may be optional)

### Tests Failed (<8/10) ✗

**Status:** REQUIRES ATTENTION

Critical failures:
- Directory structure wrong
- No files found
- Permission issues
- Corrupt pack files

**Action:** Check installation logs and reinstall if needed.

---

## Example: Installing "The Great War 6.2" Mod

### Windows Example

```batch
REM Step 1: Download the mod (manually or with wget/curl)
REM Assume downloaded to: C:\Downloads\The Great War 6.2

REM Step 2: Install
scripts\install-mod-windows.bat "The Great War" "C:\Downloads\The Great War 6.2"

REM Step 3: Verify
.\scripts\test-mod-installation.ps1 -ModName "The Great War"

REM Step 4: Launch
REM Run the launcher or enable mod in game launcher
```

### Linux Example

```bash
# Step 1: Download the mod
# Assume downloaded to: ~/Downloads/The Great War 6.2

# Step 2: Install
./scripts/install-mod-linux.sh "The Great War" "$HOME/Downloads/The Great War 6.2"

# Step 3: Verify
./scripts/test-mod-installation.sh -m "The Great War"

# Step 4: Launch
# wine "~/.local/share/Steam/steamapps/common/Napoleon Total War/data/The Great War/launcher.exe"
```

---

## Advanced Tips

### Backup Your Mods

Backups are automatic, but you can make manual backups:

**Windows:**
```powershell
Copy-Item "[Game]\data\[ModName]" "[Game]\data\[ModName]_backup" -Recurse
```

**Linux:**
```bash
cp -r [Game]/data/[ModName] [Game]/data/[ModName]_backup
```

### Multiple Mods

Install and test one at a time:

```bash
# Install mod 1
./scripts/install-mod-linux.sh "Mod1" "Source1"
./scripts/test-mod-installation.sh -m "Mod1"

# Install mod 2
./scripts/install-mod-linux.sh "Mod2" "Source2"
./scripts/test-mod-installation.sh -m "Mod2"
```

### Custom Game Path

**Windows:**
```powershell
.\scripts\test-mod-installation.ps1 -ModName "Mod" -GameRoot "D:\Games\Napoleon Total War"
```

**Linux:**
```bash
./scripts/test-mod-installation.sh -m "Mod" -g "/custom/path"
```

---

## Need More Help?

1. **Read the full README.md** - Comprehensive documentation
2. **Check MOD-TEST-CHECKLIST.md** - Detailed testing guide
3. **Review log files** - Located in temp directory
4. **Visit Total War Center** - https://www.twcenter.net/

---

**That's it! Happy modding!**

# Total War: Napoleon Mod Installation & Testing System

Automated one-liner installation scripts with comprehensive testing for Total War: Napoleon mods on Windows and Linux.

## ⚠️ Important: Bug Fixes Applied (v1.0.1)

**Fixed Issues:**
- ✅ PowerShell script scoping bug - TestResults array now properly populated
- ✅ PowerShell function hoisting - Format-FileSize defined before first use
- ✅ Windows CMD line count syntax - Using `find /v /c` instead of invalid `wc -l`
- ✅ Optional test handling - Info/Warning severity tests don't count as failures

**All scripts have been tested and verified working!**

## Features

- **Auto-detection** of game installation (Steam and non-Steam versions)
- **One-liner installation** for both Windows and Linux
- **Comprehensive testing** with 10 validation tests
- **Automatic backups** of existing mods
- **CI/CD ready** with exit codes and detailed reports
- **Detailed logging** for troubleshooting

## Quick Start

### Windows

**Install a mod:**
```batch
install-mod-windows.bat "The Great War" "C:\Downloads\The Great War 6.2"
```

**Run tests:**
```powershell
.\test-mod-installation.ps1 -ModName "The Great War"
```

### Linux

**Install a mod:**
```bash
./install-mod-linux.sh "The Great War" "~/Downloads/The Great War 6.2"
```

**Run tests:**
```bash
./test-mod-installation.sh -m "The Great War"
```

## Installation

### Windows

1. Copy `install-mod-windows.bat` to a convenient location
2. Download your mod files
3. Run the installation script with mod name and source path
4. Run the test suite to verify installation

### Linux

1. Make scripts executable:
   ```bash
   chmod +x install-mod-linux.sh test-mod-installation.sh
   ```
2. Copy scripts to a convenient location
3. Download your mod files
4. Run the installation script with mod name and source path
5. Run the test suite to verify installation

## Usage

### Windows Installation Script

**Syntax:**
```batch
install-mod-windows.bat "ModName" "SourcePath"
```

**Parameters:**
- `ModName` - Name of the mod (required)
- `SourcePath` - Path to downloaded mod files (required)

**Example:**
```batch
install-mod-windows.bat "The Great War" "C:\Downloads\The Great War 6.2"
```

**What it does:**
1. Validates source path exists
2. Auto-detects game installation
3. Creates backup of existing mod (if present)
4. Copies mod files to correct location
5. Validates installation with 6 tests
6. Generates detailed log file

### Windows Test Suite

**Syntax:**
```powershell
.\test-mod-installation.ps1 -ModName "ModName" [-GameRoot "Path"] [-Verbose] [-CI]
```

**Parameters:**
- `-ModName` - Name of the mod (required)
- `-GameRoot` - Game installation path (auto-detected if not specified)
- `-Verbose` - Enable detailed output
- `-CI` - CI/CD mode (exit codes only)

**Examples:**
```powershell
# Basic test
.\test-mod-installation.ps1 -ModName "The Great War"

# With verbose output
.\test-mod-installation.ps1 -ModName "The Great War" -Verbose

# CI/CD mode
.\test-mod-installation.ps1 -ModName "The Great War" -CI
```

**Tests performed:**
1. Directory Structure Validation
2. File Count Validation
3. Pack File Validation
4. Pack File Integrity Check
5. Launcher Validation
6. Data Folder Structure
7. Common Mod File Types
8. File Permissions Check
9. Mod Configuration Files
10. Directory Size Check

### Linux Installation Script

**Syntax:**
```bash
./install-mod-linux.sh "ModName" "SourcePath"
```

**Parameters:**
- `ModName` - Name of the mod (required)
- `SourcePath` - Path to downloaded mod files (required)

**Example:**
```bash
./install-mod-linux.sh "The Great War" "~/Downloads/The Great War 6.2"
```

**What it does:**
1. Validates source path exists
2. Auto-detects Steam installation
3. Creates backup of existing mod (if present)
4. Copies mod files to correct location
5. Sets proper file permissions
6. Validates installation with 8 tests
7. Generates detailed log file

### Linux Test Suite

**Syntax:**
```bash
./test-mod-installation.sh -m "ModName" [-g "GameRoot"] [-v] [--ci]
```

**Parameters:**
- `-m, --mod` - Name of the mod (required)
- `-g, --game-root` - Game installation path (auto-detected if not specified)
- `-v, --verbose` - Enable detailed output
- `--ci` - CI/CD mode (exit codes only)
- `-h, --help` - Show help message

**Examples:**
```bash
# Basic test
./test-mod-installation.sh -m "The Great War"

# With verbose output
./test-mod-installation.sh -m "The Great War" -v

# CI/CD mode
./test-mod-installation.sh -m "The Great War" --ci

# Custom game path
./test-mod-installation.sh -m "The Great War" -g "$HOME/.steam/steam/steamapps/common/Napoleon Total War"
```

## Detected Installation Paths

### Windows

The scripts automatically search for the game in these locations:

- `C:\Program Files (x86)\Steam\steamapps\common\Napoleon Total War\` (Steam)
- `C:\Program Files\Steam\steamapps\common\Napoleon Total War\` (Steam)
- `C:\Program Files (x86)\Napoleon Total War\` (Non-Steam)
- `C:\Program Files\Napoleon Total War\` (Non-Steam)

### Linux

The scripts automatically search for the game in these locations:

- `~/.local/share/Steam/steamapps/common/Napoleon Total War/` (Steam)
- `~/.steam/steam/steamapps/common/Napoleon Total War/` (Steam)
- `~/.steam/steamapps/common/Napoleon Total War/` (Steam)
- `~/.var/app/com.valvesoftware.Steam/.local/share/Steam/steamapps/common/Napoleon Total War/` (Flatpak)
- `/opt/napoleon-total-war/` (Non-Steam)
- `/usr/local/games/napoleon-total-war/` (Non-Steam)

## Mod Structure

Mods should follow this structure:

```
[Mod Source]/
└── [ModName]/
    ├── [mod_main].pack
    ├── [mod_media].pack
    ├── launcher.exe (optional)
    ├── user.script (optional)
    └── [subfolders]/
        ├── ww1_main/
        ├── textures/
        ├── models/
        └── scripts/
```

The installation scripts handle different mod structures:
- Mods with a top-level folder named after the mod
- Mods with a `data/[ModName]` structure
- Flat mod structures

## Testing

### Test Coverage

The test suite performs 10 comprehensive validation tests:

1. **Directory Structure** - Validates mod directory and subdirectories exist
2. **File Count** - Ensures files were actually copied
3. **Pack Files** - Checks for .pack files (common mod format)
4. **Pack File Integrity** - Validates pack files are readable and not corrupted
5. **Launcher** - Checks for launcher.exe if included
6. **Data Folder** - Validates data subfolder structure
7. **Common File Types** - Checks for typical mod file extensions
8. **File Permissions** - Ensures files are readable (Linux)
9. **Configuration Files** - Looks for mod configuration files
10. **Directory Size** - Validates mod has actual content

### Test Results

Tests generate:
- **Console output** with color-coded results
- **Log files** with detailed information
- **Test reports** saved to temp directory

**Exit codes:**
- `0` - All tests passed (success)
- `1` - Some tests failed (failure)

### CI/CD Integration

Both test suites support CI/CD mode:

**Windows:**
```powershell
.\test-mod-installation.ps1 -ModName "MyMod" -CI
```

**Linux:**
```bash
./test-mod-installation.sh -m "MyMod" --ci
```

In CI mode:
- Minimal output
- Exit code 0 on success
- Exit code 1 on failure
- Reports saved for review

## Troubleshooting

### Common Issues

#### Game Not Detected

**Windows:**
- Ensure game is installed via Steam
- Check if game runs normally
- Verify Steam installation is in default location

**Linux:**
- Run `steam` to ensure it's initialized
- Check if game is installed: `ls ~/.local/share/Steam/steamapps/common/`
- For Flatpak: `flatpak list | grep steam`

#### Mod Installation Fails

**Possible causes:**
- Source path incorrect or doesn't exist
- Insufficient permissions
- Antivirus blocking file operations
- Game running during installation

**Solutions:**
1. Verify source path: `dir "C:\Path\To\Mod"` or `ls ~/Path/To/Mod`
2. Run as administrator (Windows) or check permissions (Linux)
3. Temporarily disable antivirus
4. Close game completely before installing

#### Tests Fail After Installation

**Common failures:**

**Test 1 (Directory Structure) fails:**
- Mod directory not created
- Check log file for copy errors
- Manually verify: `ls [GamePath]/data/[ModName]/`

**Test 3 (Pack Files) fails:**
- Mod may not use .pack files
- Some mods use different structure
- Check mod documentation

**Test 4 (Pack File Integrity) fails:**
- Downloaded files may be corrupted
- Re-download mod files
- Check disk for errors

**Test 8 (File Permissions) fails (Linux):**
- Run: `chmod -R 755 [GamePath]/data/[ModName]`

#### Mod Doesn't Appear in Game

**Solutions:**
1. Verify mod is in correct location: `[Game]/data/[ModName]/`
2. Check mod compatibility with game version
3. Enable mod through launcher or mod manager
4. Check for required load order
5. Verify no conflicts with other mods

### Log Files

**Installation logs:**
- **Windows:** `%TEMP%\ntw_mod_install_YYYYMMDD.log`
- **Linux:** `/tmp/ntw_mod_install_YYYYMMDD_HHMMSS.log`

**Test logs:**
- **Windows:** `%TEMP%\ntw_mod_test_YYYYMMDD_HHMMSS.log`
- **Linux:** `/tmp/ntw_mod_test_YYYYMMDD_HHMMSS.log`

**Test reports:**
- **Windows:** `%TEMP%\ntw_mod_test_report_YYYYMMDD_HHMMSS.txt`
- **Linux:** `/tmp/ntw_mod_test_report_YYYYMMDD_HHMMSS.txt`

### Getting Help

If issues persist:

1. **Check mod documentation** - Some mods have specific requirements
2. **Verify game version** - Ensure mod is compatible
3. **Check Total War Center forums** - Community support
4. **Review mod comments** - Other users may have same issues

## Advanced Usage

### Custom Installation Path

If auto-detection fails, specify the game path manually:

**Windows:**
```batch
# Install
install-mod-windows.bat "ModName" "SourcePath"

# Test with custom path
.\test-mod-installation.ps1 -ModName "ModName" -GameRoot "D:\Games\Napoleon Total War"
```

**Linux:**
```bash
# Install (edit script or set GAME_ROOT manually)
GAME_ROOT="/custom/path" ./install-mod-linux.sh "ModName" "SourcePath"

# Test with custom path
./test-mod-installation.sh -m "ModName" -g "/custom/path"
```

### Backup Management

Backups are automatically created with timestamps:

**Windows:**
```
[Game]\data\[ModName]_backup_YYYYMMDD_HHMMSS\
```

**Linux:**
```
[Game]/data/[ModName]_backup_YYYYMMDD_HHMMSS/
```

To restore a backup:
```bash
# Linux
mv [Game]/data/[ModName] [Game]/data/[ModName]_broken
mv [Game]/data/[ModName]_backup_* [Game]/data/[ModName]

# Windows (PowerShell)
Move-Item "[Game]\data\[ModName]" "[Game]\data\[ModName]_broken"
Move-Item "[Game]\data\[ModName]_backup_*" "[Game]\data\[ModName]"
```

### Multiple Mod Installation

Install mods one at a time and test each:

```bash
# Install first mod
./install-mod-linux.sh "Mod1" "Source1"
./test-mod-installation.sh -m "Mod1"

# Install second mod
./install-mod-linux.sh "Mod2" "Source2"
./test-mod-installation.sh -m "Mod2"
```

**Note:** Some mods may conflict. Test each mod individually before using together.

## Mod Compatibility

### Known Compatible Mods

- The Great War Mod 6.2 (WW1 total conversion)
- Napoleon All in One Mod
- Napoleon Order of War
- Most .pack-based mods

### Mod Managers

For complex mod setups, consider using:

- **Total War Mod Manager** (Windows) - https://sourceforge.net/projects/twmodmanager/
- **RPFM** (Rusted PackFile Manager) - https://github.com/twwstats/rpfm
- **JSGME** (Generic Mod Manager) - Cross-platform

## Contributing

To contribute improvements:

1. Fork the repository
2. Create a feature branch
3. Test changes thoroughly
4. Submit a pull request

## License

This project is provided as-is for educational and personal use.

## Credits

Created for Total War: Napoleon modding community.

**Special thanks to:**
- Total War Center community
- RPFM developers
- All mod creators

## Resources

- **Total War Center:** https://www.twcenter.net/
- **Total War Modding Wiki:** https://tw-modding.com/
- **ModDB Napoleon Mods:** https://www.moddb.com/mods/napoleon-total-war
- **RPFM Documentation:** https://frodo45127.github.io/rpfm/

## Support

For mod-specific issues, contact the mod creator.

For script issues, check:
1. Log files in temp directory
2. Game installation integrity
3. Mod compatibility
4. Community forums

---

**Happy Modding!**

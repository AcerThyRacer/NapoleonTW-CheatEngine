# Napoleon Total War Cheat Engine - Changelog

## Version 1.0.0 (Initial Release)

### Features

#### Memory Scanner
- ✅ Cross-platform memory scanning (Windows/Linux)
- ✅ Exact value scanning
- ✅ Increased/decreased value scanning
- ✅ Support for multiple data types (INT_8, INT_16, INT_32, INT_64, FLOAT, DOUBLE)
- ✅ Real-time memory editing
- ✅ Address freezing capability
- ✅ Scan result management

#### File Editor
- ✅ ESF save game parser and editor
- ✅ XML export/import for ESF files
- ✅ Lua script editor (scripting.lua)
- ✅ Configuration editor (preferences.script)
- ✅ Quick edit presets
- ✅ Automatic backup creation

#### Pack File Modder
- ✅ .pack archive parser (v3 and v4 formats)
- ✅ File extraction from packs
- ✅ Database table editor (TSV format)
- ✅ Mod pack creator
- ✅ Directory batch import

#### Runtime Trainer
- ✅ Hotkey-activated cheats
- ✅ Campaign mode cheats:
  - Infinite Gold (Shift+F2)
  - Unlimited Movement (Shift+F3)
  - Instant Construction (Shift+F4)
  - Fast Research (Shift+F5)
- ✅ Battle mode cheats:
  - God Mode (Ctrl+F1)
  - Unlimited Ammo (Ctrl+F2)
  - High Morale (Ctrl+F3)
  - Infinite Stamina (Ctrl+F4)
  - One-Hit Kill (Ctrl+F5)
  - Super Speed (Ctrl+F6)
- ✅ Cheat status overlay (PyQt6)
- ✅ Toggle activation/deactivation

#### GUI
- ✅ PyQt6-based interface
- ✅ Dark theme
- ✅ Memory Scanner tab
- ✅ File Editor tab with sub-tabs
- ✅ Trainer tab with cheat checkboxes
- ✅ Settings tab with path configuration
- ✅ Auto-detection of game paths
- ✅ Status bar with real-time updates

#### Cross-Platform Support
- ✅ Windows support (native)
- ✅ Linux support (native Feral version)
- ✅ Proton/Wine compatibility
- ✅ Automatic path detection for both platforms
- ✅ Platform-aware process detection

#### Utilities
- ✅ Save game location auto-detection
- ✅ Script directory detection
- ✅ Game installation path detection
- ✅ Backup system with timestamps
- ✅ File validation

### Technical Implementation

#### Architecture
- Modular design with separation of concerns
- Event-driven hotkey system
- Background threading for memory operations
- Cross-platform abstractions

#### Dependencies
- PyMemoryEditor: Memory scanning
- pynput: Hotkey management
- PyQt6: GUI framework
- psutil: Process detection
- PyInstaller: Build system

#### Testing
- Unit tests for all modules
- Integration tests
- Test coverage reporting

### Documentation
- ✅ README.md with installation instructions
- ✅ USER_GUIDE.md with detailed usage
- ✅ DEVELOPER_GUIDE.md for contributors
- ✅ Inline code documentation
- ✅ API reference

### Known Issues

1. **ESF Parser Limitations**
   - Full ESF format specification not publicly available
   - Some complex saves may not parse correctly
   - Workaround: Use ESFviaXML tool for complex edits

2. **Memory Scanning on Linux**
   - May require additional permissions
   - Proton/Wine memory layout differs from native Windows
   - Workaround: Run as regular user (usually sufficient)

3. **Hotkey Conflicts**
   - Some hotkeys may conflict with in-game shortcuts
   - Discord overlay and other software may intercept hotkeys
   - Workaround: Customize hotkeys in trainer configuration

4. **GUI Performance**
   - Large scan results may slow down GUI
   - Workaround: Filter results or use CLI mode

### Platform-Specific Notes

#### Windows
- Tested on Windows 10/11
- Requires administrator privileges for some operations
- PyInstaller creates standalone .exe

#### Linux
- Tested on Ubuntu 22.04/24.04
- Works with Feral Interactive native version
- Proton compatibility verified
- AppImage builds available

### Compatibility

**Game Versions:**
- ✅ Napoleon Total War (Original)
- ✅ Napoleon Total War: Definitive Edition
- ✅ Napoleon Total War: Imperial Edition
- ✅ Feral Interactive Linux Version
- ✅ Steam Version (Windows/Linux)

**Python Versions:**
- ✅ Python 3.10
- ✅ Python 3.11
- ✅ Python 3.12

**Operating Systems:**
- ✅ Windows 10/11 (64-bit)
- ✅ Ubuntu 22.04/24.04
- ✅ Fedora 38+
- ✅ Arch Linux
- ✅ Debian 11+

### Build Instructions

#### Windows
```bash
build.bat
```
Output: `dist/NapoleonCheatEngine.exe`

#### Linux
```bash
build.sh
```
Output: `dist/NapoleonCheatEngine`

### Future Enhancements (Planned)

#### v1.1.0
- [ ] Enhanced ESF parser with full format support
- [ ] Pointer scanning for dynamic addresses
- [ ] Cheat table import/export (Cheat Engine format)
- [ ] Auto-update checker
- [ ] Multi-language support

#### v1.2.0
- [ ] Battle script editor integration
- [ ] Unit variant editor
- [ ] Texture modding support
- [ ] Mod manager with load order
- [ ] Community mod browser

#### v1.3.0
- [ ] Networked multiplayer trainer (sync cheats)
- [ ] Replay editor
- [ ] Scenario creator
- [ ] Advanced database table editor with GUI

### Credits

**Development:**
- Core development team
- Community contributors

**Special Thanks:**
- Total War Center community
- FearLess Cheat Engine forums
- Creative Assembly
- Feral Interactive

**Tools Used:**
- PyMemoryEditor by JeanExtreme002
- Pack File Manager by TWC community
- PyQt6 by Riverbank Computing

### License

Educational purposes only. Use responsibly in single-player mode.

### Support

- Documentation: See `docs/` folder
- Issues: GitHub Issues
- Community: Total War Center forums

---

**Release Date:** March 2026

**Version:** 1.0.0

**Build:** stable

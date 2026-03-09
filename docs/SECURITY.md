# Security Documentation

This document outlines the security measures, best practices, and known limitations of the Napoleon Total War Cheat Engine.

## Security Measures Implemented

### 1. Input Validation

#### Path Traversal Protection
All file operations validate paths to prevent directory traversal attacks:

```python
def _validate_path(self, file_path: str) -> Path:
    path = Path(file_path).resolve()
    
    # If base directory is set, ensure path is within it
    if self.base_directory:
        base_resolved = self.base_directory.resolve()
        try:
            path.relative_to(base_resolved)
        except ValueError:
            raise SecurityError(
                f"Path traversal detected: {file_path} is outside base directory"
            )
    
    return path
```

**Protected Components:**
- ESF Editor (`src/files/esf_editor.py`)
- Pack Parser (`src/pack/pack_parser.py`)
- Script Editor (`src/files/script_editor.py`)
- Config Editor (`src/files/config_editor.py`)

#### File Size Limits
Maximum file sizes are enforced to prevent memory exhaustion:

```python
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100 MB
MAX_NAME_LENGTH = 10000
MAX_STRING_LENGTH = 1000000
MAX_ARRAY_SIZE = 100000
```

### 2. Backup and Recovery

#### Verified Backups
Before modifying any file, a backup is created and **verified**:

```python
def create_backup(file_path: Path, backup_dir: Optional[Path] = None) -> Path:
    # ... copy file ...
    
    # VERIFY backup was written successfully
    if not backup_path.exists():
        raise IOError("Backup file was not created")
    
    backup_size = backup_path.stat().st_size
    if backup_size != original_size:
        raise IOError("Backup file size mismatch")
    
    return backup_path
```

**Backup Features:**
- Automatic backup before all file modifications
- Size verification after copy
- Timestamped backup files
- Configurable backup directory

**How to Restore:**
```bash
# Backups are stored in:
# - Windows: %APPDATA%\The Creative Assembly\Napoleon\backups\
# - Linux: ~/.local/share/Total War: NAPOLEON/backups/

# Restore manually:
cp backups/campaign.esf.backup.1234567890 campaign.esf
```

### 3. Error Handling

#### Hotkey System Recovery
The hotkey system includes automatic error recovery:

- Error counting with threshold detection
- Automatic listener restart on failure
- Cooldown period to prevent restart loops
- Status callbacks for UI notification

```python
def _handle_error(self, error_msg: str) -> None:
    self.error_count += 1
    
    if self.error_count >= self.max_errors_before_restart:
        if time_since_last > self.error_cooldown:
            self._attempt_reconnect()
            self.error_count = 0
```

#### Thread Safety
All shared state is protected with locks:

```python
with self._lock:
    # Critical section
    self._extraction_cache[file_path] = data
```

### 4. Memory Safety

#### Bounds Checking
All binary parsing includes bounds validation:

```python
# Sanity check on name length
if name_len > 10000 or offset + name_len > len(data):
    offset = self._find_next_valid_type(data, offset)
    if offset == -1:
        break
```

#### Region Validation
Memory scanning validates regions before access:

```python
def _get_readable_memory_regions(self) -> List[Dict]:
    # Only scan readable regions
    if 'r' in m.perms.lower() if hasattr(m, 'perms') else True:
        regions.append({...})
```

## Safe Usage Guidelines

### DO ✅

1. **Always work on copies** of save games when possible
2. **Verify backups** exist before testing cheats
3. **Use the built-in backup system** (enabled by default)
4. **Test cheats in custom battles** before campaign use
5. **Keep original saves** in a separate backup location
6. **Use path validation** by setting base directories

### DON'T ❌

1. **Don't modify multiplayer saves** - may result in bans
2. **Don't use on Steam Cloud saves** without local backup
3. **Don't bypass path validation** - it's there for safety
4. **Don't edit files while game is running** - can cause corruption
5. **Don't use with other mods** without testing compatibility
6. **Don't share modified saves** in multiplayer communities

## Known Limitations

### 1. ESF Parser Limitations

**Issue**: The ESF format is partially documented and may have encryption.

**Current State:**
- Basic binary parsing implemented
- Supports common node types (blocks, integers, floats, strings, booleans, arrays)
- May not handle all ESF variants

**Workaround:**
- Use official ESFviaXML tool for complex saves
- Test parsed saves in-game before relying on them
- Report parsing failures with sample files

### 2. Memory Pattern Stability

**Issue**: Memory addresses change between game versions.

**Current State:**
- Signature scanning helps find stable patterns
- Not all cheats have persistent patterns
- May require re-scanning after game updates

**Mitigation:**
- Use the parallel scanner for faster re-scanning
- Save scan results for common values
- Report working patterns for your game version

### 3. Hotkey Limitations on Linux/Proton

**Issue**: Global hotkeys may not work reliably under Proton/Wine.

**Current State:**
- Works natively on Windows and Linux
- Limited functionality under Proton
- Auto-recovery helps but may not fix all issues

**Workaround:**
- Use trainer mode in separate terminal
- Use GUI hotkey buttons instead of global hotkeys
- Run native Linux version if available

### 4. Path Validation Bypass

**Issue**: Base directory validation is optional.

**Current State:**
- Validation only active if `base_directory` is set
- Default is `None` (no validation)

**Recommendation:**
```python
# Enable validation in your code:
editor = ESFEditor(base_directory=Path('/safe/directory'))
```

## Security Checklist

Before deployment or use, verify:

- [ ] All file inputs are validated
- [ ] Backups are created before modifications
- [ ] Backups are verified after creation
- [ ] Error handling is in place for all operations
- [ ] Thread locks protect shared state
- [ ] Memory bounds are checked before access
- [ ] Path traversal protection is enabled
- [ ] File size limits are enforced
- [ ] Hotkey recovery is configured
- [ ] Original saves are backed up externally

## Reporting Security Issues

If you discover a security vulnerability:

1. **Do not** disclose publicly until fixed
2. Email: [security contact]
3. Include:
   - Description of the issue
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if any)

## Incident Response

### If a Backup Fails

1. Stop the operation immediately
2. Do not proceed with file modification
3. Check disk space and permissions
4. Try manual backup copy
5. If manual backup succeeds, report the issue

### If File Corruption Occurs

1. Restore from verified backup
2. If backup also corrupted, restore from external backup
3. Report the issue with:
   - Which file was corrupted
   - What operation was being performed
   - Error messages received

### If Hotkeys Malfunction

1. Disable hotkey system
2. Check for conflicting applications
3. Restart the trainer
4. If issue persists, use GUI controls only

## Version History

### v1.0.0 (Current)
- Path traversal protection added
- Backup verification implemented
- Hotkey error recovery added
- Thread safety improvements
- Memory bounds checking
- File size limits enforced

## References

- [OWASP Input Validation Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Input_Validation_Cheat_Sheet.html)
- [Python Security Best Practices](https://docs.python.org/3/library/security.html)
- [Total War Modding Guidelines](https://www.totalwar.com/modding/)

## Disclaimer

This software is for **single-player educational use only**. Using cheats in multiplayer games may result in bans and is against the terms of service of most gaming platforms.

**Use at your own risk.** Always maintain external backups of important save files.

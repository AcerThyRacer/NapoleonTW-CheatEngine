"""
Cross-platform utilities for Napoleon Total War Cheat Engine.
Handles platform detection, path normalization, and OS-specific operations.
"""

import os
import sys
import platform
import logging
from pathlib import Path
from typing import Optional, Dict, Any

logger = logging.getLogger('napoleon.utils.platform')


def get_platform() -> str:
    """
    Detect the current platform.
    
    Returns:
        str: 'windows', 'linux', or 'macos'
    """
    if sys.platform.startswith('win'):
        return 'windows'
    elif sys.platform.startswith('linux'):
        return 'linux'
    elif sys.platform == 'darwin':
        return 'macos'
    return 'unknown'


def is_proton() -> bool:
    """
    Check if running under Proton/Wine on Linux.
    
    Returns:
        bool: True if running under Proton/Wine
    """
    if get_platform() != 'linux':
        return False
    
    # Check for Proton/Wine environment variables
    proton_vars = [
        'STEAM_COMPAT_CLIENT_INSTALL_PATH',
        'STEAM_COMPAT_DATA_PATH',
        'WINEPREFIX',
        'PROTON_VERSION'
    ]
    
    return any(var in os.environ for var in proton_vars)


def get_steam_path() -> Optional[Path]:
    """
    Get the Steam installation path for the current platform.
    
    Returns:
        Optional[Path]: Steam path or None if not found
    """
    platform_name = get_platform()
    
    if platform_name == 'windows':
        # Default Steam installation path
        default_paths = [
            Path('C:/Program Files (x86)/Steam'),
            Path('C:/Program Files/Steam'),
            Path(os.environ.get('PROGRAMFILES(X86)', 'C:/Program Files (x86)')) / 'Steam',
        ]
        
        for path in default_paths:
            if path.exists():
                return path
        
        # Check registry (Windows only)
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r'SOFTWARE\Valve\Steam') as key:
                steam_path = winreg.QueryValueEx(key, 'SteamPath')[0]
                return Path(steam_path)
        except (ImportError, FileNotFoundError, OSError):
            pass
            
    elif platform_name == 'linux':
        # Common Linux Steam paths
        linux_paths = [
            Path.home() / '.steam' / 'steam',
            Path.home() / '.steam' / 'steamapps',
            Path.home() / '.local' / 'share' / 'Steam',
            Path.home() / '.var' / 'app' / 'com.valvesoftware.Steam' / '.local' / 'share' / 'Steam',
            Path('/run/host/home') / os.environ.get('USER', '') / '.local' / 'share' / 'Steam',
            Path('/usr/games/steam'),
        ]
        
        for path in linux_paths:
            if path.exists():
                return path
    
    return None


def get_napoleon_install_path() -> Optional[Path]:
    """
    Get the Napoleon Total War installation path.
    
    Returns:
        Optional[Path]: Game installation path or None if not found
    """
    steam_path = get_steam_path()
    if not steam_path:
        return None
    
    platform_name = get_platform()
    
    if platform_name == 'windows':
        # Steam library paths
        library_paths = [
            steam_path / 'steamapps' / 'common' / 'Total War NAPOLEON',
            steam_path / 'steamapps' / 'common' / 'Napoleon Total War',
        ]
        
        for path in library_paths:
            if path.exists():
                return path
                
    elif platform_name == 'linux':
        # Feral Interactive native version
        feral_path = Path.home() / '.local' / 'share' / 'feral-interactive' / 'Napoleon'
        if feral_path.exists():
            return feral_path
        
        # Steam Linux version
        linux_paths = [
            steam_path / 'steamapps' / 'common' / 'Total War NAPOLEON',
            steam_path / 'steamapps' / 'common' / 'Napoleon Total War',
            Path.home() / '.steam' / 'steamapps' / 'common' / 'Total War NAPOLEON',
            Path.home() / '.steam' / 'steamapps' / 'common' / 'Napoleon Total War',
        ]
        
        for path in linux_paths:
            if path.exists():
                return path
    
    return None


def get_save_game_directory() -> Optional[Path]:
    """
    Get the save game directory for Napoleon Total War.
    
    Returns:
        Optional[Path]: Save game directory or None if not found
    """
    platform_name = get_platform()
    
    if platform_name == 'windows':
        # Windows save locations
        appdata = os.environ.get('APPDATA', '')
        if appdata:
            save_path = Path(appdata) / 'The Creative Assembly' / 'Napoleon' / 'save_games'
            if save_path.exists():
                return save_path
        
        # Steam Cloud saves
        steam_path = get_steam_path()
        if steam_path:
            # Try to find Steam userdata
            userdata_path = steam_path / 'userdata'
            if userdata_path.exists():
                # Look for Napoleon's AppID (34030)
                for user_dir in userdata_path.iterdir():
                    if user_dir.is_dir():
                        ntw_save = user_dir / '34030' / 'remote' / 'save_games'
                        if ntw_save.exists():
                            return ntw_save
                            
    elif platform_name == 'linux':
        # Feral Interactive native version
        feral_save = Path.home() / '.local' / 'share' / 'Total War: NAPOLEON' / 'save_games'
        if feral_save.exists():
            return feral_save
        
        # Steam Proton version
        steam_path = get_steam_path()
        if steam_path:
            proton_save = (
                steam_path / 'steamapps' / 'compatdata' / '34030' / 'pfx' / 
                'drive_c' / 'users' / 'steamuser' / 'AppData' / 'Roaming' / 
                'The Creative Assembly' / 'Napoleon' / 'save_games'
            )
            if proton_save.exists():
                return proton_save
            
            # Alternative Proton path
            alt_proton_save = (
                Path.home() / '.steam' / 'steamapps' / 'compatdata' / '34030' / 'pfx' /
                'drive_c' / 'users' / 'steamuser' / 'AppData' / 'Roaming' /
                'The Creative Assembly' / 'Napoleon' / 'save_games'
            )
            if alt_proton_save.exists():
                return alt_proton_save
    
    return None


def get_scripts_directory() -> Optional[Path]:
    """
    Get the scripts/configuration directory.
    
    Returns:
        Optional[Path]: Scripts directory or None if not found
    """
    platform_name = get_platform()
    
    if platform_name == 'windows':
        appdata = os.environ.get('APPDATA', '')
        if appdata:
            scripts_path = Path(appdata) / 'The Creative Assembly' / 'Napoleon' / 'scripts'
            if scripts_path.exists():
                return scripts_path
                
    elif platform_name == 'linux':
        # Feral Interactive
        feral_scripts = Path.home() / '.local' / 'share' / 'Total War: NAPOLEON' / 'scripts'
        if feral_scripts.exists():
            return feral_scripts
        
        # Steam Proton
        steam_path = get_steam_path()
        if steam_path:
            proton_scripts = (
                steam_path / 'steamapps' / 'compatdata' / '34030' / 'pfx' /
                'drive_c' / 'users' / 'steamuser' / 'AppData' / 'Roaming' /
                'The Creative Assembly' / 'Napoleon' / 'scripts'
            )
            if proton_scripts.exists():
                return proton_scripts
    
    return None


def get_game_data_path() -> Optional[Path]:
    """
    Get the game data directory containing .pack files and scripts.
    
    Returns:
        Optional[Path]: Data directory or None if not found
    """
    install_path = get_napoleon_install_path()
    if not install_path:
        return None
    
    platform_name = get_platform()
    
    if platform_name == 'windows':
        data_path = install_path / 'data'
        if data_path.exists():
            return data_path
            
    elif platform_name == 'linux':
        # Feral Interactive
        data_path = install_path / 'data'
        if data_path.exists():
            return data_path
    
    return None


def normalize_path(path: str) -> Path:
    """
    Normalize a path for the current platform.
    
    Args:
        path: Path string (can be Windows or Unix format)
        
    Returns:
        Path: Normalized Path object
    """
    # Handle Windows paths on Linux (for Proton)
    if get_platform() == 'linux':
        # Convert Windows-style paths to Unix
        if path.startswith('C:\\') or path.startswith('c:\\'):
            path = path[3:].replace('\\', '/')
            return Path('/mnt/c') / path
        elif '\\' in path:
            path = path.replace('\\', '/')
    
    return Path(path)


def check_memory_access_permissions() -> Dict[str, Any]:
    """Check Linux memory access prerequisites for the current user."""
    result = {
        'can_read': False,
        'can_write': False,
        'is_root': hasattr(os, 'geteuid') and os.geteuid() == 0,
        'ptrace_scope': None,
        'recommendations': [],
    }

    if get_platform() != 'linux':
        return result

    try:
        with open('/proc/sys/kernel/yama/ptrace_scope', 'r') as handle:
            ptrace_scope = int(handle.read().strip())
            result['ptrace_scope'] = ptrace_scope
            if ptrace_scope > 0:
                result['recommendations'].append(
                    "Linux ptrace restrictions are enabled; use sudo, CAP_SYS_PTRACE, or temporarily set kernel.yama.ptrace_scope=0 on a dedicated gaming system."
                )
    except (FileNotFoundError, PermissionError, ValueError):
        pass

    mem_path = f'/proc/{os.getpid()}/mem'
    try:
        with open(mem_path, 'rb'):
            result['can_read'] = True
    except PermissionError:
        result['recommendations'].append(
            "Current user cannot read /proc/<pid>/mem; run as the same user as the game, or use sudo/CAP_SYS_PTRACE."
        )

    result['can_write'] = result['can_read'] and result['is_root']
    if not result['can_write']:
        result['recommendations'].append(
            "Write access usually requires sudo or CAP_SYS_PTRACE on Linux."
        )

    return result


def detect_display_server() -> str:
    """Detect the active Linux display server."""
    if get_platform() != 'linux':
        return 'N/A'

    session_type = os.environ.get('XDG_SESSION_TYPE', '').lower()
    wayland_display = os.environ.get('WAYLAND_DISPLAY', '')
    display = os.environ.get('DISPLAY', '')

    if 'wayland' in session_type or wayland_display:
        return 'wayland'
    if 'x11' in session_type or display:
        return 'x11'
    return 'unknown'


def get_hotkey_compatibility_warning() -> Optional[str]:
    """Return a warning when the current Linux session may block global hotkeys."""
    if detect_display_server() == 'wayland':
        return (
            "⚠️ Wayland detected: global hotkeys may be limited. "
            "Use an X11 session or XWayland for the most reliable trainer hotkeys."
        )
    return None


def create_backup(file_path: Path, backup_dir: Optional[Path] = None) -> Path:
    """
    Create a backup of a file with verification.
    
    Args:
        file_path: Path to the file to backup
        backup_dir: Optional directory to store backup (default: same directory)
        
    Returns:
        Path: Path to the backup file
        
    Raises:
        IOError: If backup verification fails
    """
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    
    if backup_dir is None:
        backup_dir = file_path.parent / 'backups'
    
    backup_dir.mkdir(parents=True, exist_ok=True)
    
    # Create timestamped backup with human-readable, always-unique name
    from datetime import datetime
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_name = f"{file_path.name}.backup.{timestamp}"
    backup_path = backup_dir / backup_name
    
    # If somehow a backup with this exact second exists, add a counter
    counter = 1
    while backup_path.exists():
        backup_name = f"{file_path.name}.backup.{timestamp}_{counter}"
        backup_path = backup_dir / backup_name
        counter += 1
    
    # Get original file size for verification
    original_size = file_path.stat().st_size
    
    # Copy file
    import shutil
    shutil.copy2(file_path, backup_path)
    
    # VERIFY backup was written successfully
    if not backup_path.exists():
        raise IOError("Backup file was not created")
    
    backup_size = backup_path.stat().st_size
    if backup_size != original_size:
        raise IOError(
            f"Backup file size mismatch: original={original_size:,} bytes, "
            f"backup={backup_size:,} bytes"
        )
    
    return backup_path


def get_process_name() -> str:
    """
    Get the Napoleon Total War process name for the current platform.
    
    Returns:
        str: Process name
    """
    platform_name = get_platform()
    
    if platform_name == 'windows':
        return 'napoleon.exe'
    elif platform_name == 'linux':
        if is_proton():
            return 'napoleon.exe'  # Proton runs the Windows binary
        return 'napoleon'  # Native Linux (Feral Interactive)
    return 'napoleon.exe'


def get_all_possible_process_names() -> list:
    """
    Get all possible process names for Napoleon Total War.
    
    Returns:
        list: List of possible process names
    """
    return [
        'napoleon.exe',           # Windows / Proton
        'Napoleon.exe',           # Windows (case variant)
        'napoleon',               # Linux native (Feral Interactive)
        'Napoleon',               # Linux native (case variant)
        'NapoleonTW',             # Linux alternative
        'TotalWarNapoleon',       # Alternative Linux name
        'Napoleon Total War',     # Display name variant
        'napoleon_total_war',     # Snake case variant
    ]

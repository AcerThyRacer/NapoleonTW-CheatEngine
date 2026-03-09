"""
Configuration file editor for Napoleon Total War.
Handles preferences.script and other configuration files.
"""

import re
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass

from src.utils import create_backup, get_scripts_directory


@dataclass
class ConfigOption:
    """Represents a configuration option."""
    name: str
    value: Any
    value_type: str
    description: str
    valid_range: Optional[Tuple] = None


class ConfigEditor:
    """
    Editor for Napoleon Total War configuration files.
    """
    
    # Known configuration options
    KNOWN_OPTIONS = {
        'battle_time_limit': ConfigOption(
            name='battle_time_limit',
            value=-1,
            value_type='int',
            description='Battle time limit in seconds (-1 for unlimited)',
            valid_range=(-1, 99999)
        ),
        'campaign_unit_multiplier': ConfigOption(
            name='campaign_unit_multiplier',
            value=1.0,
            value_type='float',
            description='Multiplier for unit sizes',
            valid_range=(0.5, 5.0)
        ),
        'default_camera_type': ConfigOption(
            name='default_camera_type',
            value=0,
            value_type='int',
            description='Camera type (0=Total War, 1=RTS, 2=Debug/Free roam)',
            valid_range=(0, 2)
        ),
        'gfx_video_memory': ConfigOption(
            name='gfx_video_memory',
            value=2147483648,
            value_type='int',
            description='Video memory in bytes',
            valid_range=(0, 4294967295)
        ),
        'gfx_detail_level': ConfigOption(
            name='gfx_detail_level',
            value='ultra',
            value_type='string',
            description='Graphics detail level',
            valid_range=('low', 'medium', 'high', 'ultra')
        ),
        'resolution_width': ConfigOption(
            name='resolution_width',
            value=1920,
            value_type='int',
            description='Screen width',
            valid_range=(800, 7680)
        ),
        'resolution_height': ConfigOption(
            name='resolution_height',
            value=1080,
            value_type='int',
            description='Screen height',
            valid_range=(600, 4320)
        ),
        'fullscreen': ConfigOption(
            name='fullscreen',
            value=True,
            value_type='bool',
            description='Fullscreen mode',
            valid_range=(False, True)
        ),
        'vsync': ConfigOption(
            name='vsync',
            value=False,
            value_type='bool',
            description='Vertical sync',
            valid_range=(False, True)
        ),
        'campaign_fog_of_war': ConfigOption(
            name='campaign_fog_of_war',
            value=True,
            value_type='bool',
            description='Enable fog of war in campaign',
            valid_range=(False, True)
        ),
    }
    
    def __init__(self):
        """Initialize configuration editor."""
        self.file_path: Optional[Path] = None
        self.content: str = ""
        self.original_content: str = ""
        self.config_values: Dict[str, Any] = {}
        self.modifications: List[str] = []
        
    def load_file(self, file_path: Optional[str] = None) -> bool:
        """
        Load preferences.script file.
        
        Args:
            file_path: Optional path (auto-detect if not provided)
            
        Returns:
            bool: True if loaded successfully
        """
        try:
            if file_path:
                path = Path(file_path)
            else:
                # Auto-detect location
                scripts_dir = get_scripts_directory()
                if not scripts_dir:
                    print("Could not find scripts directory")
                    return False
                path = scripts_dir / 'preferences.script'
            
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    self.content = f.read()
                    self.original_content = self.content
            except FileNotFoundError:
                print(f"File not found: {path}")
                return False
            except PermissionError:
                print(f"Permission denied: {path}")
                return False
            
            self.file_path = path
            
            # Parse configuration values
            self._parse_config()
            
            print(f"Loaded config: {path.name}")
            return True
            
        except Exception as e:
            print(f"Error loading config file: {e}")
            return False
    
    def _parse_config(self) -> None:
        """Parse configuration file into key-value pairs."""
        self.config_values = {}
        
        # Match lines like: key = value
        pattern = r'^\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*=\s*(.+?)\s*$'
        
        for line in self.content.split('\n'):
            match = re.match(pattern, line)
            if match:
                key = match.group(1)
                value_str = match.group(2).strip()
                
                # Parse value based on type
                value = self._parse_value(value_str)
                self.config_values[key] = value
    
    def _parse_value(self, value_str: str) -> Any:
        """Parse a value string into appropriate type."""
        # Boolean
        if value_str.lower() == 'true':
            return True
        elif value_str.lower() == 'false':
            return False
        
        # Integer
        try:
            return int(value_str)
        except ValueError:
            pass
        
        # Float
        try:
            return float(value_str)
        except ValueError:
            pass
        
        # String (remove quotes if present)
        if (value_str.startswith('"') and value_str.endswith('"')) or \
           (value_str.startswith("'") and value_str.endswith("'")):
            return value_str[1:-1]
        
        return value_str
    
    def save_file(self, output_path: Optional[str] = None) -> bool:
        """
        Save the configuration file.
        
        Args:
            output_path: Optional output path (default: overwrite original)
            
        Returns:
            bool: True if saved successfully
        """
        try:
            if output_path:
                path = Path(output_path)
            else:
                if not self.file_path:
                    print("No file path specified")
                    return False
                path = self.file_path
            
            # Create backup before overwriting
            if path.exists() and output_path is None:
                backup_path = create_backup(path)
                print(f"Backup created: {backup_path}")
            
            with open(path, 'w', encoding='utf-8') as f:
                f.write(self.content)
            
            print(f"Config saved: {path}")
            return True
            
        except Exception as e:
            print(f"Error saving config file: {e}")
            return False
    
    def set_value(self, key: str, value: Any) -> bool:
        """
        Set a configuration value.
        
        Args:
            key: Configuration key
            value: Value to set
            
        Returns:
            bool: True if successful
        """
        if key not in self.KNOWN_OPTIONS:
            print(f"Unknown configuration option: {key}")
            # Still allow setting it, but warn
            # return False
        
        # Validate value if we have range info
        config_opt = self.KNOWN_OPTIONS.get(key)
        if config_opt and config_opt.valid_range:
            if not self._validate_value(value, config_opt.valid_range):
                print(f"Value {value} out of valid range: {config_opt.valid_range}")
                return False
        
        # Update in content
        pattern = rf'^(\s*{re.escape(key)}\s*=\s*).+?$'
        replacement = f'\\g<1>{self._format_value(value)}'
        
        new_content = re.sub(pattern, replacement, self.content, flags=re.MULTILINE)
        
        if new_content == self.content:
            # Key doesn't exist, add it
            self.content += f'\n{key} = {self._format_value(value)}'
            print(f"Added new config option: {key} = {value}")
        else:
            self.content = new_content
            print(f"Set {key} = {value}")
        
        # Update parsed values
        self.config_values[key] = value
        self.modifications.append(key)
        
        return True
    
    def get_value(self, key: str, default: Any = None) -> Any:
        """
        Get a configuration value.
        
        Args:
            key: Configuration key
            default: Default value if not found
            
        Returns:
            Any: Configuration value
        """
        return self.config_values.get(key, default)
    
    def _format_value(self, value: Any) -> str:
        """Format a value for the config file."""
        if isinstance(value, bool):
            return 'true' if value else 'false'
        elif isinstance(value, str):
            return f'"{value}"'
        else:
            return str(value)
    
    def _validate_value(self, value: Any, valid_range: Tuple) -> bool:
        """Validate a value against a range."""
        if isinstance(valid_range, tuple) and len(valid_range) == 2:
            if isinstance(value, (int, float)):
                return valid_range[0] <= value <= valid_range[1]
            elif isinstance(value, str):
                return value in valid_range
            elif isinstance(value, bool):
                return value in valid_range
        return True
    
    def reset_to_defaults(self) -> bool:
        """
        Reset all values to defaults.
        
        Returns:
            bool: True if successful
        """
        self.content = self.original_content
        self._parse_config()
        self.modifications = []
        print("Configuration reset to defaults")
        return True
    
    def apply_preset(self, preset_name: str) -> bool:
        """
        Apply a configuration preset.
        
        Args:
            preset_name: Name of preset ('cheats', 'performance', 'quality', etc.)
            
        Returns:
            bool: True if successful
        """
        presets = {
            'cheats': {
                'battle_time_limit': -1,
                'campaign_unit_multiplier': 2.5,
                'default_camera_type': 2,
                'campaign_fog_of_war': False,
            },
            'performance': {
                'gfx_detail_level': 'low',
                'gfx_video_memory': 1073741824,  # 1GB
                'resolution_width': 1280,
                'resolution_height': 720,
                'vsync': False,
            },
            'ultra': {
                'gfx_detail_level': 'ultra',
                'gfx_video_memory': 8589934592,  # 8GB
                'resolution_width': 3840,
                'resolution_height': 2160,
                'vsync': True,
            },
        }
        
        if preset_name not in presets:
            print(f"Unknown preset: {preset_name}")
            return False
        
        preset = presets[preset_name]
        
        for key, value in preset.items():
            self.set_value(key, value)
        
        print(f"Applied preset: {preset_name}")
        return True
    
    def get_all_values(self) -> Dict[str, Any]:
        """
        Get all configuration values.
        
        Returns:
            Dict[str, Any]: All config values
        """
        return self.config_values.copy()
    
    def get_modifications_summary(self) -> List[str]:
        """
        Get list of modified options.
        
        Returns:
            List[str]: List of modified option names
        """
        return self.modifications
    
    def set_read_only(self, read_only: bool = True) -> bool:
        """
        Set the file to read-only (prevent game from overwriting).
        
        Args:
            read_only: Whether to make read-only
            
        Returns:
            bool: True if successful
        """
        if not self.file_path:
            return False
        
        try:
            import stat
            
            if read_only:
                # Make read-only
                current_mode = self.file_path.stat().st_mode
                self.file_path.chmod(current_mode & ~stat.S_IWRITE)
                print(f"File set to read-only: {self.file_path}")
            else:
                # Make writable
                current_mode = self.file_path.stat().st_mode
                self.file_path.chmod(current_mode | stat.S_IWRITE)
                print(f"File set to writable: {self.file_path}")
            
            return True
            
        except Exception as e:
            print(f"Failed to change file permissions: {e}")
            return False
    
    @staticmethod
    def find_config_file() -> Optional[Path]:
        """
        Find the preferences.script file.
        
        Returns:
            Optional[Path]: Path to config file or None
        """
        scripts_dir = get_scripts_directory()
        if scripts_dir:
            config_path = scripts_dir / 'preferences.script'
            if config_path.exists():
                return config_path
        return None
    
    def close(self) -> None:
        """Clear loaded data."""
        self.file_path = None
        self.content = ""
        self.original_content = ""
        self.config_values = {}
        self.modifications = []

"""
Configuration management for Napoleon Total War Cheat Engine.
Handles settings persistence, hotkey configuration, and scan parameters.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
import threading

logger = logging.getLogger('napoleon.config')


@dataclass
class HotkeyConfig:
    """Configuration for a single hotkey."""
    key: str
    modifiers: List[str] = field(default_factory=list)
    enabled: bool = True


@dataclass
class ScanSettings:
    """Memory scanning configuration."""
    default_type: str = "INT_32"
    max_results: int = 10000
    parallel_workers: int = 4
    enable_signature_scan: bool = True


@dataclass
class PathSettings:
    """Path configuration."""
    napoleon_install: Optional[str] = None
    save_directory: Optional[str] = None
    scripts_directory: Optional[str] = None
    backup_directory: Optional[str] = None


@dataclass
class Config:
    """Main configuration structure."""
    hotkeys: Dict[str, HotkeyConfig] = field(default_factory=dict)
    scan_settings: ScanSettings = field(default_factory=ScanSettings)
    paths: PathSettings = field(default_factory=PathSettings)
    ui_theme: str = "dark"
    auto_backup: bool = True
    debug_mode: bool = False
    overlay_animation: str = "smoke_screen"
    effects_overlay: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Config':
        """Create Config from dictionary."""
        config = cls()
        
        if 'hotkeys' in data:
            for name, hk_data in data['hotkeys'].items():
                config.hotkeys[name] = HotkeyConfig(**hk_data)
        
        if 'scan_settings' in data:
            config.scan_settings = ScanSettings(**data['scan_settings'])
        
        if 'paths' in data:
            config.paths = PathSettings(**data['paths'])
        
        if 'ui_theme' in data:
            config.ui_theme = data['ui_theme']
        
        if 'auto_backup' in data:
            config.auto_backup = data['auto_backup']
        
        if 'debug_mode' in data:
            config.debug_mode = data['debug_mode']
        
        if 'overlay_animation' in data:
            config.overlay_animation = data['overlay_animation']
        
        if 'effects_overlay' in data:
            config.effects_overlay = data['effects_overlay']
        
        return config


class ConfigManager:
    """
    Manages configuration loading, saving, and access.
    Thread-safe singleton pattern.
    """
    
    _instance: Optional['ConfigManager'] = None
    _lock = threading.Lock()
    
    def __new__(cls) -> 'ConfigManager':
        """Singleton pattern."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    # Schema for validating raw config dicts before deserialization
    _CONFIG_SCHEMA = {
        'hotkeys': {'type': dict, 'required': False},
        'scan_settings': {
            'type': dict,
            'required': False,
            'children': {
                'default_type': {'type': str, 'required': False},
                'max_results': {'type': int, 'required': False, 'min': 1, 'max': 10_000_000},
                'parallel_workers': {'type': int, 'required': False, 'min': 1, 'max': 64},
                'enable_signature_scan': {'type': bool, 'required': False},
            },
        },
        'paths': {
            'type': dict,
            'required': False,
            'children': {
                'napoleon_install': {'type': (str, type(None)), 'required': False},
                'save_directory': {'type': (str, type(None)), 'required': False},
                'scripts_directory': {'type': (str, type(None)), 'required': False},
                'backup_directory': {'type': (str, type(None)), 'required': False},
            },
        },
        'ui_theme': {'type': str, 'required': False},
        'auto_backup': {'type': bool, 'required': False},
        'debug_mode': {'type': bool, 'required': False},
        'overlay_animation': {'type': str, 'required': False},
        'effects_overlay': {'type': dict, 'required': False},
    }

    def __init__(self):
        """Initialize configuration manager."""
        if hasattr(self, '_initialized') and self._initialized:
            return
        
        self.config: Config = Config()
        self.config_path: Optional[Path] = None
        self._lock = threading.Lock()
        self._initialized = True
    
    def _validate_config(self, data: Dict[str, Any], schema: Optional[Dict] = None, prefix: str = '') -> List[str]:
        """
        Validate a configuration dictionary against the schema.

        Checks types, numeric ranges, and warns about unknown keys.

        Args:
            data: Configuration dict to validate
            schema: Schema dict (uses _CONFIG_SCHEMA if None)
            prefix: Dot-separated key prefix for nested error messages

        Returns:
            List[str]: List of validation error messages (empty if valid)
        """
        if schema is None:
            schema = self._CONFIG_SCHEMA

        errors: List[str] = []

        if not isinstance(data, dict):
            errors.append(f"{prefix or 'config'}: expected dict, got {type(data).__name__}")
            return errors

        # Check for unknown keys
        known_keys = set(schema.keys())
        for key in data:
            full_key = f"{prefix}.{key}" if prefix else key
            if key not in known_keys:
                logger.warning("Unknown config key ignored: %s", full_key)

        # Validate known keys
        for key, rules in schema.items():
            full_key = f"{prefix}.{key}" if prefix else key
            if key not in data:
                continue

            value = data[key]
            expected_type = rules.get('type')

            # Type check
            if expected_type is not None and not isinstance(value, expected_type):
                errors.append(
                    f"{full_key}: expected {expected_type}, got {type(value).__name__}"
                )
                continue

            # Numeric range checks
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                if 'min' in rules and value < rules['min']:
                    errors.append(f"{full_key}: value {value} below minimum {rules['min']}")
                if 'max' in rules and value > rules['max']:
                    errors.append(f"{full_key}: value {value} above maximum {rules['max']}")

            # Recurse into nested dicts
            if 'children' in rules and isinstance(value, dict):
                errors.extend(self._validate_config(value, rules['children'], full_key))

        return errors

    def load(self, config_path: Optional[str] = None) -> bool:
        """
        Load configuration from file.
        
        Args:
            config_path: Optional path to config file
            
        Returns:
            bool: True if loaded successfully
        """
        with self._lock:
            try:
                if config_path:
                    self.config_path = Path(config_path)
                else:
                    # Default config location
                    self.config_path = Path.home() / '.napoleon_cheat' / 'config.json'
                
                try:
                    with open(self.config_path, 'r') as f:
                        data = json.load(f)
                except FileNotFoundError:
                    logger.info("Config file not found: %s", self.config_path)
                    return False
                except PermissionError:
                    logger.error("Permission denied reading config: %s", self.config_path)
                    return False
                
                # Validate before applying
                errors = self._validate_config(data)
                if errors:
                    for err in errors:
                        logger.error("Config validation error: %s", err)
                    return False
                
                self.config = Config.from_dict(data)
                logger.info("Loaded configuration from %s", self.config_path)
                return True
                
            except Exception as e:
                logger.error("Failed to load config: %s", e)
                return False
    
    def save(self, config_path: Optional[str] = None) -> bool:
        """
        Save configuration to file.
        
        Args:
            config_path: Optional path (uses loaded path if None)
            
        Returns:
            bool: True if saved successfully
        """
        with self._lock:
            try:
                path = Path(config_path) if config_path else self.config_path
                
                if not path:
                    print("No config path specified")
                    return False
                
                # Create directory if needed
                path.parent.mkdir(parents=True, exist_ok=True)
                
                # Write config
                with open(path, 'w') as f:
                    json.dump(self.config.to_dict(), f, indent=2)
                
                print(f"Saved configuration to {path}")
                return True
                
            except Exception as e:
                print(f"Failed to save config: {e}")
                return False
    
    def get_hotkey(self, cheat_name: str) -> Optional[HotkeyConfig]:
        """Get hotkey configuration for a cheat."""
        return self.config.hotkeys.get(cheat_name)
    
    def set_hotkey(
        self,
        cheat_name: str,
        key: str,
        modifiers: Optional[List[str]] = None,
        enabled: bool = True
    ) -> None:
        """Set hotkey configuration for a cheat."""
        self.config.hotkeys[cheat_name] = HotkeyConfig(
            key=key,
            modifiers=modifiers or [],
            enabled=enabled
        )
    
    def get_scan_setting(self, name: str) -> Any:
        """Get a scan setting by name."""
        return getattr(self.config.scan_settings, name, None)
    
    def set_scan_setting(self, name: str, value: Any) -> bool:
        """Set a scan setting by name."""
        if hasattr(self.config.scan_settings, name):
            setattr(self.config.scan_settings, name, value)
            return True
        return False
    
    def get_path(self, name: str) -> Optional[str]:
        """Get a path setting by name."""
        return getattr(self.config.paths, name, None)
    
    def set_path(self, name: str, path: str) -> bool:
        """Set a path setting by name."""
        if hasattr(self.config.paths, name):
            setattr(self.config.paths, name, path)
            return True
        return False
    
    def reset_to_defaults(self) -> None:
        """Reset all settings to defaults."""
        self.config = Config()
    
    @classmethod
    def reset_instance(cls) -> None:
        """Reset the singleton instance. Used for test isolation."""
        with cls._lock:
            cls._instance = None
    
    def export_config(self, output_path: str) -> bool:
        """Export current config to a file."""
        try:
            with open(output_path, 'w') as f:
                json.dump(self.config.to_dict(), f, indent=2)
            return True
        except Exception:
            return False
    
    def import_config(self, input_path: str) -> bool:
        """Import config from a file."""
        try:
            with open(input_path, 'r') as f:
                data = json.load(f)
            errors = self._validate_config(data)
            if errors:
                for err in errors:
                    logger.error("Import validation error: %s", err)
                return False
            self.config = Config.from_dict(data)
            return True
        except Exception:
            return False

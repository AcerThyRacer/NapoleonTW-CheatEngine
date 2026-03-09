"""
Plugin system for Napoleon Total War Cheat Engine.
Supports hot-loadable Python plugins with event hooks.
"""

import importlib
import importlib.util
import logging
import sys
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, List, Optional, Any, Type
from dataclasses import dataclass, field
from datetime import datetime

import hashlib


logger = logging.getLogger('napoleon.plugins')


@dataclass
class PluginMetadata:
    """Metadata about a plugin."""
    name: str
    version: str = "1.0.0"
    author: str = "Unknown"
    description: str = ""
    requires: List[str] = field(default_factory=list)


class PluginBase(ABC):
    """
    Base class for all plugins.
    Plugins must inherit from this class and implement the required methods.
    """
    
    metadata: PluginMetadata = PluginMetadata(name="BasePlugin")
    
    def __init__(self):
        self._enabled = True
        self._loaded_at = datetime.now()
    
    @abstractmethod
    def on_load(self, engine: Any) -> None:
        """Called when the plugin is loaded. Set up event subscriptions here."""
        pass
    
    @abstractmethod
    def on_unload(self) -> None:
        """Called when the plugin is unloaded. Clean up resources here."""
        pass
    
    def on_enable(self) -> None:
        """Called when the plugin is enabled."""
        self._enabled = True
    
    def on_disable(self) -> None:
        """Called when the plugin is disabled."""
        self._enabled = False
    
    @property
    def enabled(self) -> bool:
        return self._enabled
    
    @property
    def name(self) -> str:
        return self.metadata.name


@dataclass
class LoadedPlugin:
    """Tracks a loaded plugin instance."""
    instance: PluginBase
    module_path: Optional[Path] = None
    loaded_at: datetime = field(default_factory=datetime.now)
    load_count: int = 1
    error_count: int = 0
    last_error: Optional[str] = None


class PluginManager:
    """
    Manages plugin lifecycle: loading, unloading, enabling, and hot-reloading.
    
    Plugins are Python files that define a class inheriting from PluginBase.
    They can subscribe to engine events and extend functionality.
    """
    
    def __init__(self, plugin_dirs: Optional[List[Path]] = None, require_allowlist: bool = False):
        """
        Initialize plugin manager.
        
        Args:
            plugin_dirs: Directories to search for plugins
            require_allowlist: If True, only load plugins whose SHA-256 hash is in the allowlist
        """
        self._plugins: Dict[str, LoadedPlugin] = {}
        self._plugin_dirs = plugin_dirs or []
        self._engine: Optional[Any] = None
        self._require_allowlist = require_allowlist
        self._hash_allowlist: set = set()
        self._allowlist_path: Optional[Path] = None
        
        # Default plugin directories
        default_dirs = [
            Path.home() / '.napoleon_cheat' / 'plugins',
            Path(__file__).parent.parent.parent / 'plugins',
        ]
        
        for d in default_dirs:
            if d not in self._plugin_dirs:
                self._plugin_dirs.append(d)
    
    def set_engine(self, engine: Any) -> None:
        """Set the engine reference passed to plugins."""
        self._engine = engine
    
    def discover_plugins(self) -> List[Path]:
        """
        Discover plugin files in plugin directories.
        
        Returns:
            List of paths to plugin files
        """
        found = []
        
        for plugin_dir in self._plugin_dirs:
            if not plugin_dir.exists():
                continue
            
            # Auto-load allowlist if present
            allowlist = plugin_dir / 'plugin_allowlist.sha256'
            if allowlist.exists() and not self._hash_allowlist:
                self.load_allowlist(allowlist)
            
            for py_file in plugin_dir.glob('*.py'):
                if py_file.name.startswith('_'):
                    continue
                found.append(py_file)
                logger.debug("Discovered plugin: %s", py_file)
        
        return found
    
    def load_allowlist(self, path: Path) -> int:
        """
        Load SHA-256 hash allowlist from a file.
        
        File format: one hex-encoded SHA-256 hash per line, 
        optionally followed by whitespace and a comment.
        Example:
            a1b2c3d4...  # my_plugin.py
        
        Returns:
            Number of hashes loaded
        """
        count = 0
        self._allowlist_path = path
        try:
            for line in path.read_text().splitlines():
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                hash_val = line.split()[0].lower()
                if len(hash_val) == 64:
                    self._hash_allowlist.add(hash_val)
                    count += 1
            logger.info("Loaded %d hashes from allowlist %s", count, path)
        except OSError as e:
            logger.error("Failed to read allowlist %s: %s", path, e)
        return count
    
    @staticmethod
    def hash_file(file_path: Path) -> str:
        """Compute SHA-256 hash of a file."""
        h = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                h.update(chunk)
        return h.hexdigest()
    
    def verify_plugin(self, file_path: Path) -> bool:
        """
        Verify a plugin file against the hash allowlist.
        
        Returns True if:
        - Allowlist is empty and require_allowlist is False
        - The file's SHA-256 hash is in the allowlist
        """
        if not self._hash_allowlist and not self._require_allowlist:
            return True
        
        file_hash = self.hash_file(file_path)
        
        if file_hash in self._hash_allowlist:
            logger.debug("Plugin %s verified (hash: %s...)", file_path.name, file_hash[:12])
            return True
        
        logger.warning(
            "⚠ Plugin %s has UNKNOWN hash: %s\n"
            "  Add to allowlist if trusted, or set require_allowlist=False to skip.",
            file_path.name, file_hash
        )
        return False
    
    def load_plugin_from_file(self, file_path: Path) -> Optional[str]:
        """
        Load a plugin from a Python file.
        
        The file must contain a class that inherits from PluginBase.
        Verifies file hash against the allowlist before loading.
        
        Args:
            file_path: Path to the plugin file
            
        Returns:
            Plugin name if loaded successfully, None otherwise
        """
        # Verify hash before loading untrusted code
        if not self.verify_plugin(file_path):
            if self._require_allowlist:
                logger.error("Refusing to load unverified plugin: %s", file_path)
                return None
            logger.warning("Loading unverified plugin: %s", file_path)
        
        try:
            # Load the module
            module_name = f"napoleon_plugin_{file_path.stem}"
            spec = importlib.util.spec_from_file_location(module_name, file_path)
            
            if spec is None or spec.loader is None:
                logger.error("Cannot load plugin spec: %s", file_path)
                return None
            
            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)
            
            # Find PluginBase subclass
            plugin_class = None
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (isinstance(attr, type) and 
                    issubclass(attr, PluginBase) and 
                    attr is not PluginBase):
                    plugin_class = attr
                    break
            
            if plugin_class is None:
                logger.warning("No PluginBase subclass found in %s", file_path)
                return None
            
            # Instantiate and load
            instance = plugin_class()
            name = instance.name
            
            # Unload existing version if present
            if name in self._plugins:
                self.unload_plugin(name)
            
            instance.on_load(self._engine)
            
            self._plugins[name] = LoadedPlugin(
                instance=instance,
                module_path=file_path,
            )
            
            logger.info("Loaded plugin: %s v%s by %s", 
                       name, instance.metadata.version, instance.metadata.author)
            return name
            
        except Exception as e:
            logger.error("Failed to load plugin %s: %s", file_path, e, exc_info=True)
            return None
    
    def load_plugin_class(self, plugin_class: Type[PluginBase]) -> Optional[str]:
        """Load a plugin from a class directly."""
        try:
            instance = plugin_class()
            name = instance.name
            
            if name in self._plugins:
                self.unload_plugin(name)
            
            instance.on_load(self._engine)
            
            self._plugins[name] = LoadedPlugin(instance=instance)
            logger.info("Loaded plugin class: %s", name)
            return name
            
        except Exception as e:
            logger.error("Failed to load plugin class: %s", e)
            return None
    
    def unload_plugin(self, name: str) -> bool:
        """Unload a plugin by name."""
        if name not in self._plugins:
            logger.warning("Plugin not loaded: %s", name)
            return False
        
        try:
            plugin = self._plugins[name]
            plugin.instance.on_unload()
            del self._plugins[name]
            logger.info("Unloaded plugin: %s", name)
            return True
            
        except Exception as e:
            logger.error("Error unloading plugin %s: %s", name, e)
            # Force remove
            if name in self._plugins:
                del self._plugins[name]
            return False
    
    def reload_plugin(self, name: str) -> bool:
        """Hot-reload a plugin."""
        if name not in self._plugins:
            return False
        
        plugin = self._plugins[name]
        if not plugin.module_path:
            logger.warning("Cannot reload plugin without file path: %s", name)
            return False
        
        file_path = plugin.module_path
        self.unload_plugin(name)
        result = self.load_plugin_from_file(file_path)
        
        if result:
            self._plugins[result].load_count = plugin.load_count + 1
            return True
        return False
    
    def enable_plugin(self, name: str) -> bool:
        """Enable a plugin."""
        if name in self._plugins:
            self._plugins[name].instance.on_enable()
            return True
        return False
    
    def disable_plugin(self, name: str) -> bool:
        """Disable a plugin."""
        if name in self._plugins:
            self._plugins[name].instance.on_disable()
            return True
        return False
    
    def load_all(self) -> int:
        """Discover and load all plugins. Returns count loaded."""
        files = self.discover_plugins()
        count = 0
        for f in files:
            if self.load_plugin_from_file(f):
                count += 1
        logger.info("Loaded %d/%d discovered plugins", count, len(files))
        return count
    
    def unload_all(self) -> None:
        """Unload all plugins."""
        for name in list(self._plugins.keys()):
            self.unload_plugin(name)
    
    def get_plugin(self, name: str) -> Optional[PluginBase]:
        """Get a plugin instance by name."""
        if name in self._plugins:
            return self._plugins[name].instance
        return None
    
    def list_plugins(self) -> List[Dict[str, Any]]:
        """List all loaded plugins."""
        return [
            {
                'name': p.instance.name,
                'version': p.instance.metadata.version,
                'author': p.instance.metadata.author,
                'description': p.instance.metadata.description,
                'enabled': p.instance.enabled,
                'loaded_at': p.loaded_at.isoformat(),
                'load_count': p.load_count,
                'file': str(p.module_path) if p.module_path else None,
            }
            for p in self._plugins.values()
        ]
    
    @property
    def plugin_count(self) -> int:
        return len(self._plugins)

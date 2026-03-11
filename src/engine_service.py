"""
Application-layer startup service for Napoleon Total War Cheat Engine.
"""

from __future__ import annotations

import configparser
import logging
import os
from pathlib import Path
from typing import Any, Callable, TypeVar

from src.config.settings import ConfigManager
from src.utils.error_reporter import AsyncErrorReporter, init_error_reporter
from src.utils.logging_config import setup_logging

T = TypeVar("T")


class EngineService:
    """Canonical application bootstrap service shared by all entry points."""

    def __init__(
        self,
        *,
        ini_path: str | Path = "napoleon.ini",
        debug: bool = False,
        verbose: bool = False,
        log_dir: Path | None = None,
        logging_setup: Callable[..., logging.Logger] = setup_logging,
        error_reporter_factory: Callable[..., AsyncErrorReporter] = init_error_reporter,
    ) -> None:
        self.ini_path = Path(ini_path)
        self.debug = debug
        self.verbose = verbose
        self.log_dir = log_dir or Path.cwd()
        self._logging_setup = logging_setup
        self._error_reporter_factory = error_reporter_factory

        self.logger = logging.getLogger("napoleon.engine")
        self.error_reporter: AsyncErrorReporter | None = None
        self._config_manager: ConfigManager | None = None
        self._startup_plugin_manager: Any = None
        self._bootstrapped = False
        self._root_warning_shown = False
        self._startup_plugins_loaded = False

    def resolve_log_level(self) -> int:
        """Resolve the effective log level from INI configuration and CLI flags."""
        log_level = logging.INFO

        if self.ini_path.exists():
            config = configparser.ConfigParser()
            try:
                config.read(self.ini_path)
            except Exception as exc:  # pragma: no cover - defensive logging path
                self.logger.debug("Failed to parse INI config %s: %s", self.ini_path, exc)
            else:
                for section_name in ("Logging", "logging"):
                    if config.has_section(section_name):
                        level_name = config.get(section_name, "level", fallback="INFO")
                        log_level = getattr(logging, level_name.upper(), logging.INFO)
                        break

        if self.debug or self.verbose:
            return logging.DEBUG

        return log_level

    def bootstrap(self, *, load_plugins: bool = False) -> "EngineService":
        """Initialize shared application services once."""
        if not self._bootstrapped:
            log_level = self.resolve_log_level()
            self._logging_setup(level=log_level, log_dir=self.log_dir)
            self.error_reporter = self._error_reporter_factory()
            self.error_reporter.start()
            self._bootstrapped = True

        if load_plugins:
            self.load_startup_plugins()

        return self

    def run(self, runner: Callable[["EngineService"], T], *, load_plugins: bool = False) -> T:
        """Run *runner* with the shared service lifecycle prepared."""
        self.warn_if_running_as_root()
        self.bootstrap(load_plugins=load_plugins)
        return runner(self)

    def warn_if_running_as_root(self) -> None:
        """Emit the existing security warning when running as root."""
        if self._root_warning_shown:
            return

        if hasattr(os, "geteuid") and os.geteuid() == 0:
            print("\n\033[1;31m[SECURITY WARNING]\033[0m")
            print("You are running this tool as root (sudo). This is a severe security risk!")
            print("It is highly recommended to run the tool as a regular user and use:")
            print("  sudo setcap cap_sys_ptrace=eip $(which python3)")
            print("to grant memory access without running the entire application as root.")
            print("If you continue, the tool may create files in your home directory owned by root.\n")

        self._root_warning_shown = True

    def load_startup_plugins(self) -> Any:
        """Load startup plugins once for UI-driven entry points."""
        if self._startup_plugins_loaded:
            return self._startup_plugin_manager

        try:
            from src.plugins.manager import PluginManager

            self._startup_plugin_manager = PluginManager()
            self._startup_plugin_manager.load_all()
            self._startup_plugins_loaded = True
        except Exception as exc:
            self.logger.warning("Failed to load startup plugins: %s", exc)

        return self._startup_plugin_manager

    def get_config_manager(self, *, load: bool = True) -> ConfigManager:
        """Return the shared configuration manager instance."""
        if self._config_manager is None:
            self._config_manager = ConfigManager()

        if load:
            self._config_manager.load()

        return self._config_manager

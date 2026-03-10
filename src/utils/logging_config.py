"""
Logging configuration for Napoleon Total War Cheat Engine.
Provides structured logging with file and console handlers.
"""

import logging
import logging.handlers
import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional


import os

def _sanitize_path(path_str: str) -> str:
    """Redact sensitive PII from paths (like user home directories)."""
    if not path_str:
        return path_str

    home_dir = str(Path.home())
    if home_dir in path_str:
        return path_str.replace(home_dir, '~')

    # Check for Windows username specifically if we are on Windows
    if sys.platform.startswith('win'):
        username = os.environ.get('USERNAME')
        if username and username in path_str:
            return path_str.replace(username, '<USER>')

    return path_str


class JSONFormatter(logging.Formatter):
    """JSON log formatter for structured logging."""
    
    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            'timestamp': datetime.fromtimestamp(record.created).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': _sanitize_path(record.getMessage()),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
        }
        
        if record.exc_info and record.exc_info[0] is not None:
            log_data['exception'] = _sanitize_path(self.formatException(record.exc_info))
        
        if hasattr(record, 'details'):
            if isinstance(record.details, str):
                log_data['details'] = _sanitize_path(record.details)
            else:
                log_data['details'] = record.details
        
        return json.dumps(log_data)


class ColoredFormatter(logging.Formatter):
    """Colored console formatter."""
    
    COLORS = {
        'DEBUG': '\033[36m',     # Cyan
        'INFO': '\033[32m',      # Green
        'WARNING': '\033[33m',   # Yellow
        'ERROR': '\033[31m',     # Red
        'CRITICAL': '\033[1;31m', # Bold Red
    }
    RESET = '\033[0m'
    
    def format(self, record: logging.LogRecord) -> str:
        original_levelname = record.levelname
        color = self.COLORS.get(record.levelname, self.RESET)
        record.levelname = f"{color}{record.levelname}{self.RESET}"
        formatted_message = super().format(record)
        record.levelname = original_levelname
        return _sanitize_path(formatted_message)


class SanitizedFileFormatter(logging.Formatter):
    """File formatter that redacts PII."""
    def format(self, record: logging.LogRecord) -> str:
        formatted_message = super().format(record)
        return _sanitize_path(formatted_message)


def setup_logging(
    level: int = logging.INFO,
    log_dir: Optional[Path] = None,
    json_logs: bool = False,
    console: bool = True,
    max_bytes: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5
) -> logging.Logger:
    """
    Configure the logging system for the entire application.
    
    Args:
        level: Logging level
        log_dir: Directory for log files (None = root project directory)
        json_logs: Use JSON format for file logs
        console: Enable console output
        max_bytes: Max log file size before rotation
        backup_count: Number of rotated log files to keep
    
    Returns:
        Root logger for the application
    """
    if log_dir is None:
        # Default to the root project directory
        log_dir = Path.cwd()
    
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # Create root logger for our app
    logger = logging.getLogger('napoleon')
    logger.setLevel(level)
    
    # Clear any existing handlers
    logger.handlers.clear()
    
    # Console handler
    if console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        
        if sys.stdout.isatty():
            console_fmt = ColoredFormatter(
                '%(asctime)s %(levelname)s [%(name)s] %(message)s',
                datefmt='%H:%M:%S'
            )
        else:
            console_fmt = logging.Formatter(
                '%(asctime)s %(levelname)s [%(name)s] %(message)s',
                datefmt='%H:%M:%S'
            )
        
        console_handler.setFormatter(console_fmt)
        logger.addHandler(console_handler)
    
    # File handler (rotating)
    log_file = log_dir / 'napoleon_cheat.log'
    file_handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)  # Always capture everything in file
    
    if json_logs:
        file_handler.setFormatter(JSONFormatter())
    else:
        file_handler.setFormatter(SanitizedFileFormatter(
            '%(asctime)s %(levelname)s [%(name)s.%(funcName)s:%(lineno)d] %(message)s'
        ))
    
    logger.addHandler(file_handler)
    
    # Error file handler (errors only)
    error_file = log_dir / 'napoleon_cheat_errors.log'
    error_handler = logging.handlers.RotatingFileHandler(
        error_file,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding='utf-8'
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(SanitizedFileFormatter(
        '%(asctime)s %(levelname)s [%(name)s.%(funcName)s:%(lineno)d] %(message)s\n'
        'Details: %(pathname)s'
    ))
    logger.addHandler(error_handler)
    
    logger.info("Logging system initialized (level=%s, dir=%s)", 
                logging.getLevelName(level), log_dir)
    
    return logger


def get_logger(name: str) -> logging.Logger:
    """
    Get a child logger for a specific module.
    
    Args:
        name: Module name (e.g., 'memory.scanner', 'files.esf')
    
    Returns:
        Logger instance
    """
    return logging.getLogger(f'napoleon.{name}')

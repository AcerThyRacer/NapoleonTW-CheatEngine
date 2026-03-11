#!/usr/bin/env python3
"""
Trainer entry point - delegates to the canonical application startup path.
"""

from src.main import main as app_main


def main():
    """Launch trainer mode through the shared engine service."""
    return app_main(["--trainer"])


if __name__ == '__main__':
    main()

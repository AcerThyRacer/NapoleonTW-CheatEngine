#!/usr/bin/env python3
"""Allow running the web backend as: python -m src.server"""

from src.main import main


def run() -> None:
    """Launch the canonical web backend entry point."""
    main(["--web"])


if __name__ == "__main__":
    run()

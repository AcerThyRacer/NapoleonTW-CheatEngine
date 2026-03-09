"""
DXVK installer utilities for Napoleon Total War.
"""

import shutil
import tarfile
import tempfile
import urllib.request
from pathlib import Path

from src.utils.events import EventEmitter, EventType, emit_error
from src.utils.platform import get_napoleon_install_path


DXVK_VERSION = "2.3"
DXVK_ARCHIVE_ROOT = f"dxvk-{DXVK_VERSION}"
DXVK_URL = (
    f"https://github.com/doitsujin/dxvk/releases/download/v{DXVK_VERSION}/"
    f"{DXVK_ARCHIVE_ROOT}.tar.gz"
)


def _extract_dll(tar: tarfile.TarFile, member_name: str, destination: Path) -> None:
    """Extract a single DLL from the DXVK archive into the game directory."""
    member = tar.getmember(member_name)
    if not member.isfile():
        raise FileNotFoundError(f"DXVK archive member is not a file: {member_name}")

    extracted = tar.extractfile(member)
    if extracted is None:
        raise FileNotFoundError(f"Could not extract DXVK archive member: {member_name}")

    with extracted, destination.open('wb') as output_file:
        shutil.copyfileobj(extracted, output_file)


def install_dxvk() -> bool:
    """Download and install the 32-bit DXVK wrapper DLLs for Napoleon."""
    game_dir = get_napoleon_install_path()
    if not game_dir:
        emit_error(
            "Could not find Napoleon Total War installation directory for DXVK.",
            source='dxvk_installer',
        )
        return False

    d3d9_path = game_dir / 'd3d9.dll'
    dxgi_path = game_dir / 'dxgi.dll'

    if d3d9_path.exists() and dxgi_path.exists():
        EventEmitter().emit(
            EventType.STATUS_CHANGED,
            {"status": "DXVK is already installed."},
            source='dxvk_installer',
        )
        return True

    try:
        EventEmitter().emit(
            EventType.STATUS_CHANGED,
            {"status": "Downloading DXVK..."},
            source='dxvk_installer',
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            archive_path = Path(temp_dir) / f"{DXVK_ARCHIVE_ROOT}.tar.gz"
            urllib.request.urlretrieve(DXVK_URL, str(archive_path))

            with tarfile.open(archive_path, 'r:gz') as archive:
                EventEmitter().emit(
                    EventType.STATUS_CHANGED,
                    {"status": "Installing DXVK..."},
                    source='dxvk_installer',
                )
                _extract_dll(archive, f"{DXVK_ARCHIVE_ROOT}/x32/d3d9.dll", d3d9_path)
                _extract_dll(archive, f"{DXVK_ARCHIVE_ROOT}/x32/dxgi.dll", dxgi_path)

        EventEmitter().emit(
            EventType.STATUS_CHANGED,
            {"status": "DXVK successfully installed!"},
            source='dxvk_installer',
        )
        return True

    except Exception as exc:
        emit_error(f"Failed to install DXVK: {exc}", source='dxvk_installer')
        return False

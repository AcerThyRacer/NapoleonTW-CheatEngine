"""
Tests for integration and cheat table validation.
"""

import os
import sys
import json
import struct
import tempfile
from pathlib import Path

import pytest
import psutil

# Patch psutil._common.pmmap if missing (some psutil versions lack it)
if not hasattr(psutil._common, 'pmmap'):
    psutil._common.pmmap = type('pmmap', (), {})

# Ensure src is importable
sys.path.insert(0, str(Path(__file__).parent.parent))


# ══════════════════════════════════════════════════════════════
# Fixtures
# ══════════════════════════════════════════════════════════════

@pytest.fixture
def temp_dir():
    """Provide a temporary directory that is cleaned up after test."""
    with tempfile.TemporaryDirectory() as d:
        yield Path(d)


@pytest.fixture
def sample_esf_data():
    """Create minimal valid ESF binary data."""
    buf = bytearray()
    buf.extend(b'ESF\x00')  # Magic
    buf.extend(struct.pack('<I', 1))  # Version 1

    # Root block node
    buf.append(0x01)  # BLOCK type
    name = b'root'
    buf.extend(struct.pack('<I', len(name)))
    buf.extend(name)

    # Child integer node
    buf.append(0x02)  # INTEGER type
    name2 = b'gold'
    buf.extend(struct.pack('<I', len(name2)))
    buf.extend(name2)
    buf.extend(struct.pack('<i', 50000))  # Value: 50000

    # Child float node
    buf.append(0x03)  # FLOAT type
    name3 = b'morale'
    buf.extend(struct.pack('<I', len(name3)))
    buf.extend(name3)
    buf.extend(struct.pack('<f', 100.0))

    # Child string node
    buf.append(0x04)  # STRING type
    name4 = b'faction'
    buf.extend(struct.pack('<I', len(name4)))
    buf.extend(name4)
    val = b'france'
    buf.extend(struct.pack('<I', len(val)))
    buf.extend(val)

    # Child boolean node
    buf.append(0x05)  # BOOLEAN type
    name5 = b'is_player'
    buf.extend(struct.pack('<I', len(name5)))
    buf.extend(name5)
    buf.append(0x01)  # True

    buf.append(0xFF)  # End block

    return bytes(buf)


@pytest.fixture
def sample_esf_file(temp_dir, sample_esf_data):
    """Write ESF data to a temp file."""
    path = temp_dir / "test_save.esf"
    path.write_bytes(sample_esf_data)
    return path


# ══════════════════════════════════════════════════════════════
# Integration Tests
# ══════════════════════════════════════════════════════════════

class TestIntegration:
    """Integration tests that combine multiple modules."""

    def test_import_all_modules(self):
        from src import memory, files, pack, trainer, utils
        assert all(m is not None for m in [memory, files, pack, trainer, utils])
        try:
            from src import gui
            assert gui is not None
        except (ImportError, NameError):
            pytest.skip("GUI requires PyQt6")

    def test_memory_module_exports(self):
        from src.memory import (
            ProcessManager, MemoryScanner, ScanType, ValueType,
            CheatManager, CheatType
        )
        assert all(cls is not None for cls in [
            ProcessManager, MemoryScanner, ScanType, ValueType,
            CheatManager, CheatType
        ])

    def test_files_module_exports(self):
        from src.files import ESFEditor, ESFNode, ScriptEditor, ConfigEditor
        assert all(cls is not None for cls in [ESFEditor, ESFNode, ScriptEditor, ConfigEditor])

    def test_esf_roundtrip(self, sample_esf_file, temp_dir):
        """Test: load ESF -> modify -> save -> reload -> verify."""
        from src.files.esf_editor import ESFEditor

        editor = ESFEditor()
        assert editor.load_file(str(sample_esf_file))

        # Save
        out = temp_dir / "modified.esf"
        assert editor.save_file(str(out))

        # Reload and verify file is loadable
        editor2 = ESFEditor()
        assert editor2.load_file(str(out))
        assert editor2.root is not None

    def test_cheat_table_valid_json(self):
        """Test: cheat tables in tables/ dir are valid JSON."""
        tables_dir = Path(__file__).parent.parent / 'tables'
        for json_file in tables_dir.glob('*.json'):
            with open(json_file) as f:
                data = json.load(f)
            assert 'game' in data
            assert 'version' in data

    def test_tools_exist(self):
        """Test: standalone tools directory has Python files."""
        tools_dir = Path(__file__).parent.parent / 'tools'
        assert tools_dir.exists()
        assert any(tools_dir.glob('*.py'))

    def test_main_module_import(self):
        """Test: src.main can be imported and has main function."""
        import src.main
        assert hasattr(src.main, 'main')

    def test_cheat_manager_init(self):
        """Test CheatManager initializes with definitions."""
        from src.memory import ProcessManager, MemoryScanner, CheatManager
        pm = ProcessManager()
        scanner = MemoryScanner(pm)
        cm = CheatManager(scanner)
        assert len(cm.cheat_definitions) > 0

    def test_cheat_type_enum(self):
        from src.memory import CheatType
        assert CheatType.INFINITE_GOLD is not None
        assert CheatType.GOD_MODE is not None
        assert CheatType.UNLIMITED_AMMO is not None


# ══════════════════════════════════════════════════════════════
# Cheat Table File Tests
# ══════════════════════════════════════════════════════════════

class TestCheatTable:
    """Tests for cheat table JSON files."""

    def test_napoleon_table_structure(self):
        table_path = Path(__file__).parent.parent / 'tables' / 'napoleon_v1_6.json'
        if not table_path.exists():
            pytest.skip("Cheat table not found")

        with open(table_path) as f:
            data = json.load(f)

        assert 'pointer_chains' in data
        assert 'aob_patterns' in data
        assert 'scan_guides' in data

        for name, chain in data['pointer_chains'].items():
            assert 'module' in chain
            assert 'base_offset' in chain
            assert 'offsets' in chain
            assert isinstance(chain['offsets'], list)

        for name, pattern in data['aob_patterns'].items():
            assert 'pattern' in pattern
            assert 'description' in pattern

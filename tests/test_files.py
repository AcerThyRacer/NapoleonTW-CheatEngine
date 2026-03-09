"""
Tests for file editors: ESF, Script, Config, Pack, Database, and ModCreator.
"""

import os
import sys
import struct
import tempfile
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch, PropertyMock

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
# ESF Editor Tests
# ══════════════════════════════════════════════════════════════

class TestESFEditor:
    """Tests for ESF file parsing and serialization."""

    def test_editor_init(self):
        from src.files import ESFEditor
        editor = ESFEditor()
        assert editor is not None
        assert editor.root is None

    def test_load_valid_esf(self, sample_esf_file):
        from src.files.esf_editor import ESFEditor
        editor = ESFEditor()
        result = editor.load_file(str(sample_esf_file))
        assert result is True
        assert editor.root is not None

    def test_parse_root_has_children(self, sample_esf_file):
        from src.files.esf_editor import ESFEditor
        editor = ESFEditor()
        editor.load_file(str(sample_esf_file))
        assert editor.root is not None
        assert len(editor.root.children) >= 1

    def test_load_empty_file(self, temp_dir):
        from src.files.esf_editor import ESFEditor
        empty_file = temp_dir / "empty.esf"
        empty_file.write_bytes(b'')
        editor = ESFEditor()
        result = editor.load_file(str(empty_file))
        assert result is False

    def test_load_nonexistent_file(self):
        from src.files.esf_editor import ESFEditor
        editor = ESFEditor()
        result = editor.load_file("/nonexistent/path/file.esf")
        assert result is False

    def test_save_and_reload(self, sample_esf_file, temp_dir):
        from src.files.esf_editor import ESFEditor
        editor = ESFEditor()
        editor.load_file(str(sample_esf_file))

        out_path = temp_dir / "resaved.esf"
        result = editor.save_file(str(out_path))
        assert result is True
        assert out_path.exists()

        editor2 = ESFEditor()
        result2 = editor2.load_file(str(out_path))
        assert result2 is True
        assert editor2.root is not None

    def test_node_to_dict(self, sample_esf_file):
        from src.files.esf_editor import ESFEditor
        editor = ESFEditor()
        editor.load_file(str(sample_esf_file))
        d = editor.root.to_dict()
        assert isinstance(d, dict)
        assert 'name' in d

    def test_esf_node_creation(self):
        from src.files.esf_editor import ESFNode, ESFNodeType
        node = ESFNode(
            name='test_node',
            node_type=ESFNodeType.INTEGER,
            value=42
        )
        assert node.name == 'test_node'
        assert node.value == 42
        assert node.node_type == ESFNodeType.INTEGER

    def test_esf_node_search(self):
        from src.files.esf_editor import ESFNode, ESFNodeType
        root = ESFNode(name='root', node_type=ESFNodeType.BLOCK_START)
        child1 = ESFNode(name='gold', node_type=ESFNodeType.INTEGER, value=1000)
        child2 = ESFNode(name='gold', node_type=ESFNodeType.INTEGER, value=2000)
        root.children = [child1, child2]
        results = root.find_all_by_name('gold')
        assert len(results) == 2
        assert results[0].value == 1000
        assert results[1].value == 2000

    def test_esf_node_find_child(self):
        from src.files.esf_editor import ESFNode, ESFNodeType
        root = ESFNode(name='root', node_type=ESFNodeType.BLOCK_START)
        child = ESFNode(name='gold', node_type=ESFNodeType.INTEGER, value=1000)
        root.children = [child]
        found = root.find_child('gold')
        assert found is not None
        assert found.value == 1000

    def test_esf_node_find_child_missing(self):
        from src.files.esf_editor import ESFNode, ESFNodeType
        root = ESFNode(name='root', node_type=ESFNodeType.BLOCK_START)
        found = root.find_child('nonexistent')
        assert found is None

    def test_esf_node_set_value(self):
        from src.files.esf_editor import ESFNode, ESFNodeType
        node = ESFNode(name='gold', node_type=ESFNodeType.INTEGER, value=100)
        result = node.set_value(999)
        assert result is True
        assert node.value == 999

    def test_security_error(self):
        from src.files.esf_editor import SecurityError
        with pytest.raises(SecurityError):
            raise SecurityError("Test security violation")


# ══════════════════════════════════════════════════════════════
# Script Editor Tests
# ══════════════════════════════════════════════════════════════

class TestScriptEditor:
    """Tests for Lua script editing."""

    def test_init(self):
        from src.files import ScriptEditor
        editor = ScriptEditor()
        assert editor is not None
        assert editor.content == ""

    def test_has_unsaved_changes_initially_false(self):
        from src.files import ScriptEditor
        editor = ScriptEditor()
        assert editor.has_unsaved_changes() is False

    def test_validate_syntax_returns_tuple(self):
        from src.files import ScriptEditor
        editor = ScriptEditor()
        editor.content = "local x = 5\nreturn x"
        result = editor.validate_syntax()
        assert isinstance(result, tuple)
        assert len(result) == 2
        assert isinstance(result[0], bool)


# ══════════════════════════════════════════════════════════════
# Config Editor Tests
# ══════════════════════════════════════════════════════════════

class TestConfigEditor:
    """Tests for game configuration editing."""

    def test_init(self):
        from src.files import ConfigEditor
        editor = ConfigEditor()
        assert editor is not None

    def test_value_parsing_bool(self):
        from src.files import ConfigEditor
        editor = ConfigEditor()
        assert editor._parse_value('true') is True
        assert editor._parse_value('false') is False

    def test_value_parsing_int(self):
        from src.files import ConfigEditor
        editor = ConfigEditor()
        assert editor._parse_value('42') == 42

    def test_value_parsing_float(self):
        from src.files import ConfigEditor
        editor = ConfigEditor()
        assert editor._parse_value('3.14') == 3.14

    def test_value_parsing_string(self):
        from src.files import ConfigEditor
        editor = ConfigEditor()
        assert editor._parse_value('"hello"') == 'hello'


# ══════════════════════════════════════════════════════════════
# Pack Parser Tests
# ══════════════════════════════════════════════════════════════

class TestPackParser:
    """Tests for pack file parsing."""

    def test_parser_init(self):
        from src.pack.pack_parser import PackParser
        parser = PackParser()
        assert parser is not None
        assert parser.files == {}

    def test_load_nonexistent_file(self):
        from src.pack.pack_parser import PackParser
        parser = PackParser()
        result = parser.load_file("/nonexistent/file.pack")
        assert result is False

    def test_cache_starts_empty(self):
        from src.pack.pack_parser import PackParser
        parser = PackParser()
        assert len(parser._extraction_cache) == 0

    def test_cache_stats(self):
        from src.pack import PackParser
        parser = PackParser()
        stats = parser.get_cache_stats()
        assert 'cached_files' in stats
        assert 'max_cache_size' in stats
        assert stats['cached_files'] == 0

    def test_list_files_empty(self):
        from src.pack import PackParser
        parser = PackParser()
        assert parser.list_files() == []


# ══════════════════════════════════════════════════════════════
# Database Editor Tests
# ══════════════════════════════════════════════════════════════

class TestDatabaseEditor:
    """Tests for database table editor."""

    def test_init(self):
        from src.pack import DatabaseEditor
        editor = DatabaseEditor()
        assert editor is not None
        assert editor.tables == {}

    def test_value_conversion_int(self):
        from src.pack.database_editor import DatabaseEditor
        editor = DatabaseEditor()
        assert editor._convert_value('42') == 42

    def test_value_conversion_float(self):
        from src.pack.database_editor import DatabaseEditor
        editor = DatabaseEditor()
        assert editor._convert_value('3.14') == 3.14

    def test_value_conversion_bool(self):
        from src.pack.database_editor import DatabaseEditor
        editor = DatabaseEditor()
        assert editor._convert_value('true') is True
        assert editor._convert_value('false') is False

    def test_value_conversion_string(self):
        from src.pack.database_editor import DatabaseEditor
        editor = DatabaseEditor()
        assert editor._convert_value('hello') == 'hello'

    def test_get_all_tables_empty(self):
        from src.pack.database_editor import DatabaseEditor
        editor = DatabaseEditor()
        assert editor.get_all_tables() == []


# ══════════════════════════════════════════════════════════════
# Mod Creator Tests
# ══════════════════════════════════════════════════════════════

class TestModCreator:
    """Tests for mod pack creator."""

    def test_init(self):
        from src.pack import ModCreator
        creator = ModCreator()
        assert creator is not None
        assert creator.files == {}

    def test_add_file(self):
        from src.pack import ModCreator
        creator = ModCreator()
        creator.add_file('test.txt', b'Hello World')
        assert 'test.txt' in creator.files
        assert creator.files['test.txt'] == b'Hello World'

    def test_remove_file(self):
        from src.pack import ModCreator
        creator = ModCreator()
        creator.add_file('test.txt', b'data')
        result = creator.remove_file('test.txt')
        assert result is True
        assert 'test.txt' not in creator.files

    def test_clear(self):
        from src.pack import ModCreator
        creator = ModCreator()
        creator.add_file('a.txt', b'aaa')
        creator.add_file('b.txt', b'bbb')
        creator.clear()
        assert creator.files == {}

    def test_get_stats_structure(self):
        from src.pack import ModCreator
        creator = ModCreator()
        creator.add_file('f.txt', b'12345')
        stats = creator.get_stats()
        assert stats['file_count'] == 1
        assert 'total_size' in stats
        assert 'f.txt' in stats['files']

    def test_set_mod_info(self):
        from src.pack import ModCreator
        creator = ModCreator()
        creator.set_mod_info("Test Mod", "A test mod", "2.0")
        assert creator.mod_name == "Test Mod"
        assert creator.mod_version == "2.0"

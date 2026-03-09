"""
Tests for the SignatureDatabase — pattern/chain loading, validation, and
integration helpers.
"""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------

TABLES_DIR = Path(__file__).parent.parent / 'tables'


@pytest.fixture
def db():
    """Return a fresh SignatureDatabase pointed at the real tables directory."""
    from src.memory.signatures import SignatureDatabase
    instance = SignatureDatabase(tables_dir=str(TABLES_DIR))
    return instance


@pytest.fixture
def loaded_db(db):
    """Return a SignatureDatabase with the default tables already loaded."""
    db.load()
    return db


@pytest.fixture
def minimal_table(tmp_path):
    """Write a minimal JSON table to a temp directory and return the path."""
    data = {
        "game": "Test Game",
        "version": "1.0",
        "platform": ["windows"],
        "created": "2026-01-01",
        "aob_patterns": {
            "gold_write": {
                "pattern": "89 86 ?? ?? ?? ?? 8B 45 FC",
                "description": "Writes gold value",
                "offset_from_match": 0,
                "nop_bytes": 6,
                "cheat": "infinite_gold",
                "cheat_action": "NOP to freeze gold"
            }
        },
        "pointer_chains": {
            "treasury": {
                "module": "test.exe",
                "base_offset": "0x00100000",
                "offsets": ["0x10", "0x4"],
                "type": "int32",
                "description": "Player gold",
                "cheat": "infinite_gold"
            }
        },
        "scan_guides": {
            "treasury": {
                "type": "int32",
                "steps": ["Step 1", "Step 2"]
            }
        }
    }
    table_file = tmp_path / 'test_v1_0.json'
    table_file.write_text(json.dumps(data))
    return tmp_path, table_file


# ---------------------------------------------------------------------------
# SignatureDatabase — unit tests
# ---------------------------------------------------------------------------

class TestSignatureDatabaseInit:
    def test_default_tables_dir(self):
        from src.memory.signatures import SignatureDatabase
        db = SignatureDatabase()
        assert db.tables_dir.is_dir()

    def test_custom_tables_dir(self, tmp_path):
        from src.memory.signatures import SignatureDatabase
        db = SignatureDatabase(tables_dir=str(tmp_path))
        assert db.tables_dir == tmp_path

    def test_initially_empty(self, db):
        assert db.list_patterns() == []
        assert db.list_chains() == []
        assert db.list_scan_guides() == []
        assert db.metadata is None
        assert db.loaded_files == []


class TestSignatureDatabaseLoadFile:
    def test_load_specific_file(self, minimal_table):
        from src.memory.signatures import SignatureDatabase
        _, table_file = minimal_table
        db = SignatureDatabase()
        count = db.load(path=str(table_file))
        assert count == 2  # 1 pattern + 1 chain

    def test_load_all_files_in_dir(self, minimal_table):
        from src.memory.signatures import SignatureDatabase
        table_dir, _ = minimal_table
        db = SignatureDatabase(tables_dir=str(table_dir))
        count = db.load()
        assert count >= 1

    def test_loaded_file_recorded(self, minimal_table):
        from src.memory.signatures import SignatureDatabase
        _, table_file = minimal_table
        db = SignatureDatabase()
        db.load(path=str(table_file))
        assert str(table_file) in db.loaded_files

    def test_load_nonexistent_file_returns_zero(self, db):
        count = db.load(path='/nonexistent/path/missing.json')
        assert count == 0

    def test_load_invalid_json_returns_zero(self, tmp_path):
        from src.memory.signatures import SignatureDatabase
        bad = tmp_path / 'bad.json'
        bad.write_text("{ this is not valid JSON }")
        db = SignatureDatabase()
        count = db.load(path=str(bad))
        assert count == 0

    def test_metadata_populated_after_load(self, minimal_table):
        from src.memory.signatures import SignatureDatabase
        _, table_file = minimal_table
        db = SignatureDatabase()
        db.load(path=str(table_file))
        assert db.metadata is not None
        assert db.metadata.game == "Test Game"
        assert db.metadata.version == "1.0"
        assert db.metadata.platform == ["windows"]

    def test_invalid_pattern_skipped(self, tmp_path):
        from src.memory.signatures import SignatureDatabase
        data = {
            "aob_patterns": {
                "bad": {"pattern": "ZZ GG invalid", "description": "bad"}
            }
        }
        f = tmp_path / 't.json'
        f.write_text(json.dumps(data))
        db = SignatureDatabase()
        count = db.load(path=str(f))
        assert count == 0
        assert db.list_patterns() == []

    def test_chain_bad_offsets_skipped(self, tmp_path):
        from src.memory.signatures import SignatureDatabase
        data = {
            "pointer_chains": {
                "bad_chain": {
                    "module": "x.exe",
                    "base_offset": "0x1000",
                    "offsets": ["not_hex"],
                    "type": "int32"
                }
            }
        }
        f = tmp_path / 't.json'
        f.write_text(json.dumps(data))
        db = SignatureDatabase()
        count = db.load(path=str(f))
        assert count == 0


class TestSignatureDatabaseRealTable:
    """Tests that exercise the real napoleon_v1_6.json table."""

    def test_real_table_exists(self):
        assert (TABLES_DIR / 'napoleon_v1_6.json').exists()

    def test_load_real_table(self, loaded_db):
        s = loaded_db.summary()
        assert s['patterns'] >= 5
        assert s['chains'] >= 4

    def test_all_expected_patterns_present(self, loaded_db):
        expected = [
            'treasury_write',
            'movement_write',
            'health_write',
            'ammo_decrement',
            'morale_write',
            'stamina_write',
            'construction_decrement',
            'research_decrement',
            'damage_modifier',
            'speed_modifier',
        ]
        for name in expected:
            assert name in loaded_db.list_patterns(), f"Missing pattern: {name}"

    def test_all_expected_chains_present(self, loaded_db):
        expected = [
            'treasury',
            'movement_points',
            'construction_timer',
            'research_timer',
            'unit_health',
            'unit_ammo',
            'unit_morale',
            'unit_stamina',
        ]
        for name in expected:
            assert name in loaded_db.list_chains(), f"Missing chain: {name}"

    def test_all_expected_scan_guides_present(self, loaded_db):
        expected = [
            'treasury',
            'movement_points',
            'unit_health',
            'unit_ammo',
            'unit_morale',
            'unit_stamina',
            'construction_timer',
            'research_timer',
        ]
        for name in expected:
            assert name in loaded_db.list_scan_guides(), f"Missing guide: {name}"

    def test_metadata_game_field(self, loaded_db):
        assert loaded_db.metadata.game == "Napoleon Total War"

    def test_metadata_version_field(self, loaded_db):
        assert "1.6" in loaded_db.metadata.version


class TestPatternValidation:
    def test_valid_exact_bytes(self):
        from src.memory.signatures import SignatureDatabase
        assert SignatureDatabase.validate_pattern("89 86 8B 45") is True

    def test_valid_with_wildcards(self):
        from src.memory.signatures import SignatureDatabase
        assert SignatureDatabase.validate_pattern("89 ?? 8B 45 ??") is True

    def test_valid_uppercase_wildcards(self):
        from src.memory.signatures import SignatureDatabase
        assert SignatureDatabase.validate_pattern("F3 0F 11 XX ?? 8B") is True

    def test_single_byte(self):
        from src.memory.signatures import SignatureDatabase
        assert SignatureDatabase.validate_pattern("90") is True

    def test_empty_string(self):
        from src.memory.signatures import SignatureDatabase
        assert SignatureDatabase.validate_pattern("") is False

    def test_whitespace_only(self):
        from src.memory.signatures import SignatureDatabase
        assert SignatureDatabase.validate_pattern("   ") is False

    def test_invalid_chars(self):
        from src.memory.signatures import SignatureDatabase
        assert SignatureDatabase.validate_pattern("ZZ GG") is False

    def test_single_hex_digit(self):
        from src.memory.signatures import SignatureDatabase
        assert SignatureDatabase.validate_pattern("8") is False

    def test_three_hex_digits(self):
        from src.memory.signatures import SignatureDatabase
        assert SignatureDatabase.validate_pattern("ABC") is False

    def test_pattern_byte_length(self):
        from src.memory.signatures import SignatureDatabase
        assert SignatureDatabase.pattern_byte_length("89 86 ?? ?? 8B") == 5

    def test_all_real_patterns_are_valid(self, loaded_db):
        from src.memory.signatures import SignatureDatabase
        for name in loaded_db.list_patterns():
            entry = loaded_db.get_pattern_entry(name)
            assert SignatureDatabase.validate_pattern(entry.pattern.pattern), \
                f"Pattern '{name}' failed validation: {entry.pattern.pattern}"


class TestGettersAndLookups:
    def test_get_pattern_returns_aob_pattern(self, minimal_table):
        from src.memory.signatures import SignatureDatabase
        from src.memory.advanced import AOBPattern
        _, table_file = minimal_table
        db = SignatureDatabase()
        db.load(path=str(table_file))
        pat = db.get_pattern('gold_write')
        assert isinstance(pat, AOBPattern)
        assert pat.name == 'gold_write'

    def test_get_pattern_unknown_returns_none(self, db):
        assert db.get_pattern('nonexistent') is None

    def test_get_pattern_entry_has_nop_bytes(self, minimal_table):
        from src.memory.signatures import SignatureDatabase
        _, table_file = minimal_table
        db = SignatureDatabase()
        db.load(path=str(table_file))
        entry = db.get_pattern_entry('gold_write')
        assert entry.nop_bytes == 6

    def test_get_chain_returns_pointer_chain(self, minimal_table):
        from src.memory.signatures import SignatureDatabase
        from src.memory.advanced import PointerChain
        _, table_file = minimal_table
        db = SignatureDatabase()
        db.load(path=str(table_file))
        chain = db.get_chain('treasury')
        assert isinstance(chain, PointerChain)
        assert chain.module_name == 'test.exe'
        assert chain.base_offset == 0x00100000
        assert chain.offsets == [0x10, 0x4]
        assert chain.value_type == 'int32'

    def test_get_chain_unknown_returns_none(self, db):
        assert db.get_chain('nonexistent') is None

    def test_get_scan_guide(self, minimal_table):
        from src.memory.signatures import SignatureDatabase
        _, table_file = minimal_table
        db = SignatureDatabase()
        db.load(path=str(table_file))
        guide = db.get_scan_guide('treasury')
        assert guide is not None
        assert guide['type'] == 'int32'
        assert len(guide['steps']) == 2

    def test_get_scan_guide_unknown_returns_none(self, db):
        assert db.get_scan_guide('nonexistent') is None

    def test_get_patterns_for_cheat(self, minimal_table):
        from src.memory.signatures import SignatureDatabase
        _, table_file = minimal_table
        db = SignatureDatabase()
        db.load(path=str(table_file))
        entries = db.get_patterns_for_cheat('infinite_gold')
        assert len(entries) == 1
        assert entries[0].name == 'gold_write'

    def test_get_patterns_for_unknown_cheat(self, loaded_db):
        assert loaded_db.get_patterns_for_cheat('nonexistent_cheat') == []

    def test_get_chain_for_cheat(self, minimal_table):
        from src.memory.signatures import SignatureDatabase
        _, table_file = minimal_table
        db = SignatureDatabase()
        db.load(path=str(table_file))
        entry = db.get_chain_for_cheat('infinite_gold')
        assert entry is not None
        assert entry.name == 'treasury'

    def test_get_chain_for_unknown_cheat(self, loaded_db):
        assert loaded_db.get_chain_for_cheat('nonexistent_cheat') is None

    def test_list_methods_return_sorted(self, loaded_db):
        patterns = loaded_db.list_patterns()
        assert patterns == sorted(patterns)
        chains = loaded_db.list_chains()
        assert chains == sorted(chains)


class TestInjection:
    def test_inject_into_scanner(self, minimal_table):
        from src.memory.signatures import SignatureDatabase
        _, table_file = minimal_table
        db = SignatureDatabase()
        db.load(path=str(table_file))

        mock_scanner = MagicMock()
        mock_scanner.KNOWN_PATTERNS = {}
        count = db.inject_into_scanner(mock_scanner)

        assert count == 1
        assert 'gold_write' in mock_scanner.KNOWN_PATTERNS

    def test_inject_into_resolver(self, minimal_table):
        from src.memory.signatures import SignatureDatabase
        _, table_file = minimal_table
        db = SignatureDatabase()
        db.load(path=str(table_file))

        mock_resolver = MagicMock()
        mock_resolver.KNOWN_CHAINS = {}
        count = db.inject_into_resolver(mock_resolver)

        assert count == 1
        assert 'treasury' in mock_resolver.KNOWN_CHAINS

    def test_inject_into_real_aob_scanner(self, loaded_db):
        from src.memory.advanced import AOBScanner
        scanner = AOBScanner()
        original_count = len(AOBScanner.KNOWN_PATTERNS)
        loaded_db.inject_into_scanner(scanner)
        # After injection the class-level dict should contain our patterns
        for name in loaded_db.list_patterns():
            assert name in scanner.KNOWN_PATTERNS

    def test_inject_into_real_pointer_resolver(self, loaded_db):
        from src.memory.advanced import PointerResolver
        resolver = PointerResolver()
        loaded_db.inject_into_resolver(resolver)
        for name in loaded_db.list_chains():
            assert name in resolver.KNOWN_CHAINS


class TestSummaryAndRepr:
    def test_summary_keys(self, loaded_db):
        s = loaded_db.summary()
        assert 'patterns' in s
        assert 'chains' in s
        assert 'scan_guides' in s
        assert 'files' in s
        assert 'metadata' in s

    def test_summary_metadata_keys(self, loaded_db):
        meta = loaded_db.summary()['metadata']
        assert 'game' in meta
        assert 'version' in meta
        assert 'verified' in meta

    def test_repr_contains_counts(self, loaded_db):
        r = repr(loaded_db)
        assert 'SignatureDatabase' in r
        assert 'patterns=' in r
        assert 'chains=' in r


class TestAdvancedModulePatterns:
    """Verify that the built-in KNOWN_PATTERNS / KNOWN_CHAINS in advanced.py
    are fully populated and all patterns are well-formed."""

    def test_known_patterns_count(self):
        from src.memory.advanced import AOBScanner
        assert len(AOBScanner.KNOWN_PATTERNS) >= 10

    def test_known_chains_count(self):
        from src.memory.advanced import PointerResolver
        assert len(PointerResolver.KNOWN_CHAINS) >= 8

    def test_all_known_patterns_valid(self):
        from src.memory.advanced import AOBScanner
        from src.memory.signatures import SignatureDatabase
        for name, pat in AOBScanner.KNOWN_PATTERNS.items():
            assert SignatureDatabase.validate_pattern(pat.pattern), \
                f"KNOWN_PATTERNS['{name}'] has invalid pattern: {pat.pattern!r}"

    def test_all_known_chains_have_offsets(self):
        from src.memory.advanced import PointerResolver
        for name, chain in PointerResolver.KNOWN_CHAINS.items():
            assert len(chain.offsets) > 0, \
                f"KNOWN_CHAINS['{name}'] has no offsets"
            assert chain.base_offset > 0, \
                f"KNOWN_CHAINS['{name}'] has zero base_offset"

    def test_campaign_chains_present(self):
        from src.memory.advanced import PointerResolver
        for key in ('treasury', 'movement_points', 'construction_timer', 'research_timer'):
            assert key in PointerResolver.KNOWN_CHAINS

    def test_battle_chains_present(self):
        from src.memory.advanced import PointerResolver
        for key in ('unit_health', 'unit_ammo', 'unit_morale', 'unit_stamina'):
            assert key in PointerResolver.KNOWN_CHAINS

    def test_campaign_patterns_present(self):
        from src.memory.advanced import AOBScanner
        for key in ('treasury_write', 'movement_write',
                    'construction_decrement', 'research_decrement'):
            assert key in AOBScanner.KNOWN_PATTERNS

    def test_battle_patterns_present(self):
        from src.memory.advanced import AOBScanner
        for key in ('health_write', 'ammo_decrement', 'morale_write',
                    'stamina_write', 'damage_modifier', 'speed_modifier'):
            assert key in AOBScanner.KNOWN_PATTERNS

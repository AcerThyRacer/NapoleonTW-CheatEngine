"""
Signature database for Napoleon Total War memory patterns.

Loads, validates and manages AOB patterns and pointer chains from JSON table
files (tables/*.json).  A SignatureDatabase instance can then inject the loaded
entries directly into :class:`AOBScanner` and :class:`PointerResolver` so that
the rest of the engine can use them transparently.
"""

import json
import logging
import re
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field

from .advanced import AOBPattern, PointerChain

logger = logging.getLogger('napoleon.memory.signatures')

# Default tables directory (repository root / tables)
_DEFAULT_TABLES_DIR = Path(__file__).parent.parent.parent / 'tables'

# Valid AOB pattern: one or more space-separated hex-byte tokens or wildcards
_PATTERN_RE = re.compile(
    r'^(?:[0-9A-Fa-f]{2}|\?\?|XX|xx)(?:\s+(?:[0-9A-Fa-f]{2}|\?\?|XX|xx))*$'
)


@dataclass
class PatternMetadata:
    """Metadata loaded from a table file header."""
    game: str
    version: str
    platform: List[str]
    created: str
    description: str = ""
    notes: str = ""
    verified: bool = False


@dataclass
class SignatureEntry:
    """A single AOB pattern entry with its full metadata."""
    name: str
    pattern: AOBPattern
    nop_bytes: int = 0
    cheat: str = ""
    cheat_action: str = ""


@dataclass
class ChainEntry:
    """A single pointer-chain entry with its full metadata."""
    name: str
    chain: PointerChain
    cheat: str = ""
    notes: str = ""


class SignatureDatabase:
    """
    Manages a database of AOB patterns and pointer chains for Napoleon Total War.

    Usage::

        db = SignatureDatabase()
        db.load()                          # load all tables/*.json files
        pat = db.get_pattern('treasury_write')
        chain = db.get_chain('treasury')

        # Optionally inject into the live scanner / resolver
        db.inject_into_scanner(aob_scanner)
        db.inject_into_resolver(pointer_resolver)
    """

    def __init__(self, tables_dir: Optional[str] = None):
        """
        Initialise the database.

        Args:
            tables_dir: Path to the directory that contains ``*.json`` table
                files.  Defaults to the repository's ``tables/`` directory.
        """
        self.tables_dir = Path(tables_dir) if tables_dir else _DEFAULT_TABLES_DIR
        self._patterns: Dict[str, SignatureEntry] = {}
        self._chains: Dict[str, ChainEntry] = {}
        self._scan_guides: Dict[str, Dict] = {}
        self._metadata: Optional[PatternMetadata] = None
        self._loaded_files: List[str] = []

    # ------------------------------------------------------------------
    # Loading
    # ------------------------------------------------------------------

    def load(self, path: Optional[str] = None) -> int:
        """
        Load patterns from a specific JSON table file *or* from every
        ``*.json`` file found in :attr:`tables_dir`.

        Args:
            path: Optional path to a single JSON file.  When omitted all
                ``*.json`` files in :attr:`tables_dir` are loaded.

        Returns:
            Total number of entries (patterns + chains) successfully loaded.
        """
        if path:
            return self._load_file(Path(path))

        count = 0
        for json_file in sorted(self.tables_dir.glob('*.json')):
            count += self._load_file(json_file)
        return count

    def _load_file(self, path: Path) -> int:
        """Parse a single JSON table file and populate internal dicts."""
        try:
            with open(path, encoding='utf-8') as fh:
                data = json.load(fh)
        except (OSError, json.JSONDecodeError) as exc:
            logger.error("Failed to load table %s: %s", path, exc)
            return 0

        count = 0

        # Metadata — captured from the first successfully loaded file
        if self._metadata is None:
            self._metadata = PatternMetadata(
                game=data.get('game', ''),
                version=data.get('version', ''),
                platform=data.get('platform', []),
                created=data.get('created', ''),
                description=data.get('description', ''),
                notes=data.get('notes', ''),
                verified=data.get('verified', False),
            )

        # AOB patterns
        for name, entry in data.get('aob_patterns', {}).items():
            pattern_str = entry.get('pattern', '')
            if not self.validate_pattern(pattern_str):
                logger.warning("Skipping invalid AOB pattern '%s': %r", name, pattern_str)
                continue
            aob = AOBPattern(
                name=name,
                pattern=pattern_str,
                description=entry.get('description', ''),
                offset_from_match=entry.get('offset_from_match', 0),
            )
            self._patterns[name] = SignatureEntry(
                name=name,
                pattern=aob,
                nop_bytes=entry.get('nop_bytes', 0),
                cheat=entry.get('cheat', ''),
                cheat_action=entry.get('cheat_action', ''),
            )
            count += 1

        # Pointer chains
        for name, entry in data.get('pointer_chains', {}).items():
            raw_offsets = entry.get('offsets', [])
            try:
                offsets = [
                    int(o, 16) if isinstance(o, str) else int(o)
                    for o in raw_offsets
                ]
            except (ValueError, TypeError) as exc:
                logger.warning("Skipping chain '%s' — bad offsets: %s", name, exc)
                continue

            raw_base = entry.get('base_offset', '0x0')
            try:
                base_offset = int(raw_base, 16) if isinstance(raw_base, str) else int(raw_base)
            except (ValueError, TypeError) as exc:
                logger.warning("Skipping chain '%s' — bad base_offset: %s", name, exc)
                continue

            chain = PointerChain(
                module_name=entry.get('module', 'napoleon.exe'),
                base_offset=base_offset,
                offsets=offsets,
                description=entry.get('description', ''),
                value_type=entry.get('type', 'int32'),
            )
            self._chains[name] = ChainEntry(
                name=name,
                chain=chain,
                cheat=entry.get('cheat', ''),
                notes=entry.get('notes', ''),
            )
            count += 1

        # Scan guides
        self._scan_guides.update(data.get('scan_guides', {}))

        self._loaded_files.append(str(path))
        logger.info("Loaded %d entries from %s", count, path.name)
        return count

    # ------------------------------------------------------------------
    # Validation helpers
    # ------------------------------------------------------------------

    @staticmethod
    def validate_pattern(pattern: str) -> bool:
        """
        Return ``True`` if *pattern* is a well-formed AOB string.

        A valid pattern consists of one or more space-separated tokens where
        each token is either a two-hex-digit byte (``4E``) or a wildcard
        (``??``, ``XX``, or ``xx``).

        Args:
            pattern: Pattern string to validate.

        Returns:
            bool: ``True`` if valid, ``False`` otherwise.
        """
        if not pattern or not pattern.strip():
            return False
        return bool(_PATTERN_RE.match(pattern.strip()))

    @staticmethod
    def pattern_byte_length(pattern: str) -> int:
        """Return the number of byte tokens in a pattern string."""
        return len(pattern.strip().split())

    # ------------------------------------------------------------------
    # Lookups
    # ------------------------------------------------------------------

    def get_pattern(self, name: str) -> Optional[AOBPattern]:
        """
        Return the :class:`AOBPattern` for *name*, or ``None``.

        Args:
            name: Pattern key as stored in the JSON ``aob_patterns`` section.
        """
        entry = self._patterns.get(name)
        return entry.pattern if entry else None

    def get_pattern_entry(self, name: str) -> Optional[SignatureEntry]:
        """Return the full :class:`SignatureEntry` (including nop_bytes, cheat
        action, etc.) for *name*, or ``None``."""
        return self._patterns.get(name)

    def get_chain(self, name: str) -> Optional[PointerChain]:
        """
        Return the :class:`PointerChain` for *name*, or ``None``.

        Args:
            name: Chain key as stored in the JSON ``pointer_chains`` section.
        """
        entry = self._chains.get(name)
        return entry.chain if entry else None

    def get_chain_entry(self, name: str) -> Optional[ChainEntry]:
        """Return the full :class:`ChainEntry` for *name*, or ``None``."""
        return self._chains.get(name)

    def get_scan_guide(self, name: str) -> Optional[Dict]:
        """
        Return the scan-guide dict for *name*, or ``None``.

        Args:
            name: Guide key as stored in the JSON ``scan_guides`` section.
        """
        return self._scan_guides.get(name)

    def get_patterns_for_cheat(self, cheat: str) -> List[SignatureEntry]:
        """Return all :class:`SignatureEntry` objects tagged with *cheat*."""
        return [e for e in self._patterns.values() if e.cheat == cheat]

    def get_chain_for_cheat(self, cheat: str) -> Optional[ChainEntry]:
        """Return the first :class:`ChainEntry` tagged with *cheat*, or ``None``."""
        for entry in self._chains.values():
            if entry.cheat == cheat:
                return entry
        return None

    # ------------------------------------------------------------------
    # Listing
    # ------------------------------------------------------------------

    def list_patterns(self) -> List[str]:
        """Return sorted names of all loaded AOB patterns."""
        return sorted(self._patterns.keys())

    def list_chains(self) -> List[str]:
        """Return sorted names of all loaded pointer chains."""
        return sorted(self._chains.keys())

    def list_scan_guides(self) -> List[str]:
        """Return sorted names of all loaded scan guides."""
        return sorted(self._scan_guides.keys())

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def metadata(self) -> Optional[PatternMetadata]:
        """Metadata from the first loaded table file."""
        return self._metadata

    @property
    def loaded_files(self) -> List[str]:
        """Paths of all successfully loaded table files."""
        return list(self._loaded_files)

    # ------------------------------------------------------------------
    # Integration with scanner / resolver
    # ------------------------------------------------------------------

    def inject_into_scanner(self, scanner: Any) -> int:
        """
        Populate *scanner*'s ``KNOWN_PATTERNS`` dict with all loaded patterns.

        Args:
            scanner: An :class:`AOBScanner` instance (or any object that
                exposes a ``KNOWN_PATTERNS`` class-level dict).

        Returns:
            Number of patterns injected.
        """
        for name, entry in self._patterns.items():
            scanner.KNOWN_PATTERNS[name] = entry.pattern
        logger.info("Injected %d patterns into scanner", len(self._patterns))
        return len(self._patterns)

    def inject_into_resolver(self, resolver: Any) -> int:
        """
        Populate *resolver*'s ``KNOWN_CHAINS`` dict with all loaded chains.

        Args:
            resolver: A :class:`PointerResolver` instance (or any object that
                exposes a ``KNOWN_CHAINS`` class-level dict).

        Returns:
            Number of chains injected.
        """
        for name, entry in self._chains.items():
            resolver.KNOWN_CHAINS[name] = entry.chain
        logger.info("Injected %d chains into resolver", len(self._chains))
        return len(self._chains)

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------

    def summary(self) -> Dict[str, Any]:
        """Return a concise summary dict of what is currently loaded."""
        return {
            'patterns': len(self._patterns),
            'chains': len(self._chains),
            'scan_guides': len(self._scan_guides),
            'files': list(self._loaded_files),
            'metadata': {
                'game': self._metadata.game if self._metadata else '',
                'version': self._metadata.version if self._metadata else '',
                'verified': self._metadata.verified if self._metadata else False,
            },
        }

    def __repr__(self) -> str:
        return (
            f"SignatureDatabase("
            f"patterns={len(self._patterns)}, "
            f"chains={len(self._chains)}, "
            f"guides={len(self._scan_guides)})"
        )

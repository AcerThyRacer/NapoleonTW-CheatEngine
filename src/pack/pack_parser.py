"""
Pack file parser for Total War .pack archives.
Based on community documentation and Pack File Manager specifications.
"""

import struct
import zlib
import logging
from collections import OrderedDict
from pathlib import Path
from typing import Dict, List, Optional, Any, BinaryIO
from dataclasses import dataclass
from functools import lru_cache
import threading

logger = logging.getLogger('napoleon.pack.parser')

try:
    from src.utils.exceptions import PackParseError, PackCorruptError
except ImportError:
    class PackParseError(Exception):
        pass
    class PackCorruptError(Exception):
        pass


@dataclass
class PackFile:
    """Represents a file within a .pack archive."""
    path: str
    offset: int
    size: int
    compressed_size: int
    is_compressed: bool
    data: Optional[bytes] = None
    
    def __str__(self):
        size_str = f"{self.size:,} bytes"
        if self.is_compressed:
            size_str += f" (compressed: {self.compressed_size:,})"
        return f"{self.path} - {size_str}"


class PackParser:
    """
    Parser for Total War .pack archive files.
    
    Pack File Format (simplified):
    - Header: Magic, version, file count, etc.
    - File Index: List of all files with metadata
    - File Data: Raw file contents
    """
    
    # Pack file magic number (4 bytes: "PACK")
    # All Total War pack files start with this identifier
    PACK_MAGIC = b'PACK'
    
    # Supported versions:
    # v3: Napoleon Total War (2010), Empire Total War
    # v4: Later Total War titles (Shogun 2, Rome 2, etc.)
    # Reference: PFM (Pack File Manager) documentation
    SUPPORTED_VERSIONS = [3, 4]
    
    def __init__(self):
        """Initialize pack parser."""
        self.file_path: Optional[Path] = None
        self.version: int = 0
        self.files: Dict[str, PackFile] = {}
        self.raw_data: bytes = b''
        self._cache_lock = threading.Lock()
        self._extraction_cache: OrderedDict = OrderedDict()
        self._max_cache_size = 100  # Maximum cached files
        
    def load_file(self, file_path: str) -> bool:
        """
        Load a .pack file.
        
        Args:
            file_path: Path to .pack file
            
        Returns:
            bool: True if loaded successfully
        """
        try:
            path = Path(file_path)
            if not path.exists():
                logger.error("File not found: %s", file_path)
                return False
            
            self.file_path = path
            
            with open(path, 'rb') as f:
                # Read and verify magic number
                magic = f.read(4)
                if magic != self.PACK_MAGIC:
                    logger.error("Invalid pack file magic: %s", magic)
                    return False
                
                # Read version
                version_bytes = f.read(4)
                self.version = struct.unpack('<I', version_bytes)[0]
                
                if self.version not in self.SUPPORTED_VERSIONS:
                    logger.warning("Unsupported pack version: %d", self.version)
                    logger.warning("Supported versions: %s", self.SUPPORTED_VERSIONS)
                    # Continue anyway, might work
                
                # Parse based on version
                if self.version == 3:
                    self._parse_v3(f)
                elif self.version == 4:
                    self._parse_v4(f)
                else:
                    # Try generic parsing
                    self._parse_generic(f)
            
            logger.info("Loaded pack file: %s (v%d)", path.name, self.version)
            logger.info("Contains %d files", len(self.files))
            return True
            
        except Exception as e:
            logger.error("Error loading pack file: %s", e)
            import traceback
            traceback.print_exc()
            return False
    
    def _parse_v3(self, f: BinaryIO) -> None:
        """
        Parse version 3 pack file.
        
        V3 Header Structure (after magic + version):
        - 0x00-0x03: File count (uint32 little-endian)
        Per File Entry:
        - 0x00-0x03: Path length (uint32)
        - 0x04-... : Path string (UTF-8, null-terminated)
        - ...+0-3: Offset in data section (uint32)
        - ...+4-7: File size (uint32)
        - ...+8-11: Compressed size (uint32, 0 if not compressed)
        """
        # Read number of files
        file_count_bytes = f.read(4)
        if len(file_count_bytes) < 4:
            raise PackParseError("Truncated file: cannot read file count")
        file_count = struct.unpack('<I', file_count_bytes)[0]
        
        # Security: sanity check file count
        if file_count > 500000:
            raise PackParseError(f"Suspicious file count: {file_count} (max 500000)")
        
        # Read file entries
        for idx in range(file_count):
            # Path length
            path_len_bytes = f.read(4)
            if len(path_len_bytes) < 4:
                logger.warning("Truncated file entry at index %d", idx)
                break
            path_len = struct.unpack('<I', path_len_bytes)[0]
            
            # Security: check path length bounds
            if path_len > 10000:
                logger.warning("Suspicious path length %d at entry %d, skipping", path_len, idx)
                break
            
            # Path string
            path_bytes = f.read(path_len)
            if len(path_bytes) < path_len:
                logger.warning("Truncated path at entry %d", idx)
                break
            file_path = path_bytes.decode('utf-8', errors='replace').rstrip('\x00')
            
            # Offset in data section
            offset_bytes = f.read(4)
            if len(offset_bytes) < 4:
                break
            offset = struct.unpack('<I', offset_bytes)[0]
            
            # Size
            size_bytes = f.read(4)
            if len(size_bytes) < 4:
                break
            size = struct.unpack('<I', size_bytes)[0]
            
            # Compressed size (0 if not compressed)
            compressed_size_bytes = f.read(4)
            if len(compressed_size_bytes) < 4:
                break
            compressed_size = struct.unpack('<I', compressed_size_bytes)[0]
            
            is_compressed = compressed_size > 0 and compressed_size != size
            
            self.files[file_path] = PackFile(
                path=file_path,
                offset=offset,
                size=size,
                compressed_size=compressed_size if is_compressed else size,
                is_compressed=is_compressed
            )
    
    def _parse_v4(self, f: BinaryIO) -> None:
        """Parse version 4 pack file (similar to v3 with minor differences)."""
        # V4 has additional fields, but basic structure is similar
        # Skip some header fields we don't need
        f.read(8)  # Skip additional header data
        
        # Then parse like v3
        self._parse_v3(f)
    
    def _parse_generic(self, f: BinaryIO) -> None:
        """Generic parsing for unknown versions."""
        # Try to read file count and parse entries
        try:
            file_count_bytes = f.read(4)
            file_count = struct.unpack('<I', file_count_bytes)[0]
            
            # Sanity check
            if file_count > 100000:
                logger.warning("File count seems too high: %d", file_count)
                return
            
            self._parse_v3(f)
        except Exception as e:
            logger.error("Generic parsing failed: %s", e)
    
    def extract_file(self, file_path: str) -> Optional[bytes]:
        """
        Extract a file from the pack archive with LRU caching.
        
        Args:
            file_path: Path within the pack
            
        Returns:
            Optional[bytes]: File data or None if not found
        """
        # Check cache first
        with self._cache_lock:
            if file_path in self._extraction_cache:
                self._extraction_cache.move_to_end(file_path)  # Mark as recently used
                return self._extraction_cache[file_path]
        
        if file_path not in self.files:
            logger.warning("File not found in pack: %s", file_path)
            return None
        
        pack_file = self.files[file_path]
        
        if pack_file.data:
            return pack_file.data
        
        # Read from disk
        if not self.file_path:
            return None
        
        try:
            with open(self.file_path, 'rb') as f:
                f.seek(pack_file.offset)
                data = f.read(pack_file.compressed_size)
                
                if pack_file.is_compressed:
                    try:
                        data = zlib.decompress(data)
                    except zlib.error as e:
                        logger.error("Decompression failed: %s", e)
                        return None
                
                pack_file.data = data
                
                # Cache the extracted data (LRU eviction)
                with self._cache_lock:
                    # Move to end if already cached (mark as recently used)
                    if file_path in self._extraction_cache:
                        self._extraction_cache.move_to_end(file_path)
                    else:
                        # Evict least recently used if at capacity
                        while len(self._extraction_cache) >= self._max_cache_size:
                            evicted_key, _ = self._extraction_cache.popitem(last=False)
                            logger.debug("LRU evicted: %s", evicted_key)
                    self._extraction_cache[file_path] = data
                
                return data
                
        except Exception as e:
            logger.error("Error extracting file: %s", e)
            return None
    
    def clear_cache(self) -> None:
        """Clear the extraction cache to free memory."""
        with self._cache_lock:
            self._extraction_cache.clear()
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Dict[str, Any]: Cache statistics
        """
        with self._cache_lock:
            total_size = sum(len(data) for data in self._extraction_cache.values())
            return {
                'cached_files': len(self._extraction_cache),
                'max_cache_size': self._max_cache_size,
                'total_cached_bytes': total_size,
                'total_cached_mb': total_size / (1024 * 1024)
            }
    
    def extract_all(self, output_dir: str) -> bool:
        """
        Extract all files from the pack.
        
        Args:
            output_dir: Directory to extract to
            
        Returns:
            bool: True if successful
        """
        import os
        
        output_path = Path(output_dir).resolve()
        output_path.mkdir(parents=True, exist_ok=True)
        
        success_count = 0
        for file_path in self.files.keys():
            data = self.extract_file(file_path)
            if data:
                # Create directory structure
                dest_path = (output_path / file_path).resolve()

                # Prevent path traversal (Zip Slip)
                try:
                    dest_path.relative_to(output_path)
                except ValueError:
                    logger.error("Path traversal detected, skipping file: %s", file_path)
                    continue

                dest_path.parent.mkdir(parents=True, exist_ok=True)
                
                with open(dest_path, 'wb') as f:
                    f.write(data)
                
                success_count += 1
        
        logger.info("Extracted %d/%d files", success_count, len(self.files))
        return success_count > 0
    
    def list_files(self, pattern: Optional[str] = None) -> List[str]:
        """
        List files in the pack.
        
        Args:
            pattern: Optional glob pattern to filter
            
        Returns:
            List[str]: List of file paths
        """
        if pattern:
            import fnmatch
            return [f for f in self.files.keys() if fnmatch.fnmatch(f, pattern)]
        return list(self.files.keys())
    
    def get_file_info(self, file_path: str) -> Optional[PackFile]:
        """
        Get information about a file in the pack.
        
        Args:
            file_path: Path within the pack
            
        Returns:
            Optional[PackFile]: File info or None
        """
        return self.files.get(file_path)
    
    def get_database_tables(self) -> List[str]:
        """
        Get list of database tables in the pack.
        
        Returns:
            List[str]: List of table names
        """
        tables = []
        for file_path in self.files.keys():
            if file_path.endswith('.tsv') or file_path.endswith('.db'):
                tables.append(file_path)
        return tables
    
    def close(self) -> None:
        """Clear loaded data."""
        self.file_path = None
        self.version = 0
        self.files = {}
        self.raw_data = b''

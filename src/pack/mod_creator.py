"""
Mod pack creator for Napoleon Total War.
Packages modified files into .pack archives.
"""

import struct
import zlib
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime

from .pack_parser import PackParser


class ModCreator:
    """
    Creates .pack mod files for Napoleon Total War.
    """
    
    def __init__(self):
        """Initialize mod creator."""
        self.files: Dict[str, bytes] = {}
        self.mod_name: str = ""
        self.mod_description: str = ""
        self.mod_version: str = "1.0"
        
    def set_mod_info(self, name: str, description: str, version: str = "1.0") -> None:
        """
        Set mod metadata.
        
        Args:
            name: Mod name
            description: Mod description
            version: Mod version
        """
        self.mod_name = name
        self.mod_description = description
        self.mod_version = version
    
    def add_file(self, file_path: str, data: bytes) -> None:
        """
        Add a file to the mod pack.
        
        Args:
            file_path: Path within the pack (e.g., 'data/campaigns/france/scripting.lua')
            data: File content as bytes
        """
        self.files[file_path] = data
        print(f"Added file: {file_path} ({len(data):,} bytes)")
    
    def add_file_from_disk(self, disk_path: str, pack_path: str) -> bool:
        """
        Add a file from disk to the mod pack.
        
        Args:
            disk_path: Path to file on disk
            pack_path: Path within the pack
            
        Returns:
            bool: True if successful
        """
        try:
            path = Path(disk_path)
            if not path.exists():
                print(f"File not found: {disk_path}")
                return False
            
            with open(path, 'rb') as f:
                data = f.read()
            
            self.add_file(pack_path, data)
            return True
            
        except Exception as e:
            print(f"Error adding file: {e}")
            return False
    
    def add_directory(
        self,
        disk_dir: str,
        pack_prefix: str,
        pattern: Optional[str] = None
    ) -> int:
        """
        Add all files from a directory.
        
        Args:
            disk_dir: Directory on disk
            pack_prefix: Path prefix within the pack
            pattern: Optional glob pattern to filter files
            
        Returns:
            int: Number of files added
        """
        dir_path = Path(disk_dir)
        if not dir_path.exists():
            print(f"Directory not found: {disk_dir}")
            return 0
        
        count = 0
        
        if pattern:
            files = dir_path.glob(pattern)
        else:
            files = dir_path.rglob('*')
        
        for file_path in files:
            if file_path.is_file():
                # Calculate relative path
                rel_path = file_path.relative_to(dir_path)
                pack_path = f"{pack_prefix}/{rel_path}".replace('\\', '/')
                
                if self.add_file_from_disk(str(file_path), pack_path):
                    count += 1
        
        print(f"Added {count} files from {disk_dir}")
        return count
    
    def save_pack(self, output_path: str, compress: bool = False) -> bool:
        """
        Save the mod as a .pack file.
        
        Args:
            output_path: Output .pack file path
            compress: Whether to compress files
            
        Returns:
            bool: True if successful
        """
        if not self.files:
            print("No files to pack")
            return False
        
        try:
            output = Path(output_path)
            output.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output, 'wb') as f:
                # Write header
                # Magic number
                f.write(b'PACK')
                
                # Version (use version 3 for compatibility)
                f.write(struct.pack('<I', 3))
                
                # Number of files
                f.write(struct.pack('<I', len(self.files)))
                
                # We'll write file entries after calculating offsets
                # For now, write placeholder
                header_size = 4 + 4 + 4  # Magic + version + file count
                
                # Calculate file data offset (after all file entries)
                # Each entry: path_len (4) + path + offset (4) + size (4) + compressed_size (4)
                file_entries_size = 0
                file_data = []
                
                for file_path, data in self.files.items():
                    path_bytes = file_path.encode('utf-8')
                    entry_size = 4 + len(path_bytes) + 4 + 4 + 4
                    file_entries_size += entry_size
                    
                    # Prepare compressed/uncompressed data
                    if compress and len(data) > 100:
                        compressed_data = zlib.compress(data, level=6)
                        is_compressed = len(compressed_data) < len(data)
                        if is_compressed:
                            file_data.append((path_bytes, compressed_data, True))
                        else:
                            file_data.append((path_bytes, data, False))
                    else:
                        file_data.append((path_bytes, data, False))
                
                data_offset = header_size + file_entries_size
                
                # Write file entries
                current_offset = data_offset
                for path_bytes, data, is_compressed in file_data:
                    # Path length
                    f.write(struct.pack('<I', len(path_bytes)))
                    
                    # Path
                    f.write(path_bytes)
                    
                    # Offset
                    f.write(struct.pack('<I', current_offset))
                    
                    # Size
                    f.write(struct.pack('<I', len(data)))
                    
                    # Compressed size (0 if not compressed)
                    comp_size = len(data) if is_compressed else 0
                    f.write(struct.pack('<I', comp_size))
                    
                    current_offset += len(data)
                
                # Write file data
                for path_bytes, data, is_compressed in file_data:
                    f.write(data)
            
            print(f"Created mod pack: {output}")
            print(f"Total files: {len(self.files)}")
            print(f"Total size: {current_offset:,} bytes")
            
            return True
            
        except Exception as e:
            print(f"Error creating pack file: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def create_mod_pack(
        self,
        output_path: str,
        files_dir: Optional[str] = None,
        compress: bool = False
    ) -> bool:
        """
        Create a mod pack from a directory or added files.
        
        Args:
            output_path: Output .pack file path
            files_dir: Optional directory to add all files from
            compress: Whether to compress files
            
        Returns:
            bool: True if successful
        """
        if files_dir:
            self.add_directory(files_dir, 'data')
        
        return self.save_pack(output_path, compress)
    
    def get_file_list(self) -> List[str]:
        """
        Get list of files in the mod pack.
        
        Returns:
            List[str]: List of file paths
        """
        return list(self.files.keys())
    
    def remove_file(self, file_path: str) -> bool:
        """
        Remove a file from the mod pack.
        
        Args:
            file_path: Path within the pack
            
        Returns:
            bool: True if removed
        """
        if file_path in self.files:
            del self.files[file_path]
            print(f"Removed: {file_path}")
            return True
        return False
    
    def clear(self) -> None:
        """Clear all files from the mod pack."""
        self.files = {}
        print("Mod pack cleared")
    
    def get_stats(self) -> Dict:
        """
        Get mod pack statistics.
        
        Returns:
            Dict: Statistics
        """
        total_size = sum(len(data) for data in self.files.values())
        
        return {
            'name': self.mod_name,
            'version': self.mod_version,
            'file_count': len(self.files),
            'total_size': f"{total_size:,} bytes",
            'files': list(self.files.keys()),
        }
    
    @staticmethod
    def create_quick_mod(
        source_dir: str,
        output_path: str,
        mod_name: str = "Custom Mod",
        compress: bool = False
    ) -> bool:
        """
        Create a mod pack from a directory in one step.
        
        Args:
            source_dir: Directory containing mod files
            output_path: Output .pack file path
            mod_name: Mod name
            compress: Whether to compress
            
        Returns:
            bool: True if successful
        """
        creator = ModCreator()
        creator.set_mod_info(mod_name, f"Mod created from {source_dir}")
        return creator.create_mod_pack(output_path, source_dir, compress)

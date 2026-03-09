"""
.esf (Encrypted Storage File) parser and editor for Total War save games.
Based on the ESF format documentation from t-a-w.blogspot.com and community tools.
"""

import struct
import logging
import threading
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum

from src.utils import create_backup

logger = logging.getLogger('napoleon.files.esf')


from src.utils.exceptions import SecurityError


class ESFNodeType(Enum):
    """Types of ESF nodes."""
    BLOCK_START = 'block_start'
    BLOCK_END = 'block_end'
    INTEGER = 'integer'
    FLOAT = 'float'
    STRING = 'string'
    BOOLEAN = 'boolean'
    ARRAY = 'array'


@dataclass
class ESFNode:
    """
    Represents a node in the ESF hierarchy.
    """
    name: str
    node_type: ESFNodeType
    value: Optional[Any] = None
    children: List['ESFNode'] = field(default_factory=list)
    parent: Optional['ESFNode'] = None
    
    def __str__(self):
        if self.node_type in [ESFNodeType.BLOCK_START, ESFNodeType.BLOCK_END]:
            return f"{self.node_type.value}: {self.name}"
        return f"{self.name} = {self.value} ({self.node_type.value})"
    
    def to_dict(self) -> Dict:
        """Convert node to dictionary representation."""
        result = {
            'name': self.name,
            'type': self.node_type.value,
        }
        
        if self.value is not None:
            result['value'] = self.value
        
        if self.children:
            result['children'] = [child.to_dict() for child in self.children]
        
        return result
    
    def find_child(self, name: str) -> Optional['ESFNode']:
        """Find a child node by name."""
        for child in self.children:
            if child.name == name:
                return child
        return None
    
    def find_all_by_name(self, name: str) -> List['ESFNode']:
        """Find all nodes (including descendants) with given name."""
        results = []
        
        if self.name == name:
            results.append(self)
        
        for child in self.children:
            results.extend(child.find_all_by_name(name))
        
        return results
    
    def set_value(self, new_value: Any) -> bool:
        """
        Set the value of this node.
        
        Args:
            new_value: New value to set
            
        Returns:
            bool: True if successful
        """
        try:
            # Type conversion based on node type
            if self.node_type == ESFNodeType.INTEGER:
                self.value = int(new_value)
            elif self.node_type == ESFNodeType.FLOAT:
                self.value = float(new_value)
            elif self.node_type == ESFNodeType.STRING:
                self.value = str(new_value)
            elif self.node_type == ESFNodeType.BOOLEAN:
                self.value = bool(new_value)
            else:
                logger.warning("Cannot set value on %s node", self.node_type.value)
                return False
            
            return True
            
        except (ValueError, TypeError) as e:
            logger.error("Failed to set value: %s", e)
            return False


class ESFEditor:
    """
    Editor for Total War .esf save game files.
    """
    
    # ESF magic number and version
    ESF_MAGIC = b'ESF\x00'
    ESF_VERSION = 1
    
    # Type codes (inferred from community documentation)
    TYPE_BLOCK = 0x01
    TYPE_INTEGER = 0x02
    TYPE_FLOAT = 0x03
    TYPE_STRING = 0x04
    TYPE_BOOLEAN = 0x05
    TYPE_ARRAY = 0x06
    
    # Maximum allowed values for security
    MAX_NAME_LENGTH = 10000
    MAX_STRING_LENGTH = 1000000
    MAX_ARRAY_SIZE = 100000
    MAX_FILE_SIZE = 100 * 1024 * 1024  # 100 MB
    DESERIALIZE_TIMEOUT = 60.0  # seconds
    
    def __init__(self, base_directory: Optional[Path] = None):
        """
        Initialize ESF editor.
        
        Args:
            base_directory: Optional base directory for path validation
        """
        self.root: Optional[ESFNode] = None
        self.file_path: Optional[Path] = None
        self.raw_data: bytes = b''
        self.base_directory = base_directory
        
    def _validate_path(self, file_path: str) -> Path:
        """
        Validate file path to prevent path traversal attacks.
        
        Args:
            file_path: Path string to validate
            
        Returns:
            Path: Validated Path object
            
        Raises:
            SecurityError: If path traversal detected
        """
        path = Path(file_path).resolve()
        
        # If base directory is set, ensure path is within it
        if self.base_directory:
            base_resolved = self.base_directory.resolve()
            try:
                path.relative_to(base_resolved)
            except ValueError:
                raise SecurityError(
                    f"Path traversal detected: {file_path} is outside base directory {base_resolved}"
                )
        
        return path
    
    def load_file(self, file_path: str) -> bool:
        """
        Load an .esf file.
        
        Args:
            file_path: Path to .esf file
            
        Returns:
            bool: True if loaded successfully
        """
        try:
            path = Path(file_path)
            
            # Validate path if base directory is set
            if self.base_directory:
                path = self._validate_path(file_path)
            
            # Check file size before loading (avoid TOCTOU by using fd)
            try:
                with open(path, 'rb') as f:
                    f.seek(0, 2)
                    file_size = f.tell()
                    if file_size > self.MAX_FILE_SIZE:
                        logger.error("File too large: %s bytes (max: %s)", f"{file_size:,}", f"{self.MAX_FILE_SIZE:,}")
                        return False
                    f.seek(0)
                    self.raw_data = f.read()
            except FileNotFoundError:
                logger.error("File not found: %s", file_path)
                return False
            except PermissionError:
                logger.error("Permission denied: %s", file_path)
                return False
            
            # Parse the file with a timeout to prevent hangs on malformed data
            parse_result: List[Optional[ESFNode]] = [None]
            parse_error: List[Optional[Exception]] = [None]

            def _do_parse():
                try:
                    parse_result[0] = self._parse_esf(self.raw_data)
                except Exception as exc:
                    parse_error[0] = exc

            parse_thread = threading.Thread(target=_do_parse, daemon=True)
            parse_thread.start()
            parse_thread.join(timeout=self.DESERIALIZE_TIMEOUT)

            if parse_thread.is_alive():
                logger.error("ESF deserialization timed out after %.0f seconds", self.DESERIALIZE_TIMEOUT)
                return False

            if parse_error[0] is not None:
                logger.error("ESF parse error: %s", parse_error[0], exc_info=True)
                return False

            self.root = parse_result[0]
            self.file_path = path
            
            if self.root:
                logger.info("Loaded ESF file: %s", path.name)
                logger.info("Root node has %d children", len(self.root.children))
                return True
            else:
                logger.error("Failed to parse ESF file")
                return False
                
        except Exception as e:
            logger.error("Error loading ESF file: %s", e, exc_info=True)
            return False
    
    def _parse_esf(self, data: bytes) -> Optional[ESFNode]:
        """
        Parse ESF binary data using proper binary format parsing.
        
        ESF Format (based on Total War modding documentation):
        - Header: Magic (4 bytes) + Version (4 bytes)
        - Node Tree: Recursive structure with type codes
        - String Table: Null-terminated strings for node names
        
        Node Structure:
        - Type code (1 byte)
        - Name length (4 bytes, little-endian)
        - Name (variable, UTF-8)
        - Value (type-dependent)
        - Children (for blocks)
        
        Args:
            data: Raw ESF file data
            
        Returns:
            Optional[ESFNode]: Root node or None if parsing failed
        """
        try:
            if len(data) < 8:
                logger.error("File too small to be valid ESF")
                return None
            
            # Create root node
            root = ESFNode(
                name='root',
                node_type=ESFNodeType.BLOCK_START,
                value=None
            )
            
            offset = 0
            
            # Parse header
            if data[:4] == self.ESF_MAGIC:
                offset = 4
                if len(data) >= 8:
                    version = struct.unpack('<I', data[4:8])[0]
                    offset = 8
                    logger.debug("ESF version: %d", version)
            
            # Parse node tree starting at offset
            try:
                children, _ = self._parse_node_tree(data, offset, 0)
                root.children = children
            except Exception as parse_error:
                logger.warning("Node tree parsing error: %s", parse_error)
                # Fallback to string extraction for partial recovery
                self._extract_strings_fallback(data, offset, root)
            
            return root
            
        except Exception as e:
            logger.error("ESF parsing error: %s", e, exc_info=True)
            return None
    
    def _parse_node_tree(self, data: bytes, offset: int, depth: int) -> Tuple[List[ESFNode], int]:
        """
        Recursively parse ESF node tree.
        
        Args:
            data: Raw data buffer
            offset: Current position in data
            depth: Current nesting depth
            
        Returns:
            Tuple[List[ESFNode], int]: List of parsed nodes and final offset
        """
        nodes = []
        original_offset = offset
        
        while offset < len(data):
            # Check for block end marker (optional, depends on format)
            if depth > 0 and offset + 1 <= len(data) and data[offset] == 0xFF:
                offset += 1
                break
            
            # Read type code
            if offset + 1 > len(data):
                break
                
            type_code = data[offset]
            offset += 1
            
            # Skip unknown types (safety)
            if type_code not in [self.TYPE_BLOCK, self.TYPE_INTEGER, self.TYPE_FLOAT, 
                               self.TYPE_STRING, self.TYPE_BOOLEAN, self.TYPE_ARRAY]:
                # Try to recover by scanning for next valid type
                offset = self._find_next_valid_type(data, offset)
                if offset == -1:
                    break
                continue
            
            # Read name length
            if offset + 4 > len(data):
                break
            name_len = struct.unpack('<I', data[offset:offset+4])[0]
            offset += 4
            
            # Sanity check on name length
            if name_len > 10000 or offset + name_len > len(data):
                offset = self._find_next_valid_type(data, offset)
                if offset == -1:
                    break
                continue
            
            # Read name
            name = data[offset:offset+name_len].decode('utf-8', errors='replace')
            offset += name_len
            
            # Parse value based on type
            if type_code == self.TYPE_BLOCK:
                # Block: parse children
                children, offset = self._parse_node_tree(data, offset, depth + 1)
                node = ESFNode(
                    name=name,
                    node_type=ESFNodeType.BLOCK_START,
                    value=None,
                    children=children
                )
                nodes.append(node)
                
            elif type_code == self.TYPE_INTEGER:
                if offset + 4 > len(data):
                    break
                value = struct.unpack('<i', data[offset:offset+4])[0]
                offset += 4
                nodes.append(ESFNode(name=name, node_type=ESFNodeType.INTEGER, value=value))
                
            elif type_code == self.TYPE_FLOAT:
                if offset + 4 > len(data):
                    break
                value = struct.unpack('<f', data[offset:offset+4])[0]
                offset += 4
                nodes.append(ESFNode(name=name, node_type=ESFNodeType.FLOAT, value=value))
                
            elif type_code == self.TYPE_STRING:
                if offset + 4 > len(data):
                    break
                str_len = struct.unpack('<I', data[offset:offset+4])[0]
                offset += 4
                if offset + str_len > len(data):
                    break
                value = data[offset:offset+str_len].decode('utf-8', errors='replace')
                offset += str_len
                nodes.append(ESFNode(name=name, node_type=ESFNodeType.STRING, value=value))
                
            elif type_code == self.TYPE_BOOLEAN:
                if offset + 1 > len(data):
                    break
                value = data[offset] != 0
                offset += 1
                nodes.append(ESFNode(name=name, node_type=ESFNodeType.BOOLEAN, value=value))
                
            elif type_code == self.TYPE_ARRAY:
                if offset + 4 > len(data):
                    break
                array_len = struct.unpack('<I', data[offset:offset+4])[0]
                offset += 4
                array_values = []
                for _ in range(array_len):
                    if offset + 4 > len(data):
                        break
                    val = struct.unpack('<f', data[offset:offset+4])[0]
                    offset += 4
                    array_values.append(val)
                nodes.append(ESFNode(name=name, node_type=ESFNodeType.ARRAY, value=array_values))
        
        return nodes, offset
    
    def _find_next_valid_type(self, data: bytes, offset: int) -> int:
        """Find next valid type code in data stream."""
        valid_types = {self.TYPE_BLOCK, self.TYPE_INTEGER, self.TYPE_FLOAT, 
                      self.TYPE_STRING, self.TYPE_BOOLEAN, self.TYPE_ARRAY}
        
        # Scan forward up to 100 bytes
        for i in range(min(100, len(data) - offset)):
            if data[offset + i] in valid_types:
                return offset + i
        return -1
    
    def _extract_strings_fallback(self, data: bytes, offset: int, root: ESFNode) -> None:
        """Fallback: extract readable strings from binary data."""
        try:
            text_data = data[offset:].decode('utf-8', errors='ignore')
            lines = text_data.split('\x00')
            
            for line in lines:
                line = line.strip()
                if 2 < len(line) < 100:
                    if line.isalnum() or ' ' in line or '_' in line:
                        node = ESFNode(
                            name='detected_string',
                            node_type=ESFNodeType.STRING,
                            value=line
                        )
                        root.children.append(node)
        except Exception:
            pass  # Silent fallback failure
    
    def save_file(self, output_path: Optional[str] = None) -> bool:
        """
        Save the ESF file.
        
        Args:
            output_path: Optional output path (default: overwrite original)
            
        Returns:
            bool: True if saved successfully
        """
        if not self.root:
            logger.error("No ESF data to save")
            return False
        
        try:
            if output_path:
                path = Path(output_path)
            else:
                if not self.file_path:
                    logger.error("No file path specified")
                    return False
                path = self.file_path
            
            # Validate path if base directory is set
            if self.base_directory:
                path = self._validate_path(str(path))
            
            # Create backup before overwriting
            if path.exists() and output_path is None:
                backup_path = create_backup(path)
                logger.info("Backup created: %s", backup_path)
            
            # Serialize the node tree
            data = self._serialize_esf()
            
            if not data:
                logger.error("Serialization produced no data")
                return False
            
            with open(path, 'wb') as f:
                f.write(data)
            
            logger.info("Saved ESF file: %s (%d bytes)", path.name, len(data))
            return True
            
        except Exception as e:
            logger.error("Error saving ESF file: %s", e, exc_info=True)
            return False
    
    def _serialize_esf(self) -> Optional[bytes]:
        """
        Serialize the ESF tree back to binary format.
        
        Returns:
            Optional[bytes]: Serialized binary data or None on failure
        """
        try:
            parts = []
            
            # Write header
            parts.append(self.ESF_MAGIC)
            parts.append(struct.pack('<I', self.ESF_VERSION))
            
            # Serialize node tree
            if self.root:
                for child in self.root.children:
                    parts.append(self._serialize_node(child))
            
            return b''.join(parts)
            
        except Exception as e:
            logger.error("ESF serialization error: %s", e, exc_info=True)
            return None
    
    def _serialize_node(self, node: 'ESFNode') -> bytes:
        """
        Serialize a single ESF node and its children.
        
        Args:
            node: Node to serialize
            
        Returns:
            bytes: Serialized node data
        """
        parts = []
        
        if node.node_type == ESFNodeType.BLOCK_START:
            # Block node: type + name + children + end marker
            parts.append(struct.pack('B', self.TYPE_BLOCK))
            name_bytes = node.name.encode('utf-8')
            parts.append(struct.pack('<I', len(name_bytes)))
            parts.append(name_bytes)
            
            # Serialize children
            for child in node.children:
                parts.append(self._serialize_node(child))
            
            # End marker
            parts.append(struct.pack('B', 0xFF))
            
        elif node.node_type == ESFNodeType.INTEGER:
            parts.append(struct.pack('B', self.TYPE_INTEGER))
            name_bytes = node.name.encode('utf-8')
            parts.append(struct.pack('<I', len(name_bytes)))
            parts.append(name_bytes)
            parts.append(struct.pack('<i', int(node.value) if node.value is not None else 0))
            
        elif node.node_type == ESFNodeType.FLOAT:
            parts.append(struct.pack('B', self.TYPE_FLOAT))
            name_bytes = node.name.encode('utf-8')
            parts.append(struct.pack('<I', len(name_bytes)))
            parts.append(name_bytes)
            parts.append(struct.pack('<f', float(node.value) if node.value is not None else 0.0))
            
        elif node.node_type == ESFNodeType.STRING:
            parts.append(struct.pack('B', self.TYPE_STRING))
            name_bytes = node.name.encode('utf-8')
            parts.append(struct.pack('<I', len(name_bytes)))
            parts.append(name_bytes)
            value_bytes = str(node.value or '').encode('utf-8')
            parts.append(struct.pack('<I', len(value_bytes)))
            parts.append(value_bytes)
            
        elif node.node_type == ESFNodeType.BOOLEAN:
            parts.append(struct.pack('B', self.TYPE_BOOLEAN))
            name_bytes = node.name.encode('utf-8')
            parts.append(struct.pack('<I', len(name_bytes)))
            parts.append(name_bytes)
            parts.append(struct.pack('B', 1 if node.value else 0))
            
        elif node.node_type == ESFNodeType.ARRAY:
            parts.append(struct.pack('B', self.TYPE_ARRAY))
            name_bytes = node.name.encode('utf-8')
            parts.append(struct.pack('<I', len(name_bytes)))
            parts.append(name_bytes)
            
            if isinstance(node.value, (list, tuple)):
                array_data = []
                for item in node.value:
                    if isinstance(item, int):
                        array_data.append(struct.pack('<i', item))
                    elif isinstance(item, float):
                        array_data.append(struct.pack('<f', item))
                    else:
                        item_bytes = str(item).encode('utf-8')
                        array_data.append(struct.pack('<I', len(item_bytes)))
                        array_data.append(item_bytes)
                
                combined = b''.join(array_data)
                parts.append(struct.pack('<I', len(combined)))
                parts.append(combined)
            else:
                parts.append(struct.pack('<I', 0))
        
        return b''.join(parts)
    
    def _get_type_code(self, node_type: ESFNodeType) -> Optional[int]:
        """Get type code for node type."""
        type_mapping = {
            ESFNodeType.BLOCK_START: self.TYPE_BLOCK,
            ESFNodeType.INTEGER: self.TYPE_INTEGER,
            ESFNodeType.FLOAT: self.TYPE_FLOAT,
            ESFNodeType.STRING: self.TYPE_STRING,
            ESFNodeType.BOOLEAN: self.TYPE_BOOLEAN,
            ESFNodeType.ARRAY: self.TYPE_ARRAY,
        }
        return type_mapping.get(node_type)
    
    def to_xml(self) -> str:
        """
        Convert ESF tree to XML format.
        
        Returns:
            str: XML string representation
        """
        if not self.root:
            return '<?xml version="1.0"?><esf error="No data loaded"/>'
        
        xml_lines = ['<?xml version="1.0" encoding="UTF-8"?>']
        xml_lines.append('<esf>')
        
        def node_to_xml(node: ESFNode, indent: int = 2) -> List[str]:
            lines = []
            indent_str = ' ' * indent
            
            if node.node_type == ESFNodeType.BLOCK_START:
                lines.append(f'{indent_str}<block name="{node.name}">')
                for child in node.children:
                    lines.extend(node_to_xml(child, indent + 2))
                lines.append(f'{indent_str}</block>')
            else:
                value_str = str(node.value).replace('"', '&quot;')
                lines.append(
                    f'{indent_str}<{node.node_type.value} name="{node.name}" value="{value_str}"/>'
                )
            
            return lines
        
        for child in self.root.children:
            xml_lines.extend(node_to_xml(child))
        
        xml_lines.append('</esf>')
        return '\n'.join(xml_lines)
    
    def to_dict(self) -> Dict:
        """
        Convert ESF tree to dictionary.
        
        Returns:
            Dict: Dictionary representation
        """
        if not self.root:
            return {}
        return self.root.to_dict()
    
    def find_nodes(self, name: str) -> List[ESFNode]:
        """
        Find all nodes with given name.
        
        Args:
            name: Node name to search for
            
        Returns:
            List[ESFNode]: List of matching nodes
        """
        if not self.root:
            return []
        return self.root.find_all_by_name(name)
    
    def set_node_value(self, node_name: str, new_value: Any, index: int = 0) -> bool:
        """
        Set value of a node by name.
        
        Args:
            node_name: Name of node to modify
            new_value: New value to set
            index: Which occurrence to modify (if multiple nodes with same name)
            
        Returns:
            bool: True if successful
        """
        nodes = self.find_nodes(node_name)
        
        if not nodes:
            logger.warning("Node not found: %s", node_name)
            return False
        
        if index >= len(nodes):
            logger.warning("Index %d out of range (found %d nodes)", index, len(nodes))
            return False
        
        node = nodes[index]
        return node.set_value(new_value)
    
    def get_node_value(self, node_name: str, index: int = 0) -> Optional[Any]:
        """
        Get value of a node by name.
        
        Args:
            node_name: Name of node to read
            index: Which occurrence to read
            
        Returns:
            Optional[Any]: Node value or None if not found
        """
        nodes = self.find_nodes(node_name)
        
        if not nodes or index >= len(nodes):
            return None
        
        return nodes[index].value
    
    def close(self) -> None:
        """Clear loaded data."""
        self.root = None
        self.file_path = None
        self.raw_data = b''

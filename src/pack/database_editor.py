"""
Database table editor for Total War pack files.
Handles TSV (Tab-Separated Values) database tables.
"""

import csv
import io
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple

from .pack_parser import PackParser


class DatabaseEditor:
    """
    Editor for database tables within .pack files.
    """
    
    # Key database tables in Napoleon TW
    KEY_TABLES = {
        'units': 'Unit definitions',
        'unit_stats_land': 'Land unit statistics',
        'unit_stats_naval': 'Naval unit statistics',
        'building_units_allowed_table': 'Building recruitment permissions',
        'technology_tables': 'Technology requirements',
        'faction_data': 'Faction information',
        'province_data': 'Province information',
        'region_data': 'Region information',
    }
    
    def __init__(self):
        """Initialize database editor."""
        self.pack_parser: Optional[PackParser] = None
        self.tables: Dict[str, List[Dict]] = {}
        self.table_schemas: Dict[str, List[str]] = {}
        
    def load_pack(self, pack_path: str) -> bool:
        """
        Load a .pack file.
        
        Args:
            pack_path: Path to .pack file
            
        Returns:
            bool: True if successful
        """
        self.pack_parser = PackParser()
        return self.pack_parser.load_file(pack_path)
    
    def load_table(self, table_path: str) -> bool:
        """
        Load a database table from the pack.
        
        Args:
            table_path: Path to table file within pack (e.g., 'db/units_tables.tsv')
            
        Returns:
            bool: True if successful
        """
        if not self.pack_parser:
            print("No pack file loaded")
            return False
        
        data = self.pack_parser.extract_file(table_path)
        if not data:
            print(f"Could not extract table: {table_path}")
            return False
        
        try:
            # Decode and parse TSV
            text_data = data.decode('utf-8', errors='replace')
            self._parse_tsv(table_path, text_data)
            return True
            
        except Exception as e:
            print(f"Error parsing table: {e}")
            return False
    
    def _parse_tsv(self, table_path: str, tsv_data: str) -> None:
        """
        Parse TSV data into structured format.
        
        Args:
            table_path: Path/identifier for the table
            tsv_data: Raw TSV string
        """
        lines = tsv_data.strip().split('\n')
        if not lines:
            return
        
        # First line is schema (column names)
        schema_line = lines[0]
        columns = schema_line.split('\t')
        
        self.table_schemas[table_path] = columns
        
        # Parse data rows
        rows = []
        for line in lines[1:]:
            if not line.strip():
                continue
            
            values = line.split('\t')
            row = {}
            
            for i, col in enumerate(columns):
                if i < len(values):
                    value = values[i]
                    # Try to convert to appropriate type
                    row[col] = self._convert_value(value)
                else:
                    row[col] = None
            
            rows.append(row)
        
        self.tables[table_path] = rows
        print(f"Loaded table {table_path}: {len(rows)} rows, {len(columns)} columns")
    
    def _convert_value(self, value: str) -> Any:
        """Convert string value to appropriate type."""
        # Try integer
        try:
            return int(value)
        except ValueError:
            pass
        
        # Try float
        try:
            return float(value)
        except ValueError:
            pass
        
        # Boolean
        if value.lower() == 'true':
            return True
        elif value.lower() == 'false':
            return False
        
        # String
        return value
    
    def get_table(self, table_path: str) -> Optional[List[Dict]]:
        """
        Get a loaded table.
        
        Args:
            table_path: Table identifier
            
        Returns:
            Optional[List[Dict]]: Table data or None
        """
        return self.tables.get(table_path)
    
    def get_schema(self, table_path: str) -> Optional[List[str]]:
        """
        Get table schema (column names).
        
        Args:
            table_path: Table identifier
            
        Returns:
            Optional[List[str]]: List of column names
        """
        return self.table_schemas.get(table_path)
    
    def query_table(
        self,
        table_path: str,
        filters: Optional[Dict[str, Any]] = None,
        columns: Optional[List[str]] = None
    ) -> List[Dict]:
        """
        Query a table with optional filters.
        
        Args:
            table_path: Table identifier
            filters: Column value filters
            columns: Columns to return (None for all)
            
        Returns:
            List[Dict]: Query results
        """
        table = self.tables.get(table_path)
        if not table:
            return []
        
        results = []
        
        for row in table:
            # Apply filters
            if filters:
                match = True
                for col, value in filters.items():
                    if col not in row or row[col] != value:
                        match = False
                        break
                
                if not match:
                    continue
            
            # Select columns
            if columns:
                filtered_row = {col: row.get(col) for col in columns if col in row}
                results.append(filtered_row)
            else:
                results.append(row.copy())
        
        return results
    
    def update_row(
        self,
        table_path: str,
        row_index: int,
        updates: Dict[str, Any]
    ) -> bool:
        """
        Update a row in a table.
        
        Args:
            table_path: Table identifier
            row_index: Index of row to update
            updates: Column updates
            
        Returns:
            bool: True if successful
        """
        if table_path not in self.tables:
            print(f"Table not loaded: {table_path}")
            return False
        
        if row_index < 0 or row_index >= len(self.tables[table_path]):
            print(f"Row index out of range: {row_index}")
            return False
        
        row = self.tables[table_path][row_index]
        
        for col, value in updates.items():
            if col in row:
                row[col] = value
            else:
                print(f"Column not found: {col}")
                return False
        
        print(f"Updated row {row_index} in {table_path}")
        return True
    
    def find_rows(
        self,
        table_path: str,
        column: str,
        value: Any
    ) -> List[Tuple[int, Dict]]:
        """
        Find rows matching a value.
        
        Args:
            table_path: Table identifier
            column: Column to search
            value: Value to match
            
        Returns:
            List[Tuple[int, Dict]]: List of (index, row) tuples
        """
        if table_path not in self.tables:
            return []
        
        results = []
        
        for i, row in enumerate(self.tables[table_path]):
            if column in row and row[column] == value:
                results.append((i, row.copy()))
        
        return results
    
    def export_table(self, table_path: str, output_path: str) -> bool:
        """
        Export a table to TSV file.
        
        Args:
            table_path: Table identifier
            output_path: Output file path
            
        Returns:
            bool: True if successful
        """
        if table_path not in self.tables:
            print(f"Table not loaded: {table_path}")
            return False
        
        try:
            schema = self.table_schemas.get(table_path, [])
            rows = self.tables[table_path]
            
            with open(output_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f, delimiter='\t')
                
                # Write header
                writer.writerow(schema)
                
                # Write data
                for row in rows:
                    writer.writerow([row.get(col, '') for col in schema])
            
            print(f"Exported table to: {output_path}")
            return True
            
        except Exception as e:
            print(f"Error exporting table: {e}")
            return False
    
    def import_table(self, table_path: str, input_path: str) -> bool:
        """
        Import a table from TSV file.
        
        Args:
            table_path: Table identifier (for storage)
            input_path: Input TSV file path
            
        Returns:
            bool: True if successful
        """
        try:
            with open(input_path, 'r', encoding='utf-8') as f:
                tsv_data = f.read()
            
            self._parse_tsv(table_path, tsv_data)
            return True
            
        except Exception as e:
            print(f"Error importing table: {e}")
            return False
    
    def get_all_tables(self) -> List[str]:
        """
        Get list of all loaded tables.
        
        Returns:
            List[str]: List of table paths
        """
        return list(self.tables.keys())
    
    def get_table_stats(self, table_path: str) -> Dict:
        """
        Get statistics about a table.
        
        Args:
            table_path: Table identifier
            
        Returns:
            Dict: Table statistics
        """
        if table_path not in self.tables:
            return {}
        
        rows = self.tables[table_path]
        schema = self.table_schemas.get(table_path, [])
        
        return {
            'row_count': len(rows),
            'column_count': len(schema),
            'columns': schema,
            'memory_estimate': f"~{len(rows) * len(schema) * 50:,} bytes",
        }
    
    def close(self) -> None:
        """Clear loaded data."""
        if self.pack_parser:
            self.pack_parser.close()
            self.pack_parser = None
        
        self.tables = {}
        self.table_schemas = {}

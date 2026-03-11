import re

with open('src/memory/scanner.py', 'r') as f:
    content = f.read()

# Add imports and caching properties
cache_imports = """
import os
import json
import hashlib
from enum import Enum
from typing import TYPE_CHECKING, Dict, List, Optional, TypedDict, Union, cast
from dataclasses import dataclass
import struct
"""
content = content.replace("from enum import Enum\nfrom typing import TYPE_CHECKING, Dict, List, Optional, TypedDict, Union, cast\nfrom dataclasses import dataclass\nimport struct\n", cache_imports)

init_updates = """
        self.results: List[ScanResult] = []
        self.previous_values: Dict[int, ScanValue] = {}
        self.scan_history: List[ScanHistoryEntry] = []
        self._freezer: Optional["MemoryFreezer"] = None

        # Incremental scan cache
        self.cache_dir = os.path.join(os.getcwd(), '.cache', 'scans')
        os.makedirs(self.cache_dir, exist_ok=True)
"""
content = content.replace("        self._freezer: Optional[\"MemoryFreezer\"] = None", init_updates)

cache_methods = """
    def _get_cache_path(self, value_type: ValueType) -> str:
        \"\"\"Get the file path for caching scan results of a specific type.\"\"\"
        if not self.process_manager.pid:
            return ""

        # Simple cache key based on PID and value type
        key = f"{self.process_manager.pid}_{value_type.name}"
        return os.path.join(self.cache_dir, f"{key}.json")

    def _save_scan_cache(self, value_type: ValueType, results: List[ScanResult]) -> None:
        \"\"\"Save scan result addresses to cache.\"\"\"
        cache_path = self._get_cache_path(value_type)
        if not cache_path:
            return

        try:
            # We only need to save addresses to know WHERE to look next time
            addresses = [r.address for r in results[:10000]] # Limit cache size
            with open(cache_path, 'w') as f:
                json.dump(addresses, f)
        except Exception as e:
            logger.debug(f"Failed to save scan cache: {e}")

    def _load_scan_cache(self, value_type: ValueType) -> List[int]:
        \"\"\"Load cached scan addresses if available.\"\"\"
        cache_path = self._get_cache_path(value_type)
        if not cache_path or not os.path.exists(cache_path):
            return []

        try:
            with open(cache_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.debug(f"Failed to load scan cache: {e}")
            return []
"""

content = content.replace("    def attach(self) -> bool:", cache_methods + "\n    def attach(self) -> bool:")

# Modify scan_exact_value to use cache
scan_exact_patch = """
        if from_scratch:
            self.results = []
            self.previous_values = {}

            # Try to load cached regions for this type
            cached_addresses = self._load_scan_cache(value_type)
            if cached_addresses:
                logger.info(f"Loaded {len(cached_addresses)} cached addresses for {value_type.name}")

        start_time = time.monotonic()

        # Use backend if available
        if self.backend:
            try:
                # Convert value to bytes
                value_bytes = self._pack_value(value, value_type)
                type_size = self._get_type_size(value_type)

                addresses = []
                if from_scratch and cached_addresses:
                    # Scan ONLY cached addresses first
                    for addr in cached_addresses:
                        if time.monotonic() - start_time > timeout:
                            break
                        try:
                            current_data = self.backend.read_bytes(addr, type_size)
                            if current_data and current_data == value_bytes:
                                addresses.append(addr)
                        except Exception:
                            pass

                    # If we found matches in cache, skip full scan
                    if addresses:
                        logger.info(f"Found {len(addresses)} matches in cache, skipping full scan")
                    else:
                        logger.info("No matches in cache, falling back to full scan")
                        addresses = self.backend.search_bytes(value_bytes)
                else:
                    # Search memory via backend
                    addresses = self.backend.search_bytes(value_bytes)

                for addr in addresses:
                    if time.monotonic() - start_time > timeout:
                        logger.warning("Scan timed out after %.1f seconds", timeout)
                        break

                    # Read current value (or we already know it matches if from backend.search_bytes)
                    current_data = self.backend.read_bytes(addr, type_size)
                    if current_data:
                        current_value = self._unpack_value(current_data, value_type)
                        self.results.append(ScanResult(
                            address=addr,
                            value=current_value,
                            value_type=value_type
                        ))

                # Save results to cache if it was a from_scratch scan and we found a reasonable amount
                if from_scratch and len(self.results) > 0 and len(self.results) < 50000:
                    self._save_scan_cache(value_type, self.results)

                return len(self.results)
"""
# Need to replace exactly the body of scan_exact_value
import sys
import re

with open('src/memory/scanner.py', 'r') as f:
    text = f.read()

# We'll use a regex to replace the body of scan_exact_value
pattern = re.compile(r'        if from_scratch:\n            self.results = \[\]\n            self.previous_values = \{\}.*?return len\(self.results\)\n                \n            except Exception as e:\n                logger.error\("Scan error: %s", e\)\n                return 0', re.DOTALL)
match = pattern.search(text)
if match:
    text = text[:match.start()] + scan_exact_patch + """
            except Exception as e:
                logger.error("Scan error: %s", e)
                return 0""" + text[match.end():]
else:
    print("Could not find body to replace")

with open('src/memory/scanner.py', 'w') as f:
    f.write(text)

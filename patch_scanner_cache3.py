import re

with open('src/memory/scanner.py', 'r') as f:
    text = f.read()

import sys
import re

# We'll use a regex to replace the body of scan_exact_value
scan_exact_patch = """
        if from_scratch:
            self.results = []
            self.previous_values = {}

            # Try to load cached regions for this type
            cached_addresses = self._load_scan_cache(value_type)
            if cached_addresses:
                logger.info(f"Loaded {len(cached_addresses)} cached addresses for {value_type.name}")
        else:
            cached_addresses = []

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

pattern = re.compile(r'        if from_scratch:\n            self.results = \[\]\n            self.previous_values = \{\}\n        \n        start_time = time.monotonic\(\)\n        \n        # Use backend if available\n        if self.backend:\n            try:\n                # Convert value to bytes\n                value_bytes = self._pack_value\(value, value_type\)\n                \n                # Search memory via backend\n                addresses = self.backend.search_bytes\(value_bytes\)\n                \n                type_size = self._get_type_size\(value_type\)\n                for addr in addresses:\n                    if time.monotonic\(\) - start_time > timeout:\n                        logger.warning\("Scan timed out after %.1f seconds", timeout\)\n                        break\n                    \n                    # Read current value\n                    current_data = self.backend.read_bytes\(addr, type_size\)\n                    if current_data:\n                        current_value = self._unpack_value\(current_data, value_type\)\n                        self.results.append\(ScanResult\(\n                            address=addr,\n                            value=current_value,\n                            value_type=value_type\n                        \)\)\n                \n                return len\(self.results\)', re.DOTALL)

match = pattern.search(text)
if match:
    text = text[:match.start()] + scan_exact_patch + text[match.end():]
else:
    print("Could not find body to replace")

# Add import os
if "import os" not in text:
    text = "import os\n" + text

with open('src/memory/scanner.py', 'w') as f:
    f.write(text)

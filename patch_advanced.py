import sys

filepath = 'src/memory/advanced.py'
with open(filepath, 'r') as f:
    content = f.read()

import_addition = """
from src.memory.backend import DMABackend
"""

content = content.replace("from enum import Enum", "from enum import Enum\n" + import_addition)

scan_physical = """        # If using DMABackend, we can optionally scan physical memory pages
        if isinstance(self.editor, DMABackend):
            return self._scan_physical_memory(pattern, max_results, timeout)

        start_time = time.time()
"""

content = content.replace("        start_time = time.time()", scan_physical)

physical_scan_method = """    def _scan_physical_memory(self, pattern: AOBPattern, max_results: int, timeout: float) -> List[int]:
        \"\"\"Scan physical memory pages via DMA instead of relying on OS APIs.\"\"\"
        results = []
        start_time = time.time()

        try:
            regions = self.editor.get_physical_regions()
        except AttributeError:
            logger.warning("Backend does not support getting physical regions, falling back to logical memory.")
            return self.scan(pattern, start_address=0, end_address=0x7FFFFFFF, max_results=max_results, timeout=timeout)

        search_bytes, mask = self._parse_pattern(pattern.pattern)

        for region in regions:
            if time.time() - start_time > timeout:
                break

            address = region['address']
            size = region['size']

            try:
                # Need physical memory reading from backend
                data = self.editor.read_physical_bytes(address, size)
                if not data:
                    continue

                matches = self._find_pattern(data, search_bytes, mask)
                for offset in matches:
                    results.append(address + offset)
                    if len(results) >= max_results:
                        return results
            except Exception as e:
                logger.debug("Failed physical read at 0x%X: %s", address, e)

        return results

    def scan(
"""

content = content.replace("    def scan(", physical_scan_method)

with open(filepath, 'w') as f:
    f.write(content)

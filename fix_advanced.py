import sys

filepath = 'src/memory/advanced.py'
with open(filepath, 'r') as f:
    content = f.read()

# Revert the first accidental replacement in chunked scanner
bad_replacement = """        total_range = end_address - start_address
        # If using DMABackend, we can optionally scan physical memory pages
        if isinstance(self.editor, DMABackend):
            return self._scan_physical_memory(pattern, max_results, timeout)

        start_time = time.time()"""

good_replacement = """        total_range = end_address - start_address
        start_time = time.time()"""
content = content.replace(bad_replacement, good_replacement)

# Fix the method call to missing _find_pattern by replacing it with custom loop logic in _scan_physical_memory
bad_method = """                matches = self._find_pattern(data, search_bytes, mask)
                for offset in matches:
                    results.append(address + offset)
                    if len(results) >= max_results:
                        return results"""

good_method = """                # Simple search for physical pages, AOB scanner needs custom matching
                # that handles masks correctly
                matches = []
                data_len = len(data)
                pattern_len = len(byte_pattern)
                for i in range(data_len - pattern_len + 1):
                    match = True
                    for j in range(pattern_len):
                        if byte_pattern[j] is not None and data[i + j] != byte_pattern[j]:
                            match = False
                            break
                    if match:
                        results.append(address + i)
                        if len(results) >= max_results:
                            return results"""

content = content.replace(bad_method, good_method)
content = content.replace("search_bytes, mask = self._parse_pattern(pattern.pattern)", "byte_pattern = pattern.bytes_pattern")

with open(filepath, 'w') as f:
    f.write(content)

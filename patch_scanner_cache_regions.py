import re

with open('src/memory/scanner.py', 'r') as f:
    text = f.read()

# Update _save_scan_cache to save regions instead of addresses
save_cache_patch = """
    def _save_scan_cache(self, value_type: ValueType, results: List[ScanResult]) -> None:
        \"\"\"Save scan result regions to cache to speed up subsequent scans.\"\"\"
        cache_path = self._get_cache_path(value_type)
        if not cache_path or not self.backend:
            return

        try:
            # Find which regions contain our results
            all_regions = self.backend.get_prioritized_regions()
            matched_regions = []

            # Simple approach: If a region contains at least one result, save it.
            # To be efficient, we'll map results to regions.
            for region in all_regions:
                start = region['address']
                end = start + region['size']
                # Check if any result falls in this region
                if any(start <= r.address < end for r in results):
                    matched_regions.append(region)

            import json
            with open(cache_path, 'w') as f:
                json.dump(matched_regions, f)
        except Exception as e:
            logger.debug(f"Failed to save scan cache: {e}")

    def _load_scan_cache(self, value_type: ValueType) -> List[dict]:
        \"\"\"Load cached scan regions if available.\"\"\"
"""

text = re.sub(r'    def _save_scan_cache\(self, value_type: ValueType, results: List\[ScanResult\]\) -> None:\n.*?\n    def _load_scan_cache\(self, value_type: ValueType\) -> List\[int\]:\n        """Load cached scan addresses if available."""', save_cache_patch.strip('\n'), text, flags=re.DOTALL)

# Update scan_exact_value to use the cached regions
scan_exact_patch = """
        if from_scratch:
            self.results = []
            self.previous_values = {}

            # Try to load cached regions for this type
            cached_regions = self._load_scan_cache(value_type)
            if cached_regions:
                logger.info(f"Loaded {len(cached_regions)} cached regions for {value_type.name}")
        else:
            cached_regions = []

        start_time = time.monotonic()

        # Use backend if available
        if self.backend:
            try:
                # Convert value to bytes
                value_bytes = self._pack_value(value, value_type)
                type_size = self._get_type_size(value_type)

                addresses = []
                if from_scratch and cached_regions:
                    logger.info("Scanning cached regions first...")
                    # Search ONLY in cached regions
                    addresses = self.backend.search_bytes(value_bytes, regions=cached_regions)

                    # If we found matches in cache, skip full scan
                    if addresses:
                        logger.info(f"Found {len(addresses)} matches in cached regions, skipping full scan")
                    else:
                        logger.info("No matches in cached regions, falling back to full scan")
                        addresses = self.backend.search_bytes(value_bytes)
                else:
                    # Search memory via backend across all prioritized regions
                    addresses = self.backend.search_bytes(value_bytes)

                for addr in addresses:
                    if time.monotonic() - start_time > timeout:
                        logger.warning("Scan timed out after %.1f seconds", timeout)
                        break

                    # Read current value
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

text = re.sub(r'        if from_scratch:\n            self\.results = \[\]\n            self\.previous_values = \{\}\n            \n            # Try to load cached regions for this type\n            cached_addresses = self\._load_scan_cache\(value_type\)\n            if cached_addresses:\n                logger\.info\(f"Loaded \{len\(cached_addresses\)\} cached addresses for \{value_type\.name\}"\)\n        else:\n            cached_addresses = \[\]\n        \n        start_time = time\.monotonic\(\)\n        \n        # Use backend if available\n        if self\.backend:\n            try:\n                # Convert value to bytes\n                value_bytes = self\._pack_value\(value, value_type\)\n                type_size = self\._get_type_size\(value_type\)\n                \n                addresses = \[\]\n                if from_scratch and cached_addresses:\n                    # Scan ONLY cached addresses first\n                    for addr in cached_addresses:\n                        if time\.monotonic\(\) - start_time > timeout:\n                            break\n                        try:\n                            current_data = self\.backend\.read_bytes\(addr, type_size\)\n                            if current_data and current_data == value_bytes:\n                                addresses\.append\(addr\)\n                        except Exception:\n                            pass\n                            \n                    # If we found matches in cache, skip full scan\n                    if addresses:\n                        logger\.info\(f"Found \{len\(addresses\)\} matches in cache, skipping full scan"\)\n                    else:\n                        logger\.info\("No matches in cache, falling back to full scan"\)\n                        addresses = self\.backend\.search_bytes\(value_bytes\)\n                else:\n                    # Search memory via backend\n                    addresses = self\.backend\.search_bytes\(value_bytes\)\n                \n                for addr in addresses:\n                    if time\.monotonic\(\) - start_time > timeout:\n                        logger\.warning\("Scan timed out after %\.1f seconds", timeout\)\n                        break\n                    \n                    # Read current value\n                    current_data = self\.backend\.read_bytes\(addr, type_size\)\n                    if current_data:\n                        current_value = self\._unpack_value\(current_data, value_type\)\n                        self\.results\.append\(ScanResult\(\n                            address=addr,\n                            value=current_value,\n                            value_type=value_type\n                        \)\)\n                \n                # Save results to cache if it was a from_scratch scan and we found a reasonable amount\n                if from_scratch and len\(self\.results\) > 0 and len\(self\.results\) < 50000:\n                    self\._save_scan_cache\(value_type, self\.results\)\n                    \n                return len\(self\.results\)', scan_exact_patch.strip('\n'), text, flags=re.DOTALL)

with open('src/memory/scanner.py', 'w') as f:
    f.write(text)

import re

with open('src/memory/scanner.py', 'r') as f:
    text = f.read()

# 1. Update cache methods
cache_methods_new = """
    def _get_cache_path(self, scan_type_label: str) -> str:
        \"\"\"Get the file path for caching scan results of a specific semantic label.\"\"\"
        if not scan_type_label:
            return ""

        # Cache key based on semantic label, allowing cross-session caching
        key = f"cache_{scan_type_label}"
        return os.path.join(self.cache_dir, f"{key}.json")

    def _save_scan_cache(self, scan_type_label: str, results: List[ScanResult]) -> None:
        \"\"\"Save scan result regions to cache to speed up subsequent scans.\"\"\"
        cache_path = self._get_cache_path(scan_type_label)
        if not cache_path or not self.backend:
            return

        try:
            # Find which regions contain our results
            all_regions = self.backend.get_prioritized_regions()
            matched_regions = []

            # Simple approach: If a region contains at least one result, save it.
            for region in all_regions:
                start = region['address']
                end = start + region['size']
                if any(start <= r.address < end for r in results):
                    matched_regions.append(region)

            import json
            with open(cache_path, 'w') as f:
                json.dump(matched_regions, f)
        except Exception as e:
            logger.debug(f"Failed to save scan cache: {e}")

    def _load_scan_cache(self, scan_type_label: str) -> List[dict]:
        \"\"\"Load cached scan regions if available.\"\"\"
        cache_path = self._get_cache_path(scan_type_label)
        if not cache_path or not os.path.exists(cache_path):
            return []

        try:
            import json
            with open(cache_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.debug(f"Failed to load scan cache: {e}")
            return []
"""

pattern_cache_methods = re.compile(r'    def _get_cache_path\(self, value_type: ValueType\) -> str:.*?return \[\]', re.DOTALL)
text = pattern_cache_methods.sub(cache_methods_new.strip('\n'), text)


# 2. Update scan_exact_value
scan_exact_patch_new = """
    def scan_exact_value(
        self,
        value: ScanValue,
        value_type: ValueType = ValueType.INT_32,
        from_scratch: bool = True,
        timeout: float = 30.0,
        scan_type_label: Optional[str] = None
    ) -> int:
        \"\"\"
        Scan for an exact value.

        Args:
            value: Value to search for
            value_type: Type of the value
            from_scratch: If True, start new scan; if False, filter previous results
            timeout: Maximum time in seconds for the scan (default: 30.0)
            scan_type_label: Optional semantic label for caching (e.g., 'gold')

        Returns:
            int: Number of results found
        \"\"\"
        if not self.is_attached():
            raise RuntimeError("Not attached to process")

        if from_scratch:
            self.results = []
            self.previous_values = {}

            # Try to load cached regions for this semantic label
            cached_regions = self._load_scan_cache(scan_type_label) if scan_type_label else []
            if cached_regions:
                logger.info(f"Loaded {len(cached_regions)} cached regions for {scan_type_label}")
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

                # Save results to cache if it was a from_scratch scan, we found a reasonable amount, and we have a label
                if from_scratch and scan_type_label and len(self.results) > 0 and len(self.results) < 50000:
                    self._save_scan_cache(scan_type_label, self.results)

                return len(self.results)

            except Exception as e:
                logger.error("Scan error: %s", e)
                return 0

        # Fallback: Manual scanning (simplified, less efficient)
        return self._manual_scan_exact(value, value_type, from_scratch)
"""

pattern_scan_exact = re.compile(r'    def scan_exact_value\(.*?return self\._manual_scan_exact\(value, value_type, from_scratch\)', re.DOTALL)
text = pattern_scan_exact.sub(scan_exact_patch_new.strip('\n'), text)

# 3. Update scan_exact_value_parallel
scan_exact_parallel_patch_new = """
    def scan_exact_value_parallel(
        self,
        value: ScanValue,
        value_type: ValueType = ValueType.INT_32,
        from_scratch: bool = True,
        max_workers: int = 4,
        timeout: float = 30.0,
        scan_type_label: Optional[str] = None
    ) -> int:
        \"\"\"
        Scan for an exact value using parallel multi-threading.

        This is significantly faster than sequential scanning for large memory spaces.

        Args:
            value: Value to search for
            value_type: Type of the value
            from_scratch: If True, start new scan
            max_workers: Number of parallel threads (default: 4)
            timeout: Maximum time in seconds for the scan (default: 30.0)
            scan_type_label: Optional semantic label for caching (e.g., 'gold')

        Returns:
            int: Number of results found
        \"\"\"
        if not self.is_attached():
            raise RuntimeError("Not attached to process")

        if from_scratch:
            self.results = []
            self.previous_values = {}

            # Try to load cached regions for this label
            cached_regions = self._load_scan_cache(scan_type_label) if scan_type_label else []
            if cached_regions:
                logger.info(f"Loaded {len(cached_regions)} cached regions for {scan_type_label}")
        else:
            cached_regions = []

        start_time = time.monotonic()

        backend = self.backend
        if not backend:
            return self._manual_scan_exact(value, value_type, from_scratch)

        try:
            # Get memory regions
            if from_scratch and cached_regions:
                regions = cached_regions
                logger.info("Parallel scan using cached regions first...")
            else:
                regions = backend.get_prioritized_regions()

            if not regions:
                return 0
"""

# Replace the beginning of scan_exact_value_parallel up to `if not regions:\n                return 0`
pattern_scan_parallel = re.compile(r'    def scan_exact_value_parallel\(.*?if not regions:\n                return 0', re.DOTALL)
text = pattern_scan_parallel.sub(scan_exact_parallel_patch_new.strip('\n'), text)

# Add saving cache in scan_exact_value_parallel
parallel_save_cache_patch = """
            if time.monotonic() - start_time > timeout:
                print(f"Parallel scan timed out after {timeout:.1f} seconds")

            self.results = thread_results

            # If we used cached regions and found nothing, we might want to fall back to a full scan.
            # However, for simplicity and performance in the parallel method, we'll just save the new cache.
            # Save results to cache if it was a from_scratch scan, we found a reasonable amount, and we have a label
            if from_scratch and scan_type_label and not cached_regions and len(self.results) > 0 and len(self.results) < 50000:
                self._save_scan_cache(scan_type_label, self.results)

            return len(self.results)
"""

pattern_parallel_save = re.compile(r'            if time\.monotonic\(\) - start_time > timeout:\n                print\(f"Parallel scan timed out after \{timeout:\.1f\} seconds"\)\n            \n            self\.results = thread_results\n            return len\(self\.results\)', re.DOTALL)
text = pattern_parallel_save.sub(parallel_save_cache_patch.strip('\n'), text)

with open('src/memory/scanner.py', 'w') as f:
    f.write(text)

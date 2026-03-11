import re

with open('src/memory/scanner.py', 'r') as f:
    text = f.read()

# 1. Optimize _save_scan_cache
save_cache_optimized = """
    def _save_scan_cache(self, scan_type_label: str, results: List[ScanResult]) -> None:
        \"\"\"Save scan result regions to cache to speed up subsequent scans.\"\"\"
        cache_path = self._get_cache_path(scan_type_label)
        if not cache_path or not self.backend:
            return

        try:
            import bisect
            # Find which regions contain our results
            all_regions = sorted(self.backend.get_prioritized_regions(), key=lambda r: r['address'])
            region_starts = [r['address'] for r in all_regions]
            matched_regions = []

            # Efficiently map results to regions using bisect
            result_addresses = sorted(r.address for r in results)
            added_regions = set()

            for addr in result_addresses:
                # Find the region that could contain this address
                idx = bisect.bisect_right(region_starts, addr) - 1
                if idx >= 0:
                    region = all_regions[idx]
                    if addr < region['address'] + region['size']:
                        if region['address'] not in added_regions:
                            matched_regions.append(region)
                            added_regions.add(region['address'])

            import json
            with open(cache_path, 'w') as f:
                json.dump(matched_regions, f)
        except Exception as e:
            logger.debug(f"Failed to save scan cache: {e}")
"""

pattern_save_cache = re.compile(r'    def _save_scan_cache\(self, scan_type_label: str, results: List\[ScanResult\]\) -> None:.*?        except Exception as e:\n            logger\.debug\(f"Failed to save scan cache: \{e\}"\)', re.DOTALL)
text = pattern_save_cache.sub(save_cache_optimized.strip('\n'), text)


# 2. Fix scan_exact_value_parallel fallback
parallel_patch = """
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
            # Prepare scan parameters
            value_bytes = self._pack_value(value, value_type)
            type_size = self._get_type_size(value_type)

            # Helper function for the thread pool
            def run_parallel_scan(regions_to_scan):
                results_lock = threading.Lock()
                thread_results: List[ScanResult] = []

                def scan_region_task(region: MemoryRegion) -> List[ScanResult]:
                    local_results: List[ScanResult] = []
                    try:
                        if time.monotonic() - start_time > timeout:
                            return local_results
                        data = backend.read_bytes(region['address'], region['size'])
                        if not data or len(data) < type_size:
                            return local_results

                        pos = 0
                        while pos <= len(data) - type_size:
                            if time.monotonic() - start_time > timeout:
                                break
                            found_pos = data.find(value_bytes, pos)
                            if found_pos == -1:
                                break

                            address = region['address'] + found_pos
                            current_data = data[found_pos:found_pos + type_size]
                            if current_data:
                                current_value = self._unpack_value(current_data, value_type)
                                local_results.append(ScanResult(
                                    address=address,
                                    value=current_value,
                                    value_type=value_type
                                ))
                            pos = found_pos + 1
                    except Exception:
                        pass
                    return local_results

                remaining = max(0.1, timeout - (time.monotonic() - start_time))
                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    future_to_region = {executor.submit(scan_region_task, region): region for region in regions_to_scan}
                    for future in as_completed(future_to_region, timeout=remaining):
                        try:
                            region_results = future.result()
                            with results_lock:
                                thread_results.extend(region_results)
                        except Exception:
                            pass
                return thread_results

            # Execution logic
            if from_scratch and cached_regions:
                logger.info("Parallel scan using cached regions first...")
                self.results = run_parallel_scan(cached_regions)

                if not self.results:
                    logger.info("No matches in cached regions, falling back to full parallel scan")
                    regions = backend.get_prioritized_regions()
                    self.results = run_parallel_scan(regions)
            else:
                regions = backend.get_prioritized_regions()
                if not regions:
                    return 0
                self.results = run_parallel_scan(regions)

            if time.monotonic() - start_time > timeout:
                print(f"Parallel scan timed out after {timeout:.1f} seconds")

            # Save results to cache if it was a from_scratch scan, we found a reasonable amount, and we have a label
            if from_scratch and scan_type_label and len(self.results) > 0 and len(self.results) < 50000:
                self._save_scan_cache(scan_type_label, self.results)

            return len(self.results)
"""

pattern_parallel = re.compile(r'    def scan_exact_value_parallel\(.*?return len\(self\.results\)', re.DOTALL)
text = pattern_parallel.sub(parallel_patch.strip('\n'), text)

# Add import threading to the top of the file if not already present (it should be, but just in case)
if "import threading" not in text:
    text = "import threading\n" + text

with open('src/memory/scanner.py', 'w') as f:
    f.write(text)

import re

with open('src/memory/scanner.py', 'r') as f:
    text = f.read()

# I want to make sure I got the init_updates correctly inserted.
if "os.makedirs(self.cache_dir, exist_ok=True)" not in text:
    print("Missed cache_dir init")
    text = text.replace("self._freezer: Optional[\"MemoryFreezer\"] = None", "self._freezer: Optional[\"MemoryFreezer\"] = None\n        self.cache_dir = os.path.join(os.getcwd(), '.cache', 'scans')\n        os.makedirs(self.cache_dir, exist_ok=True)")

if "def _get_cache_path(" not in text:
    print("Missed cache methods")
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
            import json
            with open(cache_path, 'w') as f:
                json.dump(addresses, f)
        except Exception as e:
            logger.debug(f"Failed to save scan cache: {e}")

    def _load_scan_cache(self, value_type: ValueType) -> List[int]:
        \"\"\"Load cached scan addresses if available.\"\"\"
        cache_path = self._get_cache_path(value_type)
        import os
        import json
        if not cache_path or not os.path.exists(cache_path):
            return []

        try:
            with open(cache_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.debug(f"Failed to load scan cache: {e}")
            return []
"""
    text = text.replace("    def attach(self) -> bool:", cache_methods + "\n    def attach(self) -> bool:")

with open('src/memory/scanner.py', 'w') as f:
    f.write(text)

import re

with open("src/memory/advanced.py", "r") as f:
    content = f.read()

# Add cooldown_until field to FrozenAddress
content = re.sub(
    r'(error_count: int = 0)',
    r'\1\n    cooldown_until: float = 0.0',
    content
)

# Add properties for cooldown mechanism
content = re.sub(
    r'(def __init__\(self, editor: Optional\[Any\] = None\):)',
    r'\1\n        self._error_cooldown_duration: float = 10.0  # 10 seconds cooldown\n        self._consecutive_errors: int = 0\n        self._max_consecutive_errors: int = 5\n        self._global_cooldown_until: float = 0.0',
    content
)

# Update _freeze_loop to handle global cooldown
new_freeze_loop = """    def _freeze_loop(self) -> None:
        \"\"\"Main freeze loop - runs in background thread.\"\"\"
        while self._running:
            try:
                current_time = time.time()

                # Global circuit breaker
                if current_time < self._global_cooldown_until:
                    time.sleep(self._min_interval_ms / 1000.0)
                    continue
                else:
                    self._consecutive_errors = 0  # Reset on cooldown expiration

                with self._lock:
                    addresses = list(self.frozen.values())

                for frozen in addresses:
                    if not frozen.enabled:
                        continue

                    # Per-address circuit breaker
                    if current_time < frozen.cooldown_until:
                        continue

                    # Check if it's time to write
                    elapsed_ms = (current_time - frozen.last_write_time) * 1000
                    if elapsed_ms < frozen.interval_ms:
                        continue

                    self._write_frozen_value(frozen, current_time)

                # Sleep for minimum interval
                time.sleep(self._min_interval_ms / 1000.0)

            except Exception as e:
                logger.error("Freeze loop error: %s", e)
                time.sleep(0.1)"""

content = re.sub(
    r'    def _freeze_loop\(self\) -> None:.*?(?=    def _write_frozen_value)',
    new_freeze_loop + '\n\n',
    content,
    flags=re.DOTALL
)

# Update _write_frozen_value to implement circuit breaker
new_write_frozen = """    def _write_frozen_value(self, frozen: FrozenAddress, current_time: float) -> None:
        \"\"\"Write a frozen value to memory via the backend.\"\"\"
        if not self.editor:
            return

        try:
            fmt, size = self.VALUE_FORMATS[frozen.value_type]
            data = struct.pack(fmt, frozen.value)

            # Support both backend (write_bytes) and legacy (write_process_memory)
            if hasattr(self.editor, 'write_bytes'):
                success = self.editor.write_bytes(frozen.address, data)
                if success is False:
                    raise Exception("Memory write failed (possibly permission denied)")
            else:
                self._write_mem(frozen.address, data)

            frozen.last_write_time = current_time
            frozen.write_count += 1
            frozen.error_count = 0  # Reset on success
            self._consecutive_errors = 0 # Reset global consecutive errors

            if self._on_write:
                self._on_write(frozen.address, frozen.value)

        except Exception as e:
            frozen.error_count += 1
            self._consecutive_errors += 1

            # Per-address circuit breaker
            if frozen.error_count >= self._max_errors_per_address:
                logger.warning("Circuit breaker: Cooldown for 0x%08X after %d errors",
                             frozen.address, frozen.error_count)
                frozen.cooldown_until = current_time + self._error_cooldown_duration
                frozen.error_count = 0 # Reset count after entering cooldown

                if self._on_error:
                    self._on_error(frozen.address, str(e))

            # Global circuit breaker
            if self._consecutive_errors >= self._max_consecutive_errors:
                logger.error("Global circuit breaker tripped: %d consecutive write failures. Cooling down for %.1fs",
                             self._consecutive_errors, self._error_cooldown_duration)
                self._global_cooldown_until = current_time + self._error_cooldown_duration
                self._consecutive_errors = 0

            logger.debug("Freeze write error at 0x%08X: %s", frozen.address, e)"""

content = re.sub(
    r'    def _write_frozen_value\(self, frozen: FrozenAddress, current_time: float\) -> None:.*?(?=    def get_stats)',
    new_write_frozen + '\n\n',
    content,
    flags=re.DOTALL
)

with open("src/memory/advanced.py", "w") as f:
    f.write(content)

import re

with open('src/memory/advanced.py', 'r') as f:
    text = f.read()

# Replace _write_frozen_value to only write if read data is different
write_patch = """
    def _write_frozen_value(self, frozen: FrozenAddress, current_time: float) -> None:
        \"\"\"Write a frozen value to memory via the backend if it has changed (Lazy Write).\"\"\"
        if not self.editor:
            return

        try:
            fmt, size = self.VALUE_FORMATS[frozen.value_type]
            data = struct.pack(fmt, frozen.value)

            # Read first to check if value actually changed (Lazy Freezing)
            current_data = None
            if hasattr(self.editor, 'read_bytes'):
                current_data = self.editor.read_bytes(frozen.address, size)
            else:
                current_data = self._read_mem(frozen.address, size)

            # Only perform write if the memory doesn't match our target data
            if current_data != data:
                # Support both backend (write_bytes) and legacy (write_process_memory)
                if hasattr(self.editor, 'write_bytes'):
                    self.editor.write_bytes(frozen.address, data)
                else:
                    self._write_mem(frozen.address, data)

                frozen.write_count += 1
                if self._on_write:
                    self._on_write(frozen.address, frozen.value)

            # Update time and reset error regardless of whether we wrote or skipped
            frozen.last_write_time = current_time
            frozen.error_count = 0  # Reset on success

        except Exception as e:
            frozen.error_count += 1
"""

pattern = re.compile(r'    def _write_frozen_value\(self, frozen: FrozenAddress, current_time: float\) -> None:\n        """Write a frozen value to memory via the backend\."""\n        if not self\.editor:\n            return\n        \n        try:\n            fmt, size = self\.VALUE_FORMATS\[frozen\.value_type\]\n            data = struct\.pack\(fmt, frozen\.value\)\n            \n            # Support both backend \(write_bytes\) and legacy \(write_process_memory\)\n            if hasattr\(self\.editor, \'write_bytes\'\):\n                self\.editor\.write_bytes\(frozen\.address, data\)\n            else:\n                self\._write_mem\(frozen\.address, data\)\n            \n            frozen\.last_write_time = current_time\n            frozen\.write_count \+= 1\n            frozen\.error_count = 0  # Reset on success\n            \n            if self\._on_write:\n                self\._on_write\(frozen\.address, frozen\.value\)\n                \n        except Exception as e:\n            frozen\.error_count \+= 1', re.DOTALL)

match = pattern.search(text)
if match:
    text = text[:match.start()] + write_patch.strip('\n') + text[match.end():]
else:
    print("Could not find body to replace")

with open('src/memory/advanced.py', 'w') as f:
    f.write(text)

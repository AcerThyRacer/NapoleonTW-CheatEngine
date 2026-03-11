import sys

filepath = 'tests/test_memory.py'
with open(filepath, 'r') as f:
    content = f.read()

import re

content = re.sub(
    r"def test_get_best_backend_prefers_procmem_on_native_linux\(self\):.*?assert get_best_backend\(\) is ProcMemBackend",
    """def test_get_best_backend_prefers_procmem_on_native_linux(self):
        from src.memory.backend import DMABackend, get_best_backend

        with patch('src.memory.backend.get_platform', return_value='linux'), \\
             patch('src.memory.backend.is_proton', return_value=False):
            assert get_best_backend() is DMABackend""",
    content, flags=re.DOTALL
)

content = re.sub(
    r"def test_get_best_backend_prefers_pymem_on_proton\(self\):.*?assert get_best_backend\(\) is PymemBackend",
    """def test_get_best_backend_prefers_pymem_on_proton(self):
        from src.memory.backend import DMABackend, get_best_backend

        with patch('src.memory.backend.get_platform', return_value='linux'), \\
             patch('src.memory.backend.is_proton', return_value=True):
            assert get_best_backend() is DMABackend""",
    content, flags=re.DOTALL
)

with open(filepath, 'w') as f:
    f.write(content)

import re

with open('src/memory/scanner.py', 'r') as f:
    content = f.read()

# Replace get_readable_regions calls with get_prioritized_regions
content = content.replace("regions = backend.get_readable_regions()", "regions = backend.get_prioritized_regions()")
content = content.replace("regions = self.backend.get_readable_regions()", "regions = self.backend.get_prioritized_regions()")
content = content.replace("return self.backend.get_readable_regions()", "return self.backend.get_prioritized_regions()")

with open('src/memory/scanner.py', 'w') as f:
    f.write(content)

with open('src/memory/cheats.py', 'r') as f:
    content = f.read()

content = content.replace("regions = self.backend.get_readable_regions()", "regions = self.backend.get_prioritized_regions()")
content = content.replace("regions = self.memory_scanner.backend.get_readable_regions()", "regions = self.memory_scanner.backend.get_prioritized_regions()")

with open('src/memory/cheats.py', 'w') as f:
    f.write(content)

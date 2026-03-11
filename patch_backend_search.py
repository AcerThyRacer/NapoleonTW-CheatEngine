import re

with open('src/memory/backend.py', 'r') as f:
    text = f.read()

# Replace get_readable_regions with get_prioritized_regions in search_bytes
text = text.replace("        if regions is None:\n            regions = self.get_readable_regions()", "        if regions is None:\n            regions = self.get_prioritized_regions()")

with open('src/memory/backend.py', 'w') as f:
    f.write(text)

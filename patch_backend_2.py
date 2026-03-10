import re

with open('src/memory/backend.py', 'r') as f:
    content = f.read()

# Update backend methods to populate `name` when getting regions
# PymemBackend
content = content.replace("'address': module.lpBaseOfDll,\n                    'size': module.SizeOfImage,",
                          "'address': module.lpBaseOfDll,\n                    'size': module.SizeOfImage,\n                    'name': module.name,")

# ProcMemBackend
content = content.replace("regions.append({'address': start, 'size': end - start})",
                          "name = parts[-1] if len(parts) > 5 else ''\n                    regions.append({'address': start, 'size': end - start, 'name': name})")

with open('src/memory/backend.py', 'w') as f:
    f.write(content)

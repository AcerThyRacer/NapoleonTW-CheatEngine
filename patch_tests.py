with open('tests/test_memory.py', 'r') as f:
    content = f.read()

content = content.replace("def get_readable_regions(self):", "def get_prioritized_regions(self):")
content = content.replace("assert regions == [\n        {'address': 0x00400000, 'size': 0x52000},\n        {'address': 0x00653000, 'size': 0x1000},\n    ]", "assert regions == [\n        {'address': 0x00400000, 'size': 0x52000, 'name': '/bin/cat'},\n        {'address': 0x00653000, 'size': 0x1000, 'name': '/bin/cat'},\n    ]")

with open('tests/test_memory.py', 'w') as f:
    f.write(content)

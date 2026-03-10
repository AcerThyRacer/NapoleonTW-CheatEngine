import re

with open('src/memory/scanner.py', 'r') as f:
    text = f.read()

# Remove the duplicated lines
pattern = re.compile(r'        self\.results: List\[ScanResult\] = \[\]\n        self\.previous_values: Dict\[int, ScanValue\] = \{\}\n        self\.scan_history: List\[ScanHistoryEntry\] = \[\]\n\n')
text = pattern.sub('', text)

with open('src/memory/scanner.py', 'w') as f:
    f.write(text)

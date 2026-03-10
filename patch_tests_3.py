with open('tests/test_memory.py', 'r') as f:
    lines = f.readlines()

new_lines = []
for i, line in enumerate(lines):
    if line.strip() == "def get_prioritized_regions(self):":
        new_lines.append(line)
        # Assuming the next line is the start of the function body
    elif "raise AssertionError(\"search_bytes should use supplied regions\")" in line:
        new_lines.append("                raise AssertionError(\"search_bytes should use supplied regions\")\n")
    elif line.strip() == "def get_readable_regions(self):":
        new_lines.append("            def get_readable_regions(self):\n")
    else:
        new_lines.append(line)

with open('tests/test_memory.py', 'w') as f:
    f.writelines(new_lines)

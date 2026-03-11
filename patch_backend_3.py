with open('src/memory/backend.py', 'r') as f:
    lines = f.readlines()

new_lines = []
for line in lines:
    if line.strip() == "r['priority'] = priority":
        new_lines.append(line)
        new_lines.append("            if priority != 9:\n")
        new_lines.append("                prioritized.append(r)\n")
    elif line.strip() == "if priority < 9: # Skip priority 9 entirely if possible? For now, just include but sort last.":
        pass
    elif line.strip() == "prioritized.append(r)":
        pass
    else:
        new_lines.append(line)

with open('src/memory/backend.py', 'w') as f:
    f.writelines(new_lines)

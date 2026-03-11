import re

with open('src/memory/backend.py', 'r') as f:
    content = f.read()

# Add `name` and `priority` to MemoryRegion
content = content.replace('class MemoryRegion(TypedDict):', 'class MemoryRegion(TypedDict, total=False):')
content = content.replace('    size: int', "    size: int\n    name: str\n    priority: int")

# Add prioritize_regions method to MemoryBackend
prioritize_method = """
    def get_prioritized_regions(self) -> List[MemoryRegion]:
        \"\"\"Get readable regions sorted by likelihood of containing game data.\"\"\"
        regions = self.get_readable_regions()

        # Priority mapping: lower is better
        # 0: Game executable
        # 1: Game modules (.dll / .so related to game)
        # 2: Heap / anonymous memory
        # 3: System libraries
        # 9: Skip / Deprioritize (video drivers, etc.)

        prioritized = []
        for r in regions:
            name = r.get('name', '').lower()
            priority = 2 # default to heap/anonymous

            if not name:
                priority = 2
            elif 'napoleon.exe' in name or name.endswith('.exe'):
                priority = 0
            elif 'd3d' in name or 'nv' in name or 'amd' in name or 'ati' in name or 'vulkan' in name or 'opengl' in name or 'glx' in name:
                # Video driver / graphics memory, mostly useless to scan for gold/health
                priority = 9
            elif name.startswith('[heap]') or name.startswith('[stack]'):
                priority = 2
            elif '.dll' in name or '.so' in name:
                if 'system32' in name or 'syswow64' in name or 'windows' in name or '/usr/lib' in name or '/lib/' in name:
                    priority = 3
                else:
                    # Game specific DLLs
                    priority = 1
            elif name.startswith('/'):
                # Linux system paths
                if '/usr/lib' in name or '/lib' in name:
                    priority = 3
                else:
                    priority = 1

            r['priority'] = priority
            if priority < 9: # Skip priority 9 entirely if possible? For now, just include but sort last.
                prioritized.append(r)

        prioritized.sort(key=lambda r: (r['priority'], r['address']))
        return prioritized
"""

content = content.replace('        return results', '        return results\n' + prioritize_method)

with open('src/memory/backend.py', 'w') as f:
    f.write(content)

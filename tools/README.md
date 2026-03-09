# Standalone Tools

Command-line utilities for Napoleon Total War modding.

## Tools

### esf_dump.py - ESF File Dumper
```bash
python tools/esf_dump.py save_game.esf              # Dump tree
python tools/esf_dump.py save_game.esf --json        # JSON output
python tools/esf_dump.py save_game.esf --search gold # Search nodes
python tools/esf_dump.py save_game.esf --stats       # File statistics
```

### pack_tool.py - Pack File Utility
```bash
python tools/pack_tool.py list game.pack             # List contents
python tools/pack_tool.py extract game.pack -o ./out # Extract all
python tools/pack_tool.py info game.pack             # Show info
python tools/pack_tool.py create mod.pack -d ./files # Create pack
```

### address_calc.py - Memory Address Calculator
```bash
python tools/address_calc.py convert 0x004A5F2C        # Convert formats
python tools/address_calc.py offset 0x00400000 0x004A5F2C  # Calc offset
python tools/address_calc.py pack 999999 --type int32   # Pack to bytes
python tools/address_calc.py unpack "3F 42 0F 00"       # Unpack bytes
```

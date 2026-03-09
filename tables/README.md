# Cheat Tables

Pre-defined cheat tables for Napoleon Total War.

## Files

- `napoleon_v1_6.json` - Napoleon TW v1.6 (Steam) - pointer chains, AOB patterns, scan guides

## Table Format

Each table is a JSON file containing:
- **pointer_chains**: Module-relative pointer chains for stable address resolution
- **aob_patterns**: Array of Bytes patterns for finding game instructions
- **scan_guides**: Step-by-step guides for manual value scanning

## Creating Custom Tables

1. Use the memory scanner to find addresses
2. Use the pointer scanner to find pointer chains from the game module
3. Export as JSON using the CLI: `config_save tables/my_table.json`

## Notes

- Pointer offsets may change between game patches
- AOB patterns are more stable across patches
- Always verify addresses before writing values

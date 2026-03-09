#!/usr/bin/env python3
"""
Standalone ESF file dumper.
Extracts readable data from Napoleon Total War .esf save files.

Usage: python tools/esf_dump.py <file.esf> [--json] [--search NAME]
"""

import sys
import json
import argparse
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.files.esf_editor import ESFEditor, ESFNode


def dump_tree(node: ESFNode, indent: int = 0) -> None:
    """Print ESF node tree."""
    prefix = "  " * indent
    
    if node.children:
        print(f"{prefix}[{node.name}]")
        for child in node.children:
            dump_tree(child, indent + 1)
    else:
        if node.value is not None:
            print(f"{prefix}{node.name} = {node.value} ({node.node_type.value})")
        else:
            print(f"{prefix}{node.name}")


def dump_json(node: ESFNode) -> dict:
    """Convert node tree to JSON-serializable dict."""
    return node.to_dict()


def search_nodes(node: ESFNode, name: str) -> list:
    """Search for nodes by name."""
    return node.find_all_by_name(name)


def main():
    parser = argparse.ArgumentParser(description="ESF File Dumper")
    parser.add_argument("file", help="Path to .esf file")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--search", "-s", help="Search for node by name")
    parser.add_argument("--stats", action="store_true", help="Show file statistics only")
    
    args = parser.parse_args()
    
    editor = ESFEditor()
    if not editor.load_file(args.file):
        print(f"Failed to load: {args.file}", file=sys.stderr)
        sys.exit(1)
    
    if not editor.root:
        print("No data parsed", file=sys.stderr)
        sys.exit(1)
    
    if args.stats:
        def count_nodes(node):
            return 1 + sum(count_nodes(c) for c in node.children)
        
        total = count_nodes(editor.root)
        print(f"File: {args.file}")
        print(f"Total nodes: {total}")
        print(f"Root children: {len(editor.root.children)}")
        return
    
    if args.search:
        results = search_nodes(editor.root, args.search)
        if args.json:
            print(json.dumps([n.to_dict() for n in results], indent=2))
        else:
            print(f"Found {len(results)} nodes named '{args.search}':")
            for node in results:
                print(f"  {node}")
        return
    
    if args.json:
        print(json.dumps(dump_json(editor.root), indent=2))
    else:
        dump_tree(editor.root)


if __name__ == "__main__":
    main()

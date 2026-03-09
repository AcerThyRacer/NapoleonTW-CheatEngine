#!/usr/bin/env python3
"""
Standalone pack file utility.
Extract, list, and inspect Napoleon Total War .pack archives.

Usage:
  python tools/pack_tool.py list <file.pack> [--pattern GLOB]
  python tools/pack_tool.py extract <file.pack> [--output DIR] [--file PATH]
  python tools/pack_tool.py info <file.pack>
  python tools/pack_tool.py create <output.pack> --dir <source_dir> [--compress]
"""

import sys
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.pack.pack_parser import PackParser
from src.pack.mod_creator import ModCreator


def cmd_list(args):
    parser = PackParser()
    if not parser.load_file(args.file):
        sys.exit(1)
    
    files = parser.list_files(args.pattern)
    for f in files:
        info = parser.get_file_info(f)
        size = info.size if info else 0
        comp = " (compressed)" if info and info.is_compressed else ""
        print(f"  {f:60s} {size:>10,} bytes{comp}")
    
    print(f"\nTotal: {len(files)} files")


def cmd_extract(args):
    parser = PackParser()
    if not parser.load_file(args.file):
        sys.exit(1)
    
    if args.target:
        data = parser.extract_file(args.target)
        if data:
            out = Path(args.output) / Path(args.target).name if args.output else Path(args.target).name
            Path(out).parent.mkdir(parents=True, exist_ok=True)
            with open(out, 'wb') as f:
                f.write(data)
            print(f"Extracted: {out} ({len(data):,} bytes)")
        else:
            print(f"File not found: {args.target}")
    else:
        out_dir = args.output or './extracted'
        parser.extract_all(out_dir)


def cmd_info(args):
    parser = PackParser()
    if not parser.load_file(args.file):
        sys.exit(1)
    
    total_size = sum(f.size for f in parser.files.values())
    total_comp = sum(f.compressed_size for f in parser.files.values() if f.is_compressed)
    compressed_count = sum(1 for f in parser.files.values() if f.is_compressed)
    
    print(f"File:          {args.file}")
    print(f"Version:       {parser.version}")
    print(f"Total files:   {len(parser.files)}")
    print(f"Total size:    {total_size:,} bytes ({total_size / 1024 / 1024:.1f} MB)")
    print(f"Compressed:    {compressed_count} files ({total_comp:,} bytes)")
    
    # Show database tables
    tables = parser.get_database_tables()
    if tables:
        print(f"\nDatabase tables ({len(tables)}):")
        for t in tables[:20]:
            print(f"  {t}")


def cmd_create(args):
    creator = ModCreator()
    creator.set_mod_info(
        name=Path(args.output).stem,
        description=f"Mod created from {args.dir}"
    )
    creator.create_mod_pack(args.output, args.dir, compress=args.compress)


def main():
    parser = argparse.ArgumentParser(description="Pack File Utility")
    sub = parser.add_subparsers(dest='command', required=True)
    
    # list
    p_list = sub.add_parser('list', help='List pack contents')
    p_list.add_argument('file', help='Pack file path')
    p_list.add_argument('--pattern', '-p', help='Glob pattern filter')
    
    # extract
    p_extract = sub.add_parser('extract', help='Extract from pack')
    p_extract.add_argument('file', help='Pack file path')
    p_extract.add_argument('--output', '-o', help='Output directory')
    p_extract.add_argument('--target', '-t', help='Specific file to extract')
    
    # info
    p_info = sub.add_parser('info', help='Show pack info')
    p_info.add_argument('file', help='Pack file path')
    
    # create
    p_create = sub.add_parser('create', help='Create pack file')
    p_create.add_argument('output', help='Output pack file')
    p_create.add_argument('--dir', '-d', required=True, help='Source directory')
    p_create.add_argument('--compress', '-c', action='store_true')
    
    args = parser.parse_args()
    
    if args.command == 'list':
        cmd_list(args)
    elif args.command == 'extract':
        cmd_extract(args)
    elif args.command == 'info':
        cmd_info(args)
    elif args.command == 'create':
        cmd_create(args)


if __name__ == "__main__":
    main()

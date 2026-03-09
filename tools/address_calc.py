#!/usr/bin/env python3
"""
Memory address calculator utility.
Converts between different address formats and calculates offsets.

Usage: python tools/address_calc.py [command] [args]
"""

import sys
import struct
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


def cmd_convert(args):
    """Convert between address formats."""
    value = int(args.value, 0)  # auto-detect base
    
    print(f"  Decimal:     {value}")
    print(f"  Hex:         0x{value:08X}")
    print(f"  Hex (64):    0x{value:016X}")
    print(f"  Binary:      {value:032b}")
    print(f"  Bytes (LE):  {struct.pack('<I', value & 0xFFFFFFFF).hex(' ')}")
    print(f"  Bytes (BE):  {struct.pack('>I', value & 0xFFFFFFFF).hex(' ')}")


def cmd_offset(args):
    """Calculate offset between two addresses."""
    base = int(args.base, 0)
    target = int(args.target, 0)
    offset = target - base
    
    print(f"  Base:   0x{base:08X}")
    print(f"  Target: 0x{target:08X}")
    print(f"  Offset: 0x{offset:08X} ({offset:+d})")


def cmd_pack(args):
    """Pack a value into bytes."""
    value = float(args.value) if '.' in args.value else int(args.value, 0)
    
    formats = {
        'int8': '<b', 'int16': '<h', 'int32': '<i', 'int64': '<q',
        'uint8': '<B', 'uint16': '<H', 'uint32': '<I', 'uint64': '<Q',
        'float': '<f', 'double': '<d',
    }
    
    fmt = formats.get(args.type, '<i')
    
    try:
        data = struct.pack(fmt, value)
        print(f"  Value:  {value}")
        print(f"  Type:   {args.type}")
        print(f"  Bytes:  {data.hex(' ')}")
        print(f"  Size:   {len(data)} bytes")
    except struct.error as e:
        print(f"  Error: {e}")


def cmd_unpack(args):
    """Unpack bytes into a value."""
    hex_str = args.hex_bytes.replace(' ', '').replace('0x', '')
    data = bytes.fromhex(hex_str)
    
    print(f"  Bytes: {data.hex(' ')}")
    print(f"  Size:  {len(data)} bytes")
    print()
    
    if len(data) >= 1:
        print(f"  int8:   {struct.unpack('<b', data[:1])[0]}")
        print(f"  uint8:  {struct.unpack('<B', data[:1])[0]}")
    if len(data) >= 2:
        print(f"  int16:  {struct.unpack('<h', data[:2])[0]}")
        print(f"  uint16: {struct.unpack('<H', data[:2])[0]}")
    if len(data) >= 4:
        print(f"  int32:  {struct.unpack('<i', data[:4])[0]}")
        print(f"  uint32: {struct.unpack('<I', data[:4])[0]}")
        print(f"  float:  {struct.unpack('<f', data[:4])[0]}")
    if len(data) >= 8:
        print(f"  int64:  {struct.unpack('<q', data[:8])[0]}")
        print(f"  double: {struct.unpack('<d', data[:8])[0]}")


def main():
    parser = argparse.ArgumentParser(description="Memory Address Calculator")
    sub = parser.add_subparsers(dest='command', required=True)
    
    p_conv = sub.add_parser('convert', help='Convert address formats')
    p_conv.add_argument('value', help='Value (decimal, 0x hex, or 0b binary)')
    
    p_off = sub.add_parser('offset', help='Calculate offset')
    p_off.add_argument('base', help='Base address')
    p_off.add_argument('target', help='Target address')
    
    p_pack = sub.add_parser('pack', help='Pack value to bytes')
    p_pack.add_argument('value', help='Value to pack')
    p_pack.add_argument('--type', '-t', default='int32', help='Type (int32, float, etc)')
    
    p_unpack = sub.add_parser('unpack', help='Unpack bytes to values')
    p_unpack.add_argument('hex_bytes', help='Hex bytes (e.g., "FF 00 01 02")')
    
    args = parser.parse_args()
    
    if args.command == 'convert':
        cmd_convert(args)
    elif args.command == 'offset':
        cmd_offset(args)
    elif args.command == 'pack':
        cmd_pack(args)
    elif args.command == 'unpack':
        cmd_unpack(args)


if __name__ == "__main__":
    main()

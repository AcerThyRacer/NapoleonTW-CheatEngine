#!/usr/bin/env python3
"""
Napoleon Total War - Pointer Calibration Tool

This tool helps users calibrate pointer chains and validate AOB patterns
against their running instance of Napoleon Total War.
"""

import sys
import logging
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.memory.scanner import MemoryScanner
from src.memory.advanced import PointerResolver, AOBScanner, AOBPattern
from src.memory.signatures import SignatureDatabase

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger('calibrate')

from src.memory.process import ProcessManager

def connect_to_game():
    """Connect to the game process."""
    print("Looking for Napoleon Total War process...")
    process_manager = ProcessManager()
    scanner = MemoryScanner(process_manager=process_manager)
    if not scanner.attach():
        print("Error: Could not find or attach to 'napoleon.exe'. Please ensure the game is running.")
        sys.exit(1)

    print(f"Connected to PID {scanner.process_manager.pid}")
    return scanner

def prompt_float(prompt_text):
    """Prompt user for a float value."""
    while True:
        try:
            val = input(f"{prompt_text} (or 'q' to quit): ")
            if val.lower() == 'q':
                return None
            return float(val)
        except ValueError:
            print("Please enter a valid number.")

def prompt_int(prompt_text):
    """Prompt user for an integer value."""
    while True:
        try:
            val = input(f"{prompt_text} (or 'q' to quit): ")
            if val.lower() == 'q':
                return None
            return int(val)
        except ValueError:
            print("Please enter a valid integer.")

def calibrate_chain_interactive(resolver, chain_name, db):
    """Guide the user through calibrating a specific chain."""
    chain = db.get_chain(chain_name)
    if not chain:
        print(f"Error: Chain '{chain_name}' not found in database.")
        return False

    guide = db.get_scan_guide(chain_name)

    print(f"\n--- Calibrating '{chain_name}' ---")
    print(f"Description: {chain.description}")

    if guide:
        print("\nGuide:")
        for step in guide.get('steps', []):
            print(f"  {step}")
        print()

    # Ask for the known value
    val_type = chain.value_type
    prompt = f"Enter the current known value for '{chain_name}'"

    known_value = None
    if val_type in ['float', 'double']:
        known_value = prompt_float(prompt)
    else:
        known_value = prompt_int(prompt)

    if known_value is None:
        return False

    print(f"Attempting to calibrate {chain_name} to value {known_value}...")

    # Try calibrating
    calibrated_chain = resolver.calibrate_chain(chain_name, known_value, scan_range=0x2000)

    if calibrated_chain:
        print(f"Success! {chain_name} calibrated.")
        return True
    else:
        print(f"Failed to calibrate {chain_name}. Try entering the value again, or ensure the value hasn't changed.")
        return False

def validate_aob_patterns(scanner, db):
    """Validate all AOB patterns in the database."""
    print("\n--- Validating AOB Patterns ---")
    aob_scanner = AOBScanner(scanner.backend)

    patterns = db.list_patterns()
    valid_count = 0

    for name in patterns:
        entry = db.get_pattern_entry(name)
        if not entry:
            continue

        print(f"Scanning for {name} ({entry.pattern.pattern})... ", end='', flush=True)

        # Limit search to main module if possible, or use standard scan
        matches = aob_scanner.scan(entry.pattern, max_results=1, timeout=5.0)

        if matches:
            print(f"FOUND at 0x{matches[0]:08X}")
            valid_count += 1
        else:
            print("NOT FOUND")

    print(f"\nAOB Validation Complete: {valid_count}/{len(patterns)} patterns found.")

def main():
    print("==================================================")
    print("Napoleon Total War - Pointer Calibration Tool")
    print("==================================================")

    # Load signatures
    db = SignatureDatabase()
    count = db.load()
    if count == 0:
        print("Warning: No signatures loaded from tables/. Ensure you run this from the project root.")
    else:
        print(f"Loaded {count} signatures/chains from database.")

    # Connect to game
    scanner = connect_to_game()
    resolver = PointerResolver(editor=scanner.backend, pid=scanner.process_manager.pid)

    # Inject db into resolver so it has the known chains
    db.inject_into_resolver(resolver)

    while True:
        print("\nOptions:")
        print("1. Validate all AOB patterns")
        print("2. Calibrate Treasury (Gold)")
        print("3. Calibrate Unit Health")
        print("4. Save calibrations")
        print("5. Exit")

        choice = input("Select an option (1-5): ")

        if choice == '1':
            validate_aob_patterns(scanner, db)
        elif choice == '2':
            calibrate_chain_interactive(resolver, 'treasury', db)
        elif choice == '3':
            calibrate_chain_interactive(resolver, 'unit_health', db)
        elif choice == '4':
            if resolver.save_calibration():
                print("Calibrations saved successfully to pointer_chains.json")
            else:
                print("Failed to save calibrations.")
        elif choice == '5':
            break
        else:
            print("Invalid option.")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nExiting...")
        sys.exit(0)

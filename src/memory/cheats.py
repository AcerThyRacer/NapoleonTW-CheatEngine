"""
Pre-defined cheat implementations for Napoleon Total War.
Contains known memory addresses and patterns for common cheats.
"""

from enum import Enum
from typing import Optional, List, Dict, Any
from dataclasses import dataclass

from .scanner import MemoryScanner, ValueType, ScanResult
from .process import ProcessManager


class CheatType(Enum):
    """Types of cheats available."""
    INFINITE_GOLD = 'infinite_gold'
    UNLIMITED_MOVEMENT = 'unlimited_movement'
    INSTANT_CONSTRUCTION = 'instant_construction'
    FAST_RESEARCH = 'fast_research'
    GOD_MODE = 'god_mode'
    UNLIMITED_AMMO = 'unlimited_ammo'
    HIGH_MORALE = 'high_morale'
    INFINITE_STAMINA = 'infinite_stamina'
    ONE_HIT_KILL = 'one_hit_kill'
    SUPER_SPEED = 'super_speed'


@dataclass
class CheatDefinition:
    """Definition of a cheat."""
    cheat_type: CheatType
    name: str
    description: str
    value_type: ValueType
    default_value: Any
    cheat_value: Any
    mode: str  # 'campaign' or 'battle'
    scan_pattern: Optional[Dict] = None  # Initial scan parameters


class CheatManager:
    """
    Manages cheat activation and deactivation.
    Auto-resolves addresses via pointer chains, AOB scanning, or cached addresses.
    """
    
    def __init__(self, memory_scanner: MemoryScanner):
        """
        Initialize cheat manager.
        
        Args:
            memory_scanner: MemoryScanner instance
        """
        self.memory_scanner = memory_scanner
        self.active_cheats: Dict[CheatType, Dict] = {}
        self.frozen_addresses: Dict[int, Any] = {}
        self._resolved_addresses: Dict[CheatType, int] = {}
        self._pointer_resolver = None
        self._aob_scanner = None
        
        # Define known cheat patterns
        self.cheat_definitions = self._init_cheat_definitions()
    
    def _init_cheat_definitions(self) -> List[CheatDefinition]:
        """Initialize cheat definitions with known patterns."""
        return [
            # Campaign Cheats
            CheatDefinition(
                cheat_type=CheatType.INFINITE_GOLD,
                name="Infinite Gold",
                description="Set treasury to maximum value",
                value_type=ValueType.INT_32,
                default_value=0,
                cheat_value=999999,
                mode='campaign',
                scan_pattern={
                    'initial_scan': {'value': None, 'type': 'unknown'},
                    'description': 'Scan for unknown value, spend gold, scan for decreased value'
                }
            ),
            CheatDefinition(
                cheat_type=CheatType.UNLIMITED_MOVEMENT,
                name="Unlimited Movement",
                description="Freeze movement points",
                value_type=ValueType.FLOAT,
                default_value=1.0,
                cheat_value=999.0,
                mode='campaign',
            ),
            CheatDefinition(
                cheat_type=CheatType.INSTANT_CONSTRUCTION,
                name="Instant Construction",
                description="Set construction timers to 0",
                value_type=ValueType.INT_32,
                default_value=None,
                cheat_value=0,
                mode='campaign',
            ),
            CheatDefinition(
                cheat_type=CheatType.FAST_RESEARCH,
                name="Fast Research",
                description="Set research timers to 1 turn",
                value_type=ValueType.INT_32,
                default_value=None,
                cheat_value=1,
                mode='campaign',
            ),
            
            # Battle Cheats
            CheatDefinition(
                cheat_type=CheatType.GOD_MODE,
                name="God Mode",
                description="Set unit health to maximum",
                value_type=ValueType.FLOAT,
                default_value=100.0,
                cheat_value=9999.0,
                mode='battle',
            ),
            CheatDefinition(
                cheat_type=CheatType.UNLIMITED_AMMO,
                name="Unlimited Ammo",
                description="Freeze ammo count",
                value_type=ValueType.INT_32,
                default_value=None,
                cheat_value=999,
                mode='battle',
            ),
            CheatDefinition(
                cheat_type=CheatType.HIGH_MORALE,
                name="High Morale",
                description="Set morale to maximum",
                value_type=ValueType.FLOAT,
                default_value=1.0,
                cheat_value=2.0,
                mode='battle',
            ),
            CheatDefinition(
                cheat_type=CheatType.INFINITE_STAMINA,
                name="Infinite Stamina",
                description="Prevent stamina depletion",
                value_type=ValueType.FLOAT,
                default_value=1.0,
                cheat_value=999.0,
                mode='battle',
            ),
            CheatDefinition(
                cheat_type=CheatType.ONE_HIT_KILL,
                name="One-Hit Kill",
                description="Maximize damage dealt",
                value_type=ValueType.FLOAT,
                default_value=1.0,
                cheat_value=999.0,
                mode='battle',
            ),
            CheatDefinition(
                cheat_type=CheatType.SUPER_SPEED,
                name="Super Speed",
                description="Increase game speed",
                value_type=ValueType.FLOAT,
                default_value=1.0,
                cheat_value=5.0,
                mode='battle',
            ),
        ]
    
    def activate_cheat(self, cheat_type: CheatType, address: Optional[int] = None) -> bool:
        """
        Activate a cheat. Attempts to auto-resolve the address if not provided.
        
        Resolution order:
        1. Explicit address (if provided)
        2. Previously cached address for this cheat
        3. Pointer chain resolution (from known chains)
        4. Logs instructions for manual scanning
        
        Args:
            cheat_type: Type of cheat to activate
            address: Optional memory address (if known)
            
        Returns:
            bool: True if activated successfully
        """
        cheat_def = self._get_cheat_definition(cheat_type)
        if not cheat_def:
            print(f"Unknown cheat type: {cheat_type}")
            return False
        
        # Step 1: Use explicit address
        if not address:
            # Step 2: Check cached addresses
            address = self._resolved_addresses.get(cheat_type)
        
        if not address:
            # Step 3: Try pointer chain resolution
            address = self._try_resolve_pointer_chain(cheat_type)
        
        if address:
            # Read original value before writing
            original = self.memory_scanner.read_value(address, cheat_def.value_type)
            
            # Write the cheat value
            success = self.memory_scanner.write_value(
                address,
                cheat_def.cheat_value,
                cheat_def.value_type
            )
            
            if success:
                # Also freeze the value so the game can't overwrite it
                self.memory_scanner.freeze_value(address, cheat_def.cheat_value, cheat_def.value_type)
                
                self.active_cheats[cheat_type] = {
                    'address': address,
                    'definition': cheat_def,
                    'original_value': original,
                }
                # Cache the resolved address for future use
                self._resolved_addresses[cheat_type] = address
                print(f"✓ {cheat_def.name} ACTIVATED at 0x{address:08X}")
            
            return success
        else:
            print(f"⚠ Could not auto-resolve address for {cheat_def.name}.")
            print(f"  Use memory scanner to find it, then pass the address.")
            instructions = self.get_cheat_instructions(cheat_type)
            print(f"  Instructions:\n{instructions}")
            return False
    
    def _try_resolve_pointer_chain(self, cheat_type: CheatType) -> Optional[int]:
        """
        Attempt to resolve a cheat's address via pointer chains.
        """
        if not self.memory_scanner.is_attached():
            return None
        
        from .advanced import PointerResolver
        
        if self._pointer_resolver is None:
            self._pointer_resolver = PointerResolver(
                editor=self.memory_scanner.backend,
                pid=self.memory_scanner.process_manager.pid
            )
        
        # Map cheat types to known chain names
        chain_map = {
            CheatType.INFINITE_GOLD: 'treasury',
            CheatType.UNLIMITED_MOVEMENT: 'movement_points',
        }
        
        chain_name = chain_map.get(cheat_type)
        if chain_name and chain_name in PointerResolver.KNOWN_CHAINS:
            chain = PointerResolver.KNOWN_CHAINS[chain_name]
            address = self._pointer_resolver.resolve_chain(chain)
            if address:
                # Verify the address is readable
                test_val = self.memory_scanner.read_value(address, ValueType.INT_32)
                if test_val is not None:
                    print(f"  ✓ Resolved {chain_name} via pointer chain → 0x{address:08X}")
                    return address
        
        return None
    
    def set_address(self, cheat_type: CheatType, address: int) -> None:
        """
        Manually set/cache a resolved address for a cheat type.
        Use this after finding an address with the memory scanner.
        """
        self._resolved_addresses[cheat_type] = address
        print(f"Cached address for {cheat_type.value}: 0x{address:08X}")
    
    def deactivate_cheat(self, cheat_type: CheatType) -> bool:
        """
        Deactivate a cheat. Unfreezes the address and optionally restores original value.
        
        Args:
            cheat_type: Type of cheat to deactivate
            
        Returns:
            bool: True if deactivated successfully
        """
        if cheat_type not in self.active_cheats:
            return False
        
        cheat_info = self.active_cheats[cheat_type]
        address = cheat_info['address']
        
        # Unfreeze the address first
        self.memory_scanner.unfreeze_value(address)
        
        # Restore original value if we have it
        if cheat_info.get('original_value') is not None:
            original_value = cheat_info['original_value']
            value_type = cheat_info['definition'].value_type
            self.memory_scanner.write_value(address, original_value, value_type)
        
        cheat_name = cheat_info['definition'].name
        del self.active_cheats[cheat_type]
        print(f"✗ {cheat_name} DEACTIVATED")
        return True
    
    def toggle_cheat(self, cheat_type: CheatType, address: Optional[int] = None) -> bool:
        """
        Toggle a cheat on/off.
        
        Args:
            cheat_type: Type of cheat to toggle
            address: Optional memory address
            
        Returns:
            bool: True if toggled successfully
        """
        if cheat_type in self.active_cheats:
            return self.deactivate_cheat(cheat_type)
        else:
            return self.activate_cheat(cheat_type, address)
    
    def is_cheat_active(self, cheat_type: CheatType) -> bool:
        """
        Check if a cheat is active.
        
        Args:
            cheat_type: Type of cheat
            
        Returns:
            bool: True if active
        """
        return cheat_type in self.active_cheats
    
    def get_active_cheats(self) -> List[CheatType]:
        """
        Get list of active cheats.
        
        Returns:
            List[CheatType]: List of active cheat types
        """
        return list(self.active_cheats.keys())
    
    def deactivate_all_cheats(self) -> None:
        """
        Deactivate all active cheats.
        """
        for cheat_type in list(self.active_cheats.keys()):
            self.deactivate_cheat(cheat_type)
    
    def _get_cheat_definition(self, cheat_type: CheatType) -> Optional[CheatDefinition]:
        """
        Get cheat definition.
        
        Args:
            cheat_type: Type of cheat
            
        Returns:
            Optional[CheatDefinition]: Cheat definition or None
        """
        for cheat_def in self.cheat_definitions:
            if cheat_def.cheat_type == cheat_type:
                return cheat_def
        return None
    
    def get_cheat_instructions(self, cheat_type: CheatType) -> str:
        """
        Get instructions for finding a cheat address.
        
        Args:
            cheat_type: Type of cheat
            
        Returns:
            str: Instructions string
        """
        cheat_def = self._get_cheat_definition(cheat_type)
        if not cheat_def:
            return "Unknown cheat type"
        
        if cheat_type == CheatType.INFINITE_GOLD:
            return (
                "1. Note your current gold amount\n"
                "2. Scan for exact value (4 Bytes)\n"
                "3. Spend some gold in-game\n"
                "4. Scan for decreased value\n"
                "5. Repeat until 1-3 addresses remain\n"
                "6. Change value to 999999"
            )
        elif cheat_type == CheatType.GOD_MODE:
            return (
                "1. Start a battle\n"
                "2. Note a unit's health\n"
                "3. Scan for exact value (Float)\n"
                "4. Let the unit take damage\n"
                "5. Scan for decreased value\n"
                "6. Repeat until address found\n"
                "7. Freeze or change value to 9999"
            )
        else:
            return f"Use memory scanner to find {cheat_def.name} address"
    
    def get_all_cheats(self) -> List[Dict]:
        """
        Get all available cheats.
        
        Returns:
            List[Dict]: List of cheat information dictionaries
        """
        return [
            {
                'type': cheat.cheat_type.value,
                'name': cheat.name,
                'description': cheat.description,
                'mode': cheat.mode,
                'value_type': cheat.value_type.value,
                'active': cheat.cheat_type in self.active_cheats,
            }
            for cheat in self.cheat_definitions
        ]

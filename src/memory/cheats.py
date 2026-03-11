"""
Pre-defined cheat implementations for Napoleon Total War.
Contains real cheat metadata, pointer-chain resolution, signature scanning,
and patch / code-cave activation helpers.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
import json
import logging
import struct
import threading
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field

from .scanner import MemoryScanner, ValueType
from src.utils.crash_recovery import CrashRecoveryManager

logger = logging.getLogger('napoleon.memory.cheats')

_TABLES_DIR = Path(__file__).resolve().parents[2] / 'tables'
_DEFAULT_ADDRESS_EXPORT = _TABLES_DIR / 'napoleon_addresses.json'


class CheatType(Enum):
    """Types of cheats available."""

    # Original cheats
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

    # Extended campaign cheats
    INFINITE_ACTION_POINTS = 'infinite_action_points'
    MAX_RESEARCH_POINTS = 'max_research_points'
    INSTANT_AGENT_TRAINING = 'instant_agent_training'
    FREE_DIPLOMATIC_ACTIONS = 'free_diplomatic_actions'
    INVISIBLE_ARMIES = 'invisible_armies'

    # Extended battle cheats
    INFINITE_MORALE = 'infinite_morale'
    INSTANT_RELOAD = 'instant_reload'
    RANGE_BOOST = 'range_boost'
    SPEED_BOOST = 'speed_boost'
    INFINITE_UNIT_HEALTH = 'infinite_unit_health'

    # Strategic cheats
    INSTANT_VICTORY = 'instant_victory'
    MAX_PUBLIC_ORDER = 'max_public_order'
    ZERO_ATTRITION = 'zero_attrition'
    FREE_UPGRADES = 'free_upgrades'

    # New cheat categories (PR #29)
    # AI Manipulation
    ENHANCED_AI = 'enhanced_ai'
    AI_DISABLED = 'ai_disabled'
    PERFECT_AI_ACCURACY = 'perfect_ai_accuracy'

    # Time Control
    TIME_SCALE = 'time_scale'
    PAUSE_GAME = 'pause_game'
    FAST_FORWARD = 'fast_forward'

    # Unit Spawning/Modification
    SPAWN_ELITE_GUARD = 'spawn_elite_guard'
    MAX_UNIT_VETERANCY = 'max_unit_veterancy'
    INSTANT_UNIT_RECRUITMENT = 'instant_unit_recruitment'

    # Weather & Environment
    CLEAR_WEATHER = 'clear_weather'
    FOG_IMMUNITY = 'fog_immunity'
    TERRAIN_ADVANTAGE = 'terrain_advantage'

    # Camera & Visual
    FREE_CAMERA = 'free_camera'
    REVEAL_MAP = 'reveal_map'
    ENHANCED_VISIBILITY = 'enhanced_visibility'

    # Additional cheats from PR #24
    INSTANT_RECRUITMENT = 'instant_recruitment'
    NO_FOG_OF_WAR = 'no_fog_of_war'
    UNLIMITED_AGENTS = 'unlimited_agents'


@dataclass
class CheatDefinition:
    """Definition of a cheat."""

    cheat_type: CheatType
    name: str
    description: str
    value_type: ValueType
    default_value: Any
    cheat_value: Any
    mode: str  # 'campaign', 'battle', or 'strategic'
    scan_pattern: Optional[Dict] = None
    pointer_chains: List[str] = field(default_factory=list)
    aob_patterns: List[str] = field(default_factory=list)
    scan_key: Optional[str] = None
    patch_mode: str = 'freeze'  # freeze, nop, code_cave
    overwrite_size: int = 5


@dataclass
class MemoryPatch:
    """Represents a block of bytes patched in process memory."""

    address: int
    original_bytes: bytes
    patched_bytes: bytes
    description: str = ""


from typing import Callable

@dataclass
class HookInfo:
    """Information about a specific hook in a chain."""
    hook_id: str
    payload_builder: Callable[[int], bytes]
    priority: int = 50
    active: bool = True
    install_order: int = 0

class HookManager:
    """Manages chains of hooks at specific memory addresses.

    When multiple hooks target the same address, it chains them together
    in priority order. It also verifies that the game hasn't overwritten
    the hook entry points.
    """

    def __init__(self, backend: Any):
        self.backend = backend
        # Mapping from site address to a list of HookInfo
        self.hooks: Dict[int, List[HookInfo]] = {}
        # Mapping from site address to the original bytes
        self.original_bytes: Dict[int, bytes] = {}
        # Mapping from site address to the current injected patch details
        self.active_patches: Dict[int, List[MemoryPatch]] = {}
        # Mapping from site address to its trampoline address
        self.trampolines: Dict[int, int] = {}
        self._next_install_order: int = 0

    def add_hook(self, address: int, hook_id: str, payload_builder: Callable[[int], bytes], overwrite_size: int, priority: int = 50) -> bool:
        """Add a hook to an address. If the address is already hooked, it will be chained.

        The payload_builder is a function that takes the trampoline address (or 0 if none created)
        and returns the hook's payload bytes. This allows hooks to CALL the original instructions.
        """
        if not self.backend:
            return False

        if address not in self.original_bytes:
            orig = self.backend.read_bytes(address, overwrite_size)
            if orig is None or len(orig) != overwrite_size:
                return False
            self.original_bytes[address] = orig
            self.hooks[address] = []

        # Remove existing hook with same ID if it exists
        self.hooks[address] = [h for h in self.hooks[address] if h.hook_id != hook_id]

        new_hook = HookInfo(
            hook_id=hook_id,
            payload_builder=payload_builder,
            priority=priority,
            install_order=self._next_install_order
        )
        self._next_install_order += 1
        self.hooks[address].append(new_hook)

        if len(self.hooks[address]) > 1:
            logger.warning(f"Conflict detected: Multiple hooks target address 0x{address:X}.")
            logger.warning("Consider adjusting priorities if they conflict.")
            # Log installation order and priorities
            for h in sorted(self.hooks[address], key=lambda x: x.install_order):
                logger.warning(f"  Hook '{h.hook_id}' - Priority: {h.priority}, Install Order: {h.install_order}")

        # Sort by priority (higher priority first)
        self.hooks[address].sort(key=lambda x: x.priority, reverse=True)

        return self._apply_hooks(address, overwrite_size)

    def remove_hook(self, address: int, hook_id: str, overwrite_size: int) -> bool:
        """Remove a specific hook from an address."""
        if address not in self.hooks:
            return False

        self.hooks[address] = [h for h in self.hooks[address] if h.hook_id != hook_id]

        if not self.hooks[address]:
            # No hooks left, restore original bytes
            return self.remove_all_hooks(address)

        return self._apply_hooks(address, overwrite_size)

    def remove_all_hooks(self, address: int) -> bool:
        """Remove all hooks from an address and restore original bytes."""
        if address not in self.original_bytes:
            return True

        if address in self.active_patches:
            for patch in reversed(self.active_patches[address]):
                if patch.address == address:
                    self.backend.write_bytes(address, self.original_bytes[address])
                else:
                    # Restore cave with original zeros/int3s
                    self.backend.write_bytes(patch.address, patch.original_bytes)
            del self.active_patches[address]

        # Clean up trampoline if any
        if address in self.trampolines:
            trampoline_addr = self.trampolines.pop(address)
            # The trampoline was allocated by find_code_cave, ideally we would restore its zero/int3 padding
            # For simplicity, we just forget about it here. The game won't jump to it anymore.

        if address in self.hooks:
            del self.hooks[address]
        if address in self.original_bytes:
            del self.original_bytes[address]
        return True

    def _apply_hooks(self, address: int, overwrite_size: int) -> bool:
        """Apply the chain of hooks for an address."""
        if address in self.active_patches:
            # Clean up old patches
            for patch in reversed(self.active_patches[address]):
                if patch.address != address:  # Keep the site clean for a moment
                    self.backend.write_bytes(patch.address, patch.original_bytes)

        active_hooks = [h for h in self.hooks[address] if h.active]
        if not active_hooks:
            self.backend.write_bytes(address, self.original_bytes[address])
            if address in self.active_patches:
                del self.active_patches[address]
            return True

        injector = CodeCaveInjector(self.backend)

        # Create trampoline if it doesn't exist
        if address not in self.trampolines:
            trampoline = injector.create_trampoline(address, overwrite_size)
            if trampoline is None:
                return False
            self.trampolines[address] = trampoline

        trampoline_addr = self.trampolines[address]

        combined_payload = b""
        for hook in active_hooks:
            combined_payload += hook.payload_builder(trampoline_addr)

        patches = injector.inject(
            site_address=address,
            payload=combined_payload,
            overwrite_size=overwrite_size,
        )

        if patches:
            self.active_patches[address] = patches
            return True
        return False

    def validate_hooks(self, repair: bool = True) -> Dict[int, str]:
        """Validate all active hooks to check if they have been overwritten.

        Args:
            repair: If True, attempts to auto-restore overwritten hooks.

        Returns a dict of addresses mapped to their status (e.g. 'restored', 'corrupted', 'ok').
        """
        hook_status = {}
        if not self.backend:
            return hook_status

        for address, patches in self.active_patches.items():
            if not patches:
                continue

            status = 'ok'
            corrupted = False

            # Check trampoline and code caves
            for patch in patches:
                current_bytes = self.backend.read_bytes(patch.address, len(patch.patched_bytes))
                if current_bytes != patch.patched_bytes:
                    corrupted = True
                    break

            # Also check trampoline if it exists
            if not corrupted and address in self.trampolines:
                trampoline_addr = self.trampolines[address]
                overwrite_size = len(self.original_bytes[address])
                trampoline_size = overwrite_size + 5
                current_trampoline = self.backend.read_bytes(trampoline_addr, trampoline_size)
                # Ensure the original instruction matches the first part
                # and the jump matches the second part
                if current_trampoline is None or len(current_trampoline) != trampoline_size:
                    corrupted = True
                else:
                    # Validate jump back instruction
                    expected_jump = CodeCaveInjector.build_relative_jump(
                        trampoline_addr + overwrite_size,
                        address + overwrite_size,
                    )
                    expected_trampoline = self.original_bytes[address] + expected_jump
                    if current_trampoline != expected_trampoline:
                        corrupted = True

            if corrupted:
                logger.warning(f"Hook or trampoline at 0x{address:X} was corrupted!")
                if repair:
                    logger.info(f"Auto-restoring hook at 0x{address:X}...")
                    overwrite_size = len(self.original_bytes[address])
                    if self._apply_hooks(address, overwrite_size):
                        status = 'restored'
                    else:
                        status = 'corrupted'
                else:
                    status = 'corrupted'

            hook_status[address] = status

        return hook_status

class CodeCaveInjector:
    """Minimal code-cave injector for complex instruction redirection cheats."""

    def __init__(self, backend: Any):
        self.backend = backend

    @staticmethod
    def build_relative_jump(source_address: int, target_address: int) -> bytes:
        """Build a near JMP rel32 instruction."""
        displacement = target_address - (source_address + 5)
        return b'\xE9' + struct.pack('<i', displacement)

    def find_code_cave(
        self,
        minimum_size: int,
        fill_bytes: tuple[int, ...] = (0x00, 0xCC),
    ) -> Optional[int]:
        """Locate a simple code cave in readable regions using zero/INT3 padding."""
        if not self.backend or minimum_size <= 0:
            return None

        for region in self.backend.get_readable_regions():
            data = self.backend.read_bytes(region['address'], region['size'])
            if not data or len(data) < minimum_size:
                continue

            run_start = None
            run_length = 0
            for index, byte in enumerate(data):
                if byte in fill_bytes:
                    if run_start is None:
                        run_start = index
                    run_length += 1
                    if run_length >= minimum_size:
                        return region['address'] + run_start
                else:
                    run_start = None
                    run_length = 0

        return None

    def inject(
        self,
        site_address: int,
        payload: bytes,
        overwrite_size: int = 5,
        cave_address: Optional[int] = None,
    ) -> Optional[List[MemoryPatch]]:
        """Inject a payload into a code cave and redirect execution to it."""
        if not self.backend or overwrite_size < 5 or not payload:
            return None

        cave_size = len(payload) + 5
        cave_address = cave_address or self.find_code_cave(cave_size)
        if cave_address is None:
            return None

        original_site = self.backend.read_bytes(site_address, overwrite_size)
        original_cave = self.backend.read_bytes(cave_address, cave_size)
        if original_site is None or len(original_site) != overwrite_size:
            return None
        if original_cave is None or len(original_cave) != cave_size:
            return None

        cave_payload = payload + self.build_relative_jump(
            cave_address + len(payload),
            site_address + overwrite_size,
        )
        site_patch = self.build_relative_jump(site_address, cave_address)
        if overwrite_size > 5:
            site_patch += b'\x90' * (overwrite_size - 5)

        if not self.backend.write_bytes(cave_address, cave_payload):
            return None
        if not self.backend.write_bytes(site_address, site_patch):
            self.backend.write_bytes(cave_address, original_cave)
            return None

        return [
            MemoryPatch(
                address=cave_address,
                original_bytes=original_cave,
                patched_bytes=cave_payload,
                description='code cave payload',
            ),
            MemoryPatch(
                address=site_address,
                original_bytes=original_site,
                patched_bytes=site_patch,
                description='jmp to code cave',
            ),
        ]

    def create_trampoline(
        self,
        site_address: int,
        overwrite_size: int,
    ) -> Optional[int]:
        """Creates a callable trampoline containing the original instructions.

        Returns the memory address of the trampoline. The caller can CALL or JMP
        to this address to execute the original instructions, which will then JMP
        back to the instruction following the hook.
        """
        if not self.backend or overwrite_size < 5:
            return None

        original_site = self.backend.read_bytes(site_address, overwrite_size)
        if original_site is None or len(original_site) != overwrite_size:
            return None

        trampoline_size = overwrite_size + 5
        trampoline_address = self.find_code_cave(trampoline_size)
        if trampoline_address is None:
            return None

        trampoline_payload = original_site + self.build_relative_jump(
            trampoline_address + overwrite_size,
            site_address + overwrite_size,
        )

        if not self.backend.write_bytes(trampoline_address, trampoline_payload):
            return None

        return trampoline_address


class CheatManager:
    """
    Manages cheat activation and deactivation.
    Auto-resolves addresses via pointer chains, AOB scanning, or cached addresses.
    """

    def __init__(self, memory_scanner: MemoryScanner):
        """Initialize cheat manager."""
        self.memory_scanner = memory_scanner
        self.active_cheats: Dict[CheatType, Dict[str, Any]] = {}
        self.frozen_addresses: Dict[int, Any] = {}
        self._resolved_addresses: Dict[CheatType, int] = {}
        self._pointer_resolver = None
        self._aob_scanner = None
        self.signature_db = None
        self.saved_cheat_state: List[CheatType] = []
        self._healing_lock = threading.Lock()
        self._healing_in_progress = set()
        try:
            from .ultra_hook import UltraReliableHookManager
            self.hook_manager = UltraReliableHookManager(self.memory_scanner.backend, self.memory_scanner.process_manager)
        except ImportError:
            self.hook_manager = HookManager(self.memory_scanner.backend)

        self.crash_recovery = CrashRecoveryManager()
        self._validation_thread = None
        self._stop_validation = threading.Event()

        self._load_signatures()
        self.cheat_definitions = self._init_cheat_definitions()

        # Wire up the freezer healing callback if scanner is ready
        if hasattr(self.memory_scanner, '_freezer') and self.memory_scanner._freezer:
            self.memory_scanner._freezer.set_callbacks(on_error=self._on_freeze_error)

        self.start_validation_thread()

    def start_validation_thread(self):
        """Starts a background thread to continuously validate and auto-restore hooks."""
        if self._validation_thread and self._validation_thread.is_alive():
            return

        self._stop_validation.clear()
        self._validation_thread = threading.Thread(target=self._validation_loop, daemon=True)
        self._validation_thread.start()

    def stop_validation_thread(self):
        """Stops the background validation thread."""
        self._stop_validation.set()
        if self._validation_thread:
            self._validation_thread.join(timeout=2.0)
            self._validation_thread = None

    def _validation_loop(self):
        import time
        while not self._stop_validation.is_set():
            if self.memory_scanner.is_attached():
                self.validate_hooks(repair=True)
            time.sleep(5.0)

    def _on_freeze_error(self, address: int, error_msg: str) -> None:
        """Called when the memory freezer repeatedly fails to write to an address."""
        # Find which cheat owns this address
        target_cheat = None
        for cheat_type, cheat_info in self.active_cheats.items():
            if cheat_info.get('address') == address:
                target_cheat = cheat_type
                break

        if target_cheat:
            logger.warning("Freeze error for %s at 0x%08X: %s. Initiating self-healing.", target_cheat.value, address, error_msg)
            # Run the healing process in a background thread to not block the freezer loop
            threading.Thread(target=self.heal_cheat, args=(target_cheat,), daemon=True).start()

    def heal_cheat(self, cheat_type: CheatType) -> bool:
        """
        Self-healing pointer system.
        Suspends the cheat, attempts an AOB re-scan to find the new address, and resumes if found.
        """
        with self._healing_lock:
            if cheat_type in self._healing_in_progress:
                return False
            self._healing_in_progress.add(cheat_type)

        logger.info("Self-healing initiated for %s", cheat_type.value)
        success = False
        try:
            # 1. Suspend the cheat temporarily
            if self.is_cheat_active(cheat_type):
                logger.info("Suspending %s for healing", cheat_type.value)
                # We do a 'soft' deactivate so we don't clear the user's intent to have it on
                self.deactivate_cheat(cheat_type)

            # Clear cached address so it forces a re-resolve
            if cheat_type in self._resolved_addresses:
                del self._resolved_addresses[cheat_type]

            # 2. Try to activate it again. activate_cheat will automatically
            # try to resolve the pointer chain or AOB scan again.
            if self.activate_cheat(cheat_type):
                logger.info("Successfully healed %s! New address cached.", cheat_type.value)
                success = True
            else:
                logger.error("Self-healing failed for %s. Could not resolve new address.", cheat_type.value)

        finally:
            with self._healing_lock:
                self._healing_in_progress.remove(cheat_type)

        return success

    def validate_hooks(self, repair: bool = True) -> Dict[int, str]:
        """Periodic validation of active hooks. This should be called from the main loop."""
        if self.hook_manager:
            status = self.hook_manager.validate_hooks(repair=repair)
            for addr, s in status.items():
                if s == 'restored':
                    logger.warning(f"Hook at 0x{addr:X} auto-restored.")
            return status
        return {}

    def _load_signatures(self) -> None:
        """Load the JSON-backed pointer-chain and AOB signature database."""
        try:
            from .advanced import AOBScanner, PointerResolver
            from .signatures import SignatureDatabase

            self.signature_db = SignatureDatabase()
            self.signature_db.load()
            self.signature_db.inject_into_scanner(AOBScanner)
            self.signature_db.inject_into_resolver(PointerResolver)
        except Exception as exc:
            logger.debug("Unable to load signature database: %s", exc)
            self.signature_db = None

    def _init_cheat_definitions(self) -> List[CheatDefinition]:
        """Initialize cheat definitions with known pointers and signatures."""
        return [
            # Campaign cheats
            CheatDefinition(
                cheat_type=CheatType.INFINITE_GOLD,
                name="Infinite Gold",
                description="Freeze faction treasury at a high value",
                value_type=ValueType.INT_32,
                default_value=0,
                cheat_value=999999,
                mode='campaign',
                scan_pattern={
                    'initial_scan': {'value': None, 'type': 'unknown'},
                    'description': 'Scan treasury value after spending gold',
                },
                pointer_chains=['treasury'],
                aob_patterns=['treasury_write'],
                scan_key='treasury',
            ),
            CheatDefinition(
                cheat_type=CheatType.UNLIMITED_MOVEMENT,
                name="Unlimited Movement",
                description="Freeze selected army movement points",
                value_type=ValueType.FLOAT,
                default_value=1.0,
                cheat_value=999.0,
                mode='campaign',
                pointer_chains=['movement_points'],
                aob_patterns=['movement_write'],
                scan_key='movement_points',
            ),
            CheatDefinition(
                cheat_type=CheatType.INSTANT_CONSTRUCTION,
                name="Instant Construction",
                description="Set settlement construction timer to 0",
                value_type=ValueType.INT_32,
                default_value=None,
                cheat_value=0,
                mode='campaign',
                pointer_chains=['construction_timer'],
                aob_patterns=['construction_decrement'],
                scan_key='construction_timer',
            ),
            CheatDefinition(
                cheat_type=CheatType.FAST_RESEARCH,
                name="Fast Research",
                description="Set active research timer to 1 turn",
                value_type=ValueType.INT_32,
                default_value=None,
                cheat_value=1,
                mode='campaign',
                pointer_chains=['research_timer'],
                aob_patterns=['research_decrement'],
                scan_key='research_timer',
            ),
            CheatDefinition(
                cheat_type=CheatType.INFINITE_ACTION_POINTS,
                name="Infinite Action Points",
                description="Freeze selected agent action points",
                value_type=ValueType.FLOAT,
                default_value=1.0,
                cheat_value=999.0,
                mode='campaign',
                pointer_chains=['agent_action_points'],
                aob_patterns=['agent_action_write'],
                scan_key='agent_action_points',
            ),
            CheatDefinition(
                cheat_type=CheatType.MAX_RESEARCH_POINTS,
                name="Max Research Points",
                description="Set research pool points to the maximum",
                value_type=ValueType.INT_32,
                default_value=0,
                cheat_value=9999,
                mode='campaign',
                pointer_chains=['research_points'],
                aob_patterns=['research_points_write'],
                scan_key='research_points',
            ),
            CheatDefinition(
                cheat_type=CheatType.INSTANT_AGENT_TRAINING,
                name="Instant Agent Training",
                description="Complete agent training in a single turn",
                value_type=ValueType.INT_32,
                default_value=None,
                cheat_value=0,
                mode='campaign',
                pointer_chains=['agent_training_timer'],
                aob_patterns=['agent_training_decrement'],
                scan_key='agent_training_timer',
            ),
            CheatDefinition(
                cheat_type=CheatType.FREE_DIPLOMATIC_ACTIONS,
                name="Free Diplomatic Actions",
                description="Zero out diplomatic action costs",
                value_type=ValueType.INT_32,
                default_value=0,
                cheat_value=0,
                mode='campaign',
                pointer_chains=['diplomatic_action_cost'],
                aob_patterns=['diplomacy_cost_write'],
                scan_key='diplomatic_action_cost',
            ),
            CheatDefinition(
                cheat_type=CheatType.INVISIBLE_ARMIES,
                name="Invisible Armies",
                description="Force selected army visibility / fog immunity flag",
                value_type=ValueType.INT_32,
                default_value=0,
                cheat_value=1,
                mode='campaign',
                pointer_chains=['army_visibility_flag'],
                aob_patterns=['fog_of_war_check'],
                scan_key='army_visibility_flag',
            ),

            # Battle cheats
            CheatDefinition(
                cheat_type=CheatType.GOD_MODE,
                name="God Mode",
                description="Keep selected unit health at maximum",
                value_type=ValueType.FLOAT,
                default_value=100.0,
                cheat_value=250.0,
                mode='battle',
                pointer_chains=['unit_health'],
                aob_patterns=['health_write'],
                scan_key='unit_health',
            ),
            CheatDefinition(
                cheat_type=CheatType.UNLIMITED_AMMO,
                name="Unlimited Ammo",
                description="Prevent ranged ammunition from decreasing",
                value_type=ValueType.INT_32,
                default_value=None,
                cheat_value=999,
                mode='battle',
                pointer_chains=['unit_ammo'],
                aob_patterns=['ammo_decrement'],
                scan_key='unit_ammo',
                patch_mode='nop',
                overwrite_size=6,
            ),
            CheatDefinition(
                cheat_type=CheatType.HIGH_MORALE,
                name="High Morale",
                description="Raise morale and prevent routing",
                value_type=ValueType.FLOAT,
                default_value=1.0,
                cheat_value=2.0,
                mode='battle',
                pointer_chains=['unit_morale'],
                aob_patterns=['morale_write'],
                scan_key='unit_morale',
            ),
            CheatDefinition(
                cheat_type=CheatType.INFINITE_MORALE,
                name="Infinite Morale",
                description="Never allow the selected unit to rout",
                value_type=ValueType.FLOAT,
                default_value=1.0,
                cheat_value=3.0,
                mode='battle',
                pointer_chains=['unit_morale'],
                aob_patterns=['morale_write'],
                scan_key='unit_morale',
            ),
            CheatDefinition(
                cheat_type=CheatType.INFINITE_STAMINA,
                name="Infinite Stamina",
                description="Prevent battle stamina drain",
                value_type=ValueType.FLOAT,
                default_value=1.0,
                cheat_value=1.0,
                mode='battle',
                pointer_chains=['unit_stamina'],
                aob_patterns=['stamina_write'],
                scan_key='unit_stamina',
            ),
            CheatDefinition(
                cheat_type=CheatType.INSTANT_RELOAD,
                name="Instant Reload",
                description="Remove artillery and musket reload delay",
                value_type=ValueType.FLOAT,
                default_value=1.0,
                cheat_value=0.0,
                mode='battle',
                pointer_chains=['artillery_reload_timer'],
                aob_patterns=['reload_timer_write'],
                scan_key='artillery_reload_timer',
            ),
            CheatDefinition(
                cheat_type=CheatType.RANGE_BOOST,
                name="Range Boost",
                description="Increase unit projectile or musket range",
                value_type=ValueType.FLOAT,
                default_value=100.0,
                cheat_value=500.0,
                mode='battle',
                pointer_chains=['unit_range'],
                aob_patterns=['range_modifier'],
                scan_key='unit_range',
            ),
            CheatDefinition(
                cheat_type=CheatType.SPEED_BOOST,
                name="Speed Boost",
                description="Increase cavalry charge and movement speed",
                value_type=ValueType.FLOAT,
                default_value=1.0,
                cheat_value=4.0,
                mode='battle',
                pointer_chains=['charge_speed'],
                aob_patterns=['charge_speed_write'],
                scan_key='charge_speed',
                patch_mode='code_cave',
                overwrite_size=5,
            ),
            CheatDefinition(
                cheat_type=CheatType.INFINITE_UNIT_HEALTH,
                name="Infinite Unit Health",
                description="Continuously regenerate selected unit health",
                value_type=ValueType.FLOAT,
                default_value=100.0,
                cheat_value=250.0,
                mode='battle',
                pointer_chains=['unit_regeneration'],
                aob_patterns=['regeneration_tick'],
                scan_key='unit_regeneration',
            ),
            CheatDefinition(
                cheat_type=CheatType.ONE_HIT_KILL,
                name="One-Hit Kill",
                description="Inject a damage multiplier write for massive damage",
                value_type=ValueType.FLOAT,
                default_value=1.0,
                cheat_value=250.0,
                mode='battle',
                aob_patterns=['damage_modifier'],
                patch_mode='code_cave',
                overwrite_size=9,
            ),
            CheatDefinition(
                cheat_type=CheatType.SUPER_SPEED,
                name="Super Speed",
                description="Inject a large movement speed value",
                value_type=ValueType.FLOAT,
                default_value=1.0,
                cheat_value=5.0,
                mode='battle',
                aob_patterns=['speed_modifier'],
                patch_mode='code_cave',
                overwrite_size=5,
            ),

            # Strategic cheats
            CheatDefinition(
                cheat_type=CheatType.INSTANT_VICTORY,
                name="Instant Victory",
                description="Force the auto-resolve victory result flag",
                value_type=ValueType.INT_32,
                default_value=0,
                cheat_value=1,
                mode='strategic',
                pointer_chains=['autoresolve_victory_flag'],
                aob_patterns=['autoresolve_result_write'],
                scan_key='autoresolve_victory_flag',
            ),
            CheatDefinition(
                cheat_type=CheatType.MAX_PUBLIC_ORDER,
                name="Max Public Order",
                description="Set city public order to the maximum",
                value_type=ValueType.INT_32,
                default_value=0,
                cheat_value=100,
                mode='strategic',
                pointer_chains=['public_order'],
                aob_patterns=['public_order_write'],
                scan_key='public_order',
            ),
            CheatDefinition(
                cheat_type=CheatType.ZERO_ATTRITION,
                name="Zero Attrition",
                description="Prevent campaign army attrition damage",
                value_type=ValueType.FLOAT,
                default_value=0.0,
                cheat_value=0.0,
                mode='strategic',
                pointer_chains=['attrition_rate'],
                aob_patterns=['attrition_tick'],
                scan_key='attrition_rate',
            ),
            CheatDefinition(
                cheat_type=CheatType.FREE_UPGRADES,
                name="Free Upgrades",
                description="Zero veterancy / upgrade cost requirements",
                value_type=ValueType.INT_32,
                default_value=0,
                cheat_value=0,
                mode='strategic',
                pointer_chains=['veterancy_upgrade_cost'],
                aob_patterns=['veterancy_upgrade_cost_write'],
                scan_key='veterancy_upgrade_cost',
            ),

            # New cheat categories (PR #29)
            # AI Manipulation
            CheatDefinition(
                cheat_type=CheatType.ENHANCED_AI,
                name="Enhanced AI",
                description="Improve AI decision making and tactics",
                value_type=ValueType.INT_32,
                default_value=1,
                cheat_value=3,
                mode='campaign',
                pointer_chains=['ai_difficulty'],
                scan_key='ai_difficulty',
            ),
            CheatDefinition(
                cheat_type=CheatType.AI_DISABLED,
                name="AI Disabled",
                description="Disable AI opponent actions",
                value_type=ValueType.INT_32,
                default_value=1,
                cheat_value=0,
                mode='battle',
                pointer_chains=['ai_enabled'],
                scan_key='ai_enabled',
            ),
            CheatDefinition(
                cheat_type=CheatType.PERFECT_AI_ACCURACY,
                name="Perfect AI Accuracy",
                description="Set AI accuracy to maximum",
                value_type=ValueType.FLOAT,
                default_value=0.5,
                cheat_value=1.0,
                mode='battle',
                pointer_chains=['ai_accuracy'],
                scan_key='ai_accuracy',
            ),

            # Time Control
            CheatDefinition(
                cheat_type=CheatType.TIME_SCALE,
                name="Time Scale",
                description="Control game time speed",
                value_type=ValueType.FLOAT,
                default_value=1.0,
                cheat_value=2.0,
                mode='campaign',
                pointer_chains=['time_scale'],
                scan_key='time_scale',
            ),
            CheatDefinition(
                cheat_type=CheatType.PAUSE_GAME,
                name="Pause Game",
                description="Pause game execution",
                value_type=ValueType.INT_32,
                default_value=0,
                cheat_value=1,
                mode='campaign',
                pointer_chains=['game_paused'],
                scan_key='game_paused',
            ),
            CheatDefinition(
                cheat_type=CheatType.FAST_FORWARD,
                name="Fast Forward",
                description="Speed up game time",
                value_type=ValueType.FLOAT,
                default_value=1.0,
                cheat_value=5.0,
                mode='campaign',
                pointer_chains=['time_scale'],
                scan_key='time_scale',
            ),

            # Unit Spawning/Modification
            CheatDefinition(
                cheat_type=CheatType.SPAWN_ELITE_GUARD,
                name="Spawn Elite Guard",
                description="Spawn elite bodyguard unit",
                value_type=ValueType.INT_32,
                default_value=0,
                cheat_value=1,
                mode='battle',
                pointer_chains=['unit_spawn_flag'],
                scan_key='unit_spawn',
            ),
            CheatDefinition(
                cheat_type=CheatType.MAX_UNIT_VETERANCY,
                name="Max Unit Veterancy",
                description="Set selected unit to maximum veterancy",
                value_type=ValueType.INT_32,
                default_value=0,
                cheat_value=3,
                mode='battle',
                pointer_chains=['unit_veterancy'],
                scan_key='unit_veterancy',
            ),
            CheatDefinition(
                cheat_type=CheatType.INSTANT_UNIT_RECRUITMENT,
                name="Instant Unit Recruitment",
                description="Complete unit recruitment instantly",
                value_type=ValueType.INT_32,
                default_value=None,
                cheat_value=0,
                mode='campaign',
                pointer_chains=['recruitment_timer'],
                scan_key='recruitment_timer',
            ),

            # Weather & Environment
            CheatDefinition(
                cheat_type=CheatType.CLEAR_WEATHER,
                name="Clear Weather",
                description="Force clear weather conditions",
                value_type=ValueType.INT_32,
                default_value=0,
                cheat_value=1,
                mode='battle',
                pointer_chains=['weather_type'],
                scan_key='weather_control',
            ),
            CheatDefinition(
                cheat_type=CheatType.FOG_IMMUNITY,
                name="Fog Immunity",
                description="Ignore fog of war penalties",
                value_type=ValueType.INT_32,
                default_value=0,
                cheat_value=1,
                mode='battle',
                pointer_chains=['fog_penalty'],
                scan_key='fog_immunity',
            ),
            CheatDefinition(
                cheat_type=CheatType.TERRAIN_ADVANTAGE,
                name="Terrain Advantage",
                description="Always have terrain bonus",
                value_type=ValueType.FLOAT,
                default_value=1.0,
                cheat_value=2.0,
                mode='battle',
                pointer_chains=['terrain_modifier'],
                scan_key='terrain_advantage',
            ),

            # Camera & Visual
            CheatDefinition(
                cheat_type=CheatType.FREE_CAMERA,
                name="Free Camera",
                description="Unlock camera boundaries",
                value_type=ValueType.INT_32,
                default_value=0,
                cheat_value=1,
                mode='battle',
                pointer_chains=['camera_unlocked'],
                scan_key='free_camera',
            ),
            CheatDefinition(
                cheat_type=CheatType.REVEAL_MAP,
                name="Reveal Map",
                description="Reveal entire map",
                value_type=ValueType.INT_32,
                default_value=0,
                cheat_value=1,
                mode='campaign',
                pointer_chains=['map_revealed'],
                scan_key='reveal_map',
            ),
            CheatDefinition(
                cheat_type=CheatType.ENHANCED_VISIBILITY,
                name="Enhanced Visibility",
                description="Increase visibility range",
                value_type=ValueType.FLOAT,
                default_value=1.0,
                cheat_value=3.0,
                mode='campaign',
                pointer_chains=['visibility_range'],
                scan_key='visibility_range',
            ),

            # Additional cheats from PR #24
            CheatDefinition(
                cheat_type=CheatType.INSTANT_RECRUITMENT,
                name="Instant Recruitment",
                description="Instantly recruit any unit",
                value_type=ValueType.INT_32,
                default_value=None,
                cheat_value=0,
                mode='campaign',
                pointer_chains=['recruitment_timer'],
                aob_patterns=['recruitment_decrement'],
                scan_key='recruitment_timer',
            ),
            CheatDefinition(
                cheat_type=CheatType.NO_FOG_OF_WAR,
                name="No Fog of War",
                description="Remove fog of war completely",
                value_type=ValueType.INT_32,
                default_value=0,
                cheat_value=1,
                mode='campaign',
                pointer_chains=['fog_of_war_enabled'],
                aob_patterns=['fog_of_war_check'],
                scan_key='fog_of_war',
            ),
            CheatDefinition(
                cheat_type=CheatType.UNLIMITED_AGENTS,
                name="Unlimited Agents",
                description="Remove agent action limits",
                value_type=ValueType.INT_32,
                default_value=1,
                cheat_value=99,
                mode='campaign',
                pointer_chains=['agent_actions_remaining'],
                aob_patterns=['agent_action_decrement'],
                scan_key='agent_actions',
            ),
        ]

    def activate_cheat(self, cheat_type: CheatType, address: Optional[int] = None) -> bool:
        """Activate a cheat."""
        cheat_def = self._get_cheat_definition(cheat_type)
        if not cheat_def:
            print(f"Unknown cheat type: {cheat_type}")
            return False

        if cheat_def.patch_mode == 'freeze':
            return self._activate_value_cheat(cheat_def, address)

        if self._activate_aob_cheat(cheat_def):
            return True

        print(f"⚠ Could not auto-resolve signature for {cheat_def.name}.")
        print(f"  Instructions:\n{self.get_cheat_instructions(cheat_type)}")
        return False

    def _activate_value_cheat(
        self,
        cheat_def: CheatDefinition,
        address: Optional[int] = None,
    ) -> bool:
        """Activate a value/freeze-based cheat using explicit or resolved addresses."""

        # Ensure the freezer has our error callback registered
        if self.memory_scanner._freezer and not self.memory_scanner._freezer._on_error:
            self.memory_scanner._freezer.set_callbacks(on_error=self._on_freeze_error)

        if not address:
            address = self._resolved_addresses.get(cheat_def.cheat_type)

        if not address:
            address = self._try_resolve_pointer_chain(cheat_def.cheat_type)

        if not address:
            print(f"⚠ Could not auto-resolve address for {cheat_def.name}.")
            print(f"  Use memory scanner to find it, then pass the address.")
            print(f"  Instructions:\n{self.get_cheat_instructions(cheat_def.cheat_type)}")
            return False

        original = self.memory_scanner.read_value(address, cheat_def.value_type)
        success = self.memory_scanner.write_value(
            address,
            cheat_def.cheat_value,
            cheat_def.value_type,
        )

        if not success:
            # Write might have failed due to invalid address (e.g. ASLR shift)
            # Invalidate cached address so it re-resolves next time
            if cheat_def.cheat_type in self._resolved_addresses:
                print(f"Invalidating cached address for {cheat_def.name}...")
                del self._resolved_addresses[cheat_def.cheat_type]
            return False

        self.memory_scanner.freeze_value(address, cheat_def.cheat_value, cheat_def.value_type)
        self.active_cheats[cheat_def.cheat_type] = {
            'address': address,
            'definition': cheat_def,
            'original_value': original,
        }
        self._resolved_addresses[cheat_def.cheat_type] = address
        print(f"✓ {cheat_def.name} ACTIVATED at 0x{address:08X}")
        return True

    def _activate_aob_cheat(self, cheat_def: CheatDefinition) -> bool:
        """Activate a signature/patch-based cheat."""
        if not self.memory_scanner.is_attached() or not self.memory_scanner.backend:
            return False

        matches = self.scan_pattern_signatures(cheat_def.cheat_type, max_results=1)
        if not matches:
            return False

        pattern_name, addresses = next(iter(matches.items()))
        if not addresses:
            return False
        match_address = addresses[0]

        if cheat_def.patch_mode == 'nop':
            return self._activate_nop_patch_cheat(cheat_def, pattern_name, match_address)
        if cheat_def.patch_mode == 'code_cave':
            return self._activate_code_cave_cheat(cheat_def, pattern_name, match_address)
        return False

    def _activate_nop_patch_cheat(
        self,
        cheat_def: CheatDefinition,
        pattern_name: str,
        match_address: int,
    ) -> bool:
        """Apply a NOP patch at the matched signature address."""
        if not self.signature_db or not self.memory_scanner.backend:
            return False

        entry = self.signature_db.get_pattern_entry(pattern_name)
        nop_bytes = entry.nop_bytes if entry and entry.nop_bytes else cheat_def.overwrite_size
        original = self.memory_scanner.backend.read_bytes(match_address, nop_bytes)
        if original is None or len(original) != nop_bytes:
            return False

        patched = b'\x90' * nop_bytes
        if not self.memory_scanner.backend.write_bytes(match_address, patched):
            if cheat_def.cheat_type in self._resolved_addresses:
                print(f"Invalidating cached address for {cheat_def.name}...")
                del self._resolved_addresses[cheat_def.cheat_type]
            return False

        self.active_cheats[cheat_def.cheat_type] = {
            'address': match_address,
            'definition': cheat_def,
            'patches': [
                MemoryPatch(
                    address=match_address,
                    original_bytes=original,
                    patched_bytes=patched,
                    description=pattern_name,
                )
            ],
        }
        print(f"✓ {cheat_def.name} PATCHED at 0x{match_address:08X}")
        return True

    def _activate_code_cave_cheat(
        self,
        cheat_def: CheatDefinition,
        pattern_name: str,
        match_address: int,
    ) -> bool:
        """Redirect a complex cheat through a code cave using HookManager."""
        if not self.memory_scanner.backend:
            return False

        payload = self._build_code_cave_payload(cheat_def, match_address)
        if not payload:
            return False

        # We need a builder since add_hook now expects one. For existing cheats that don't need
        # to call the original trampoline, we can just return the payload directly and then
        # execute the trampoline to ensure the original instruction is executed, if needed.
        # However, looking at the code, these cheats historically overwrote the original bytes
        # and did not call them (they just jumped back to match_address + overwrite_size).
        # We'll maintain that behaviour by ignoring the trampoline address.
        def payload_builder(trampoline_addr: int) -> bytes:
            return payload

        success = self.hook_manager.add_hook(
            address=match_address,
            hook_id=cheat_def.cheat_type.value,
            payload_builder=payload_builder,
            overwrite_size=cheat_def.overwrite_size,
        )
        if not success:
            if cheat_def.cheat_type in self._resolved_addresses:
                print(f"Invalidating cached address for {cheat_def.name}...")
                del self._resolved_addresses[cheat_def.cheat_type]
            return False

        # Instead of storing patches, we track that the cheat is handled by hook_manager
        self.active_cheats[cheat_def.cheat_type] = {
            'address': match_address,
            'definition': cheat_def,
            'is_hook': True,
            'pattern_name': pattern_name,
        }
        print(f"✓ {cheat_def.name} CODE-CAVE HOOK ACTIVE at 0x{match_address:08X}")
        return True

    def _build_code_cave_payload(
        self,
        cheat_def: CheatDefinition,
        match_address: int,
    ) -> Optional[bytes]:
        """Build a minimal payload for register-relative float writes."""
        if not self.memory_scanner.backend:
            return None

        if cheat_def.cheat_type == CheatType.ONE_HIT_KILL:
            disp = self.memory_scanner.backend.read_bytes(match_address + 8, 1)
            if not disp:
                return None
            return b'\xC7\x46' + disp + struct.pack('<f', float(cheat_def.cheat_value))

        if cheat_def.cheat_type in (
            CheatType.SUPER_SPEED,
            CheatType.SPEED_BOOST,
        ):
            disp = self.memory_scanner.backend.read_bytes(match_address + 4, 1)
            if not disp:
                return None
            return b'\xC7\x41' + disp + struct.pack('<f', float(cheat_def.cheat_value))

        return None

    def _get_pointer_chain_names(self, cheat_def: CheatDefinition) -> List[str]:
        """Resolve pointer-chain names for a cheat definition."""
        names = list(cheat_def.pointer_chains)
        if self.signature_db:
            chain_entry = self.signature_db.get_chain_for_cheat(cheat_def.cheat_type.value)
            if chain_entry and chain_entry.name not in names:
                names.append(chain_entry.name)

        # Prioritize previously successful method if it exists in history
        game_version = "unknown"
        if self.signature_db and self.signature_db.metadata:
            game_version = self.signature_db.metadata.version

        preferred_method = self.crash_recovery.get_preferred_resolution_method(game_version, cheat_def.cheat_type.value)
        preferred_chain = preferred_method.get("pattern_name") # In the history we saved it as pattern_name

        if preferred_chain and preferred_chain in names:
            names.remove(preferred_chain)
            names.insert(0, preferred_chain)

        return names

    def _get_pattern_names(self, cheat_def: CheatDefinition) -> List[str]:
        """Resolve AOB pattern names for a cheat definition."""
        names = list(cheat_def.aob_patterns)
        if self.signature_db:
            for entry in self.signature_db.get_patterns_for_cheat(cheat_def.cheat_type.value):
                if entry.name not in names:
                    names.append(entry.name)

        # Prioritize previously successful method if it exists in history
        game_version = "unknown"
        if self.signature_db and self.signature_db.metadata:
            game_version = self.signature_db.metadata.version

        preferred_method = self.crash_recovery.get_preferred_resolution_method(game_version, cheat_def.cheat_type.value)
        preferred_pattern = preferred_method.get("pattern_name")

        if preferred_pattern and preferred_pattern in names:
            names.remove(preferred_pattern)
            names.insert(0, preferred_pattern)

        return names

    def _try_resolve_pointer_chain(self, cheat_type: CheatType) -> Optional[int]:
        """Attempt to resolve a cheat's address via configured pointer chains."""
        if not self.memory_scanner.is_attached():
            return None

        from .advanced import PointerResolver

        if self._pointer_resolver is None:
            self._pointer_resolver = PointerResolver(
                editor=self.memory_scanner.backend,
                pid=self.memory_scanner.process_manager.pid,
            )

        cheat_def = self._get_cheat_definition(cheat_type)
        if not cheat_def:
            return None

        for chain_name in self._get_pointer_chain_names(cheat_def):
            chain = PointerResolver.KNOWN_CHAINS.get(chain_name)
            if not chain:
                continue

            address = self._pointer_resolver.resolve_chain(chain)
            if not address:
                continue

            test_val = self.memory_scanner.read_value(address, cheat_def.value_type)
            if test_val is not None:
                print(f"  ✓ Resolved {chain_name} via pointer chain → 0x{address:08X}")
                return address

        return None

    def scan_pattern_signatures(
        self,
        cheat_type: CheatType,
        max_results: int = 5,
    ) -> Dict[str, List[int]]:
        """Scan readable regions for the AOB signatures tagged for a cheat."""
        cheat_def = self._get_cheat_definition(cheat_type)
        if not cheat_def or not self.signature_db or not self.memory_scanner.backend:
            return {}

        from .advanced import AOBScanner

        if self._aob_scanner is None:
            self._aob_scanner = AOBScanner(self.memory_scanner.backend)
        else:
            self._aob_scanner.set_editor(self.memory_scanner.backend)

        regions = self.memory_scanner.backend.get_prioritized_regions()
        if not regions:
            return {}

        matches: Dict[str, List[int]] = {}
        for pattern_name in self._get_pattern_names(cheat_def):
            pattern = self.signature_db.get_pattern(pattern_name)
            if not pattern:
                continue

            found: List[int] = []
            for region in regions:
                region_matches = self._aob_scanner.scan(
                    pattern,
                    start_address=region['address'],
                    end_address=region['address'] + region['size'],
                    max_results=max_results - len(found),
                    timeout=2.0,
                )
                if region_matches:
                    found.extend(region_matches)
                if len(found) >= max_results:
                    break

            if found:
                matches[pattern_name] = found[:max_results]

        return matches

    def set_address(self, cheat_type: CheatType, address: int) -> None:
        """Manually set/cache a resolved address for a cheat type."""
        self._resolved_addresses[cheat_type] = address
        print(f"Cached address for {cheat_type.value}: 0x{address:08X}")

    def deactivate_cheat(self, cheat_type: CheatType) -> bool:
        """Deactivate a cheat and restore any patched bytes / values."""
        if cheat_type not in self.active_cheats:
            return False

        cheat_info = self.active_cheats[cheat_type]
        cheat_def: CheatDefinition = cheat_info['definition']

        if cheat_info.get('is_hook'):
            self.hook_manager.remove_hook(
                address=cheat_info['address'],
                hook_id=cheat_def.cheat_type.value,
                overwrite_size=cheat_def.overwrite_size
            )
        else:
            patches = cheat_info.get('patches', [])
            if patches and self.memory_scanner.backend:
                for patch in reversed(patches):
                    self.memory_scanner.backend.write_bytes(patch.address, patch.original_bytes)
            else:
                address = cheat_info['address']
                self.memory_scanner.unfreeze_value(address)

                if cheat_info.get('original_value') is not None:
                    self.memory_scanner.write_value(
                        address,
                        cheat_info['original_value'],
                        cheat_def.value_type,
                    )

        del self.active_cheats[cheat_type]
        print(f"✗ {cheat_def.name} DEACTIVATED")
        return True

    def toggle_cheat(self, cheat_type: CheatType, address: Optional[int] = None) -> bool:
        """Toggle a cheat on/off."""
        if cheat_type in self.active_cheats:
            return self.deactivate_cheat(cheat_type)
        return self.activate_cheat(cheat_type, address)

    def is_cheat_active(self, cheat_type: CheatType) -> bool:
        """Check if a cheat is active."""
        return cheat_type in self.active_cheats

    def get_active_cheats(self) -> List[CheatType]:
        """Get list of active cheat types."""
        return list(self.active_cheats.keys())

    def deactivate_all_cheats(self) -> None:
        """Deactivate all active cheats."""
        for cheat_type in list(self.active_cheats.keys()):
            self.deactivate_cheat(cheat_type)

    def save_active_cheats_state(self, game_version: str = "unknown", crashed: bool = False) -> None:
        """Save the current active cheats to be restored later (e.g., after process crash)."""
        self.saved_cheat_state = list(self.active_cheats.keys())

        # Try to resolve game version if not provided
        if game_version == "unknown" and self.signature_db and self.signature_db.metadata:
            game_version = self.signature_db.metadata.version

        # Build a dict representing the state to save to disk
        state_to_save = {}
        for cheat_type, cheat_info in self.active_cheats.items():
            state_to_save[cheat_type.value] = cheat_info

        # Add tracking of cheat ownership by address to the state to save
        self.crash_recovery.save_state(state_to_save, game_version)

        # Automatically deactivate them to clean up internal state, but skip if the process crashed
        # Attempting to deactivate cheats (write bytes) to a dead process can crash the trainer loop
        if not crashed:
            for cheat_type in self.saved_cheat_state:
                self.deactivate_cheat(cheat_type)
        else:
            self.active_cheats.clear()

    def restore_saved_cheats(self, game_version: str = "unknown") -> int:
        """Restore cheats that were saved previously. Returns number of cheats restored."""
        restored_count = 0

        if game_version == "unknown" and self.signature_db and self.signature_db.metadata:
            game_version = self.signature_db.metadata.version

        # Load from disk
        saved_state = self.crash_recovery.load_state(game_version)

        # Merge with in-memory saved state
        for cheat_data in saved_state:
            try:
                cheat_type = CheatType(cheat_data['cheat_type'])
                if cheat_type not in self.saved_cheat_state:
                    self.saved_cheat_state.append(cheat_type)
            except ValueError:
                continue

        for cheat_type in self.saved_cheat_state:
            # Check history to see if there is a preferred method we can use to speed up activation
            preferred_method = self.crash_recovery.get_preferred_resolution_method(game_version, cheat_type.value)

            # Since the game restarted, addresses are likely invalid due to ASLR, but pattern names are useful.
            # If there's a preferred pattern, we could theoretically modify the cheat's AOB list to try it first.
            # However, `activate_cheat` natively cycles through the aob_patterns in the definition anyway.
            # The most important thing is that we *do not* pass `address=preferred_address`
            # as that points to dead/wrong memory from the previous process.

            # Try normal activation (which will re-resolve via pointer chain or AOB scan)
            if self.activate_cheat(cheat_type):
                restored_count += 1
            else:
                logger.warning(f"Failed to auto-restore cheat {cheat_type.value}. Address could not be resolved in the new process.")

        self.saved_cheat_state.clear()

        if restored_count > 0:
            logger.info(f"Restored {restored_count} cheats")
            print(f"Restored {restored_count} cheats")

        return restored_count

    def _get_cheat_definition(self, cheat_type: CheatType) -> Optional[CheatDefinition]:
        """Get a cheat definition."""
        for cheat_def in self.cheat_definitions:
            if cheat_def.cheat_type == cheat_type:
                return cheat_def
        return None

    def get_cheat_instructions(self, cheat_type: CheatType) -> str:
        """Get instructions for finding or validating a cheat address."""
        cheat_def = self._get_cheat_definition(cheat_type)
        if not cheat_def:
            return "Unknown cheat type"

        if self.signature_db and cheat_def.scan_key:
            guide = self.signature_db.get_scan_guide(cheat_def.scan_key)
            if guide and guide.get('steps'):
                return "\n".join(guide['steps'])

        if cheat_type == CheatType.INFINITE_GOLD:
            return (
                "1. Note your current gold amount\n"
                "2. Scan for exact value (4 Bytes)\n"
                "3. Spend some gold in-game\n"
                "4. Scan for decreased value\n"
                "5. Repeat until 1-3 addresses remain\n"
                "6. Change value to 999999"
            )
        if cheat_type == CheatType.GOD_MODE:
            return (
                "1. Start a battle\n"
                "2. Note a unit's health\n"
                "3. Scan for exact value (Float)\n"
                "4. Let the unit take damage\n"
                "5. Scan for decreased value\n"
                "6. Repeat until address found\n"
                "7. Freeze or change value to 9999"
            )

        pattern_names = self._get_pattern_names(cheat_def)
        if pattern_names:
            return (
                f"Use AOB signature scanning for {cheat_def.name}. "
                f"Known patterns: {', '.join(pattern_names)}"
            )
        return f"Use memory scanner to find {cheat_def.name} address"

    def get_all_cheats(self) -> List[Dict[str, Any]]:
        """Get all available cheats."""
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

    def build_address_table_payload(self) -> Dict[str, Any]:
        """Build a serialisable address/signature table for export."""
        metadata = self.signature_db.metadata if self.signature_db else None
        payload = {
            'game': metadata.game if metadata else 'Napoleon Total War',
            'version': metadata.version if metadata else '',
            'generated': datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
            'source_tables': self.signature_db.loaded_files if self.signature_db else [],
            'auto_update': {
                'strategy': 'regenerate_when_source_tables_change',
                'default_output': str(_DEFAULT_ADDRESS_EXPORT.name),
            },
            'cheats': {},
            'pointer_chains': {},
            'aob_patterns': {},
            'scan_guides': {},
        }

        if self.signature_db:
            for name in self.signature_db.list_chains():
                chain = self.signature_db.get_chain_entry(name)
                if chain:
                    payload['pointer_chains'][name] = {
                        'module': chain.chain.module_name,
                        'base_offset': hex(chain.chain.base_offset),
                        'offsets': [hex(offset) for offset in chain.chain.offsets],
                        'type': chain.chain.value_type,
                        'description': chain.chain.description,
                        'cheat': chain.cheat,
                        'notes': chain.notes,
                    }

            for name in self.signature_db.list_patterns():
                pattern = self.signature_db.get_pattern_entry(name)
                if pattern:
                    payload['aob_patterns'][name] = {
                        'pattern': pattern.pattern.pattern,
                        'description': pattern.pattern.description,
                        'offset_from_match': pattern.pattern.offset_from_match,
                        'nop_bytes': pattern.nop_bytes,
                        'cheat': pattern.cheat,
                        'cheat_action': pattern.cheat_action,
                    }

            for name in self.signature_db.list_scan_guides():
                payload['scan_guides'][name] = self.signature_db.get_scan_guide(name)

        for cheat in self.cheat_definitions:
            payload['cheats'][cheat.cheat_type.value] = {
                'name': cheat.name,
                'description': cheat.description,
                'mode': cheat.mode,
                'value_type': cheat.value_type.value,
                'default_value': cheat.default_value,
                'cheat_value': cheat.cheat_value,
                'pointer_chains': self._get_pointer_chain_names(cheat),
                'aob_patterns': self._get_pattern_names(cheat),
                'patch_mode': cheat.patch_mode,
                'scan_key': cheat.scan_key,
            }

        return payload

    def export_address_table(self, output_path: Optional[str] = None) -> Path:
        """Export the current address/signature table to JSON."""
        destination = Path(output_path) if output_path else _DEFAULT_ADDRESS_EXPORT
        destination.parent.mkdir(parents=True, exist_ok=True)
        payload = self.build_address_table_payload()
        destination.write_text(json.dumps(payload, indent=2), encoding='utf-8')
        return destination

    def refresh_address_table_if_stale(self, output_path: Optional[str] = None) -> bool:
        """Regenerate the exported address table if a source table changed."""
        destination = Path(output_path) if output_path else _DEFAULT_ADDRESS_EXPORT
        if not self.signature_db or not self.signature_db.loaded_files:
            return False

        if not destination.exists():
            self.export_address_table(str(destination))
            return True

        output_mtime = destination.stat().st_mtime
        for source in self.signature_db.loaded_files:
            if Path(source).stat().st_mtime > output_mtime:
                self.export_address_table(str(destination))
                return True
        return False

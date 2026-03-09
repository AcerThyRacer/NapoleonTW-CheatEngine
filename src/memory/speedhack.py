"""
Speedhack (time-manipulation) manager for Napoleon Total War.

Provides the ability to modify the game's perceived passage of time
by scanning for and modifying delta-time / tick-rate values in memory.
"""

import logging
import struct
import time
from typing import Any, Dict, List, Optional

logger = logging.getLogger('napoleon.memory.speedhack')


class SpeedhackManager:
    """
    Modify game speed by altering timer-related memory values.

    The manager searches for the game's delta-time multiplier or
    tick-rate variable and continuously overwrites it to achieve
    the desired speed factor.

    Typical workflow::

        shm = SpeedhackManager(scanner)
        shm.find_speed_addresses()       # auto-detect timer addresses
        shm.set_game_speed(2.0)          # 2× speed
        shm.set_game_speed(1.0)          # restore normal
        shm.restore()                    # full cleanup
    """

    # Napoleon TW WARSCAPE engine known AOB patterns for tick-rate code.
    SPEED_SIGNATURES = [
        {
            'name': 'delta_time_write',
            'pattern': 'F3 0F 11 41 ?? F3 0F 10 05',
            'description': 'MOVSS [ECX+offset], XMM0 — writes delta-time value',
        },
        {
            'name': 'game_tick_rate',
            'pattern': 'F3 0F 59 C8 F3 0F 11 4E ??',
            'description': 'MULSS XMM1,XMM0 / MOVSS — tick-rate scaling',
        },
    ]

    # Sensible limits
    MIN_MULTIPLIER = 0.5
    MAX_MULTIPLIER = 10.0
    DEFAULT_MULTIPLIER = 1.0

    def __init__(self, scanner=None):
        """
        Initialise the speedhack manager.

        Args:
            scanner: A ``MemoryScanner`` (or compatible) instance for reading/writing.
        """
        self._scanner = scanner
        self._speed_addresses: List[int] = []
        self._original_values: Dict[int, float] = {}
        self._multiplier: float = self.DEFAULT_MULTIPLIER
        self._active: bool = False

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def multiplier(self) -> float:
        """Current speed multiplier."""
        return self._multiplier

    @property
    def is_active(self) -> bool:
        """Whether a non-default speed is being enforced."""
        return self._active

    @property
    def speed_addresses(self) -> List[int]:
        """Addresses currently being manipulated."""
        return list(self._speed_addresses)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_scanner(self, scanner) -> None:
        """Attach or replace the memory scanner."""
        self._scanner = scanner

    def find_speed_addresses(self) -> List[int]:
        """
        Attempt to locate timer/speed-related memory addresses
        by scanning for known AOB signatures.

        Returns:
            List of discovered addresses.
        """
        if self._scanner is None:
            logger.warning("No scanner set — cannot search for speed addresses")
            return []

        found: List[int] = []

        for sig in self.SPEED_SIGNATURES:
            try:
                from src.memory.advanced import AOBPattern, AOBScanner

                pattern = AOBPattern(
                    name=sig['name'],
                    pattern=sig['pattern'],
                    description=sig['description'],
                )
                aob = AOBScanner(editor=self._scanner.backend)
                results = aob.scan(pattern, max_results=5, timeout=15.0)
                found.extend(results)
            except Exception as exc:
                logger.debug("Signature scan for '%s' failed: %s", sig['name'], exc)

        self._speed_addresses = found
        logger.info("Found %d speed-related addresses", len(found))
        return found

    def add_speed_address(self, address: int) -> None:
        """Manually register an address as speed-related."""
        if address not in self._speed_addresses:
            self._speed_addresses.append(address)

    def set_game_speed(self, multiplier: float) -> bool:
        """
        Modify the game speed.

        Args:
            multiplier: Speed factor — ``1.0`` is normal,
                        ``2.0`` is double speed, ``0.5`` is half speed.
                        Clamped to ``[MIN_MULTIPLIER, MAX_MULTIPLIER]``.

        Returns:
            ``True`` if at least one address was successfully written.
        """
        multiplier = max(self.MIN_MULTIPLIER, min(self.MAX_MULTIPLIER, multiplier))
        self._multiplier = multiplier

        if not self._speed_addresses:
            logger.warning("No speed addresses registered — call find_speed_addresses() first")
            return False

        if self._scanner is None:
            logger.warning("No scanner available")
            return False

        success = False
        for addr in self._speed_addresses:
            try:
                # Save original if not already saved
                if addr not in self._original_values:
                    self._save_original(addr)

                data = struct.pack('<f', multiplier)
                if hasattr(self._scanner, 'backend') and self._scanner.backend:
                    self._scanner.backend.write_bytes(addr, data)
                else:
                    self._scanner.write_value(addr, multiplier)
                success = True
            except Exception as exc:
                logger.debug("Failed to write speed @ 0x%08X: %s", addr, exc)

        self._active = multiplier != self.DEFAULT_MULTIPLIER
        logger.info("Game speed set to %.1fx (%d addresses)", multiplier, len(self._speed_addresses))
        return success

    def restore(self) -> bool:
        """
        Restore all modified speed addresses to their original values.

        Returns:
            ``True`` if at least one address was restored.
        """
        if not self._original_values:
            self._multiplier = self.DEFAULT_MULTIPLIER
            self._active = False
            return True

        if self._scanner is None:
            return False

        success = False
        for addr, original in self._original_values.items():
            try:
                data = struct.pack('<f', original)
                if hasattr(self._scanner, 'backend') and self._scanner.backend:
                    self._scanner.backend.write_bytes(addr, data)
                else:
                    self._scanner.write_value(addr, original)
                success = True
            except Exception as exc:
                logger.debug("Failed to restore speed @ 0x%08X: %s", addr, exc)

        self._original_values.clear()
        self._multiplier = self.DEFAULT_MULTIPLIER
        self._active = False
        logger.info("Game speed restored to normal")
        return success

    def get_status(self) -> Dict[str, Any]:
        """Return a summary dictionary of the speedhack state."""
        return {
            'active': self._active,
            'multiplier': self._multiplier,
            'address_count': len(self._speed_addresses),
            'addresses': [f'0x{a:08X}' for a in self._speed_addresses],
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _save_original(self, addr: int) -> None:
        """Read and cache the original float value at *addr*."""
        try:
            if hasattr(self._scanner, 'backend') and self._scanner.backend:
                data = self._scanner.backend.read_bytes(addr, 4)
                if data and len(data) >= 4:
                    self._original_values[addr] = struct.unpack('<f', data[:4])[0]
            else:
                from src.memory.scanner import ValueType
                val = self._scanner.read_value(addr, ValueType.FLOAT)
                if val is not None:
                    self._original_values[addr] = val
        except Exception as exc:
            logger.debug("Could not save original value @ 0x%08X: %s", addr, exc)

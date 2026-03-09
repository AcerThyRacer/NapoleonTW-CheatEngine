"""
Teleport manager for Napoleon Total War.

Reads and writes army / unit coordinates in game memory, enabling
instant relocation of armies on the campaign map or units on the
battle map.
"""

import logging
import struct
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger('napoleon.memory.teleport')


@dataclass
class Coordinates:
    """3-D position in game space."""
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0

    def as_tuple(self) -> Tuple[float, float, float]:
        return (self.x, self.y, self.z)

    def __str__(self) -> str:
        return f"({self.x:.2f}, {self.y:.2f}, {self.z:.2f})"


@dataclass
class TeleportTarget:
    """
    Describes a named location that can be jumped to.
    """
    name: str
    coords: Coordinates
    description: str = ""


class TeleportManager:
    """
    Read and write army/unit coordinates via memory.

    The manager works with a ``MemoryScanner`` (or any object that
    exposes ``read_value`` / ``write_value`` and an ``is_attached`` method)
    and maintains a set of coordinate addresses grouped by entity.

    Typical workflow::

        tm = TeleportManager(scanner)
        tm.register_entity("army_1", x_addr, y_addr, z_addr)
        pos = tm.read_position("army_1")
        tm.teleport("army_1", Coordinates(100.0, 0.0, 200.0))

    Saved bookmarks let users jump back to favourite locations::

        tm.save_bookmark("Paris", Coordinates(150.0, 0.0, 300.0))
        tm.teleport_to_bookmark("army_1", "Paris")
    """

    # Known pointer-chain templates for army position (WARSCAPE engine, v1.6).
    # After resolving the *army base pointer* the X/Y/Z floats sit at fixed
    # offsets from that base.
    POSITION_OFFSETS = {
        'x': 0x50,
        'y': 0x54,
        'z': 0x58,
    }

    def __init__(self, scanner=None):
        """
        Initialise the teleport manager.

        Args:
            scanner: A ``MemoryScanner`` (or compatible) instance.
        """
        self._scanner = scanner
        # entity_id -> {'x': addr, 'y': addr, 'z': addr}
        self._entities: Dict[str, Dict[str, int]] = {}
        self._bookmarks: Dict[str, TeleportTarget] = {}

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------

    def set_scanner(self, scanner) -> None:
        """Attach or replace the memory scanner."""
        self._scanner = scanner

    # ------------------------------------------------------------------
    # Entity registration
    # ------------------------------------------------------------------

    def register_entity(
        self,
        entity_id: str,
        x_address: int,
        y_address: int,
        z_address: int,
    ) -> None:
        """
        Register coordinate addresses for an entity.

        Args:
            entity_id: A logical name for the army / unit.
            x_address: Memory address of the X coordinate (float).
            y_address: Memory address of the Y coordinate (float).
            z_address: Memory address of the Z coordinate (float).
        """
        self._entities[entity_id] = {
            'x': x_address,
            'y': y_address,
            'z': z_address,
        }
        logger.info(
            "Registered entity '%s': X=0x%08X Y=0x%08X Z=0x%08X",
            entity_id, x_address, y_address, z_address,
        )

    def register_entity_from_base(self, entity_id: str, base_address: int) -> None:
        """
        Register an entity using a base pointer and the standard
        ``POSITION_OFFSETS`` for X / Y / Z.
        """
        self.register_entity(
            entity_id,
            x_address=base_address + self.POSITION_OFFSETS['x'],
            y_address=base_address + self.POSITION_OFFSETS['y'],
            z_address=base_address + self.POSITION_OFFSETS['z'],
        )

    def unregister_entity(self, entity_id: str) -> None:
        """Remove an entity from tracking."""
        self._entities.pop(entity_id, None)

    def list_entities(self) -> List[str]:
        """Return IDs of all registered entities."""
        return list(self._entities.keys())

    # ------------------------------------------------------------------
    # Reading coordinates
    # ------------------------------------------------------------------

    def read_position(self, entity_id: str) -> Optional[Coordinates]:
        """
        Read the current position of *entity_id*.

        Returns:
            A ``Coordinates`` instance, or ``None`` on failure.
        """
        if entity_id not in self._entities:
            logger.warning("Unknown entity '%s'", entity_id)
            return None

        addrs = self._entities[entity_id]
        vals = {}

        for axis in ('x', 'y', 'z'):
            v = self._read_float(addrs[axis])
            if v is None:
                logger.warning("Could not read %s for '%s'", axis, entity_id)
                return None
            vals[axis] = v

        coords = Coordinates(**vals)
        logger.debug("Read position of '%s': %s", entity_id, coords)
        return coords

    def read_all_positions(self) -> Dict[str, Optional[Coordinates]]:
        """Read positions of every registered entity."""
        return {eid: self.read_position(eid) for eid in self._entities}

    # ------------------------------------------------------------------
    # Writing coordinates (teleport)
    # ------------------------------------------------------------------

    def teleport(self, entity_id: str, coords: Coordinates) -> bool:
        """
        Instantly move *entity_id* to *coords*.

        Returns:
            ``True`` if all three axes were written successfully.
        """
        if entity_id not in self._entities:
            logger.warning("Unknown entity '%s'", entity_id)
            return False

        addrs = self._entities[entity_id]
        ok = True

        for axis, value in [('x', coords.x), ('y', coords.y), ('z', coords.z)]:
            if not self._write_float(addrs[axis], value):
                logger.warning("Failed to write %s for '%s'", axis, entity_id)
                ok = False

        if ok:
            logger.info("Teleported '%s' to %s", entity_id, coords)
        return ok

    def teleport_relative(
        self, entity_id: str, dx: float = 0.0, dy: float = 0.0, dz: float = 0.0
    ) -> bool:
        """Move an entity by a relative offset from its current position."""
        current = self.read_position(entity_id)
        if current is None:
            return False

        new_coords = Coordinates(
            x=current.x + dx,
            y=current.y + dy,
            z=current.z + dz,
        )
        return self.teleport(entity_id, new_coords)

    # ------------------------------------------------------------------
    # Bookmarks
    # ------------------------------------------------------------------

    def save_bookmark(
        self, name: str, coords: Coordinates, description: str = ""
    ) -> None:
        """Save a reusable map location."""
        self._bookmarks[name] = TeleportTarget(
            name=name, coords=coords, description=description,
        )
        logger.info("Saved bookmark '%s' at %s", name, coords)

    def delete_bookmark(self, name: str) -> bool:
        """Delete a bookmark. Returns ``True`` if it existed."""
        return self._bookmarks.pop(name, None) is not None

    def list_bookmarks(self) -> List[TeleportTarget]:
        """Return all saved bookmarks."""
        return list(self._bookmarks.values())

    def get_bookmark(self, name: str) -> Optional[TeleportTarget]:
        """Retrieve a bookmark by name."""
        return self._bookmarks.get(name)

    def teleport_to_bookmark(self, entity_id: str, bookmark_name: str) -> bool:
        """Teleport an entity to a saved bookmark."""
        bm = self._bookmarks.get(bookmark_name)
        if bm is None:
            logger.warning("Unknown bookmark '%s'", bookmark_name)
            return False
        return self.teleport(entity_id, bm.coords)

    def get_status(self) -> Dict[str, Any]:
        """Return a summary of the teleport system state."""
        return {
            'entity_count': len(self._entities),
            'entities': list(self._entities.keys()),
            'bookmark_count': len(self._bookmarks),
            'bookmarks': [b.name for b in self._bookmarks.values()],
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _read_float(self, address: int) -> Optional[float]:
        """Read a single-precision float from *address*."""
        if self._scanner is None:
            return None

        try:
            if hasattr(self._scanner, 'backend') and self._scanner.backend:
                data = self._scanner.backend.read_bytes(address, 4)
                if data and len(data) >= 4:
                    return struct.unpack('<f', data[:4])[0]
            else:
                from src.memory.scanner import ValueType
                return self._scanner.read_value(address, ValueType.FLOAT)
        except Exception as exc:
            logger.debug("Float read error @ 0x%08X: %s", address, exc)
        return None

    def _write_float(self, address: int, value: float) -> bool:
        """Write a single-precision float to *address*."""
        if self._scanner is None:
            return False

        try:
            data = struct.pack('<f', value)
            if hasattr(self._scanner, 'backend') and self._scanner.backend:
                self._scanner.backend.write_bytes(address, data)
                return True
            else:
                from src.memory.scanner import ValueType
                return self._scanner.write_value(address, value, ValueType.FLOAT)
        except Exception as exc:
            logger.debug("Float write error @ 0x%08X: %s", address, exc)
        return False

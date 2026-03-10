"""
ML Predictor for dynamic memory address resolution.
Uses historical data and pattern matching to predict addresses in new sessions.

EXPERIMENTAL FEATURE:
This module uses machine learning techniques to predict memory addresses across
game sessions. It tracks historical data, computes module offsets (ASLR-resistant),
and validates using contextual memory signatures.

Status: Experimental - may require tuning for optimal accuracy.
"""

import logging
import json
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger('napoleon.memory.ml_predictor')


@dataclass
class AddressHistory:
    """Historical record of a successful address."""
    cheat_type: str
    module_name: str
    module_offset: int  # Offset from module base
    signature_context: bytes  # 16 bytes surrounding the address
    address: int
    session_id: str
    timestamp: str
    success_count: int = 1


class MLPredictor:
    """
    Machine learning predictor for memory addresses.
    
    Features:
    - Track historical successful addresses across sessions
    - Compute module offsets relative to base (ASLR-resistant)
    - Contextual memory signatures for validation
    - Fallback integration with CheatManager
    """
    
    def __init__(
        self,
        data_file: Optional[str] = None,
        max_history_per_cheat: int = 100,
    ):
        """
        Initialize ML predictor.
        
        Args:
            data_file: Path to store historical data
            max_history_per_cheat: Maximum history entries per cheat type
        """
        self.data_file = Path(data_file) if data_file else Path.cwd() / 'address_history.json'
        self.max_history_per_cheat = max_history_per_cheat
        
        self._history: Dict[str, List[AddressHistory]] = {}  # cheat_type -> histories
        self._module_bases: Dict[str, int] = {}  # module_name -> base_address
        self._current_session_id = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Load existing history
        self._load_history()
    
    def set_module_base(self, module_name: str, base_address: int) -> None:
        """
        Set the base address of a module.
        
        Args:
            module_name: Module name (e.g., 'napoleon.exe')
            base_address: Base address in current session
        """
        self._module_bases[module_name] = base_address
        logger.debug("Module base set: %s = 0x%X", module_name, base_address)
    
    def get_module_base(self, module_name: str) -> Optional[int]:
        """Get the base address of a module."""
        return self._module_bases.get(module_name)
    
    def record_successful_address(
        self,
        cheat_type: str,
        address: int,
        module_name: str = 'napoleon.exe',
        signature_context: Optional[bytes] = None,
    ) -> None:
        """
        Record a successful address for future predictions.
        
        Args:
            cheat_type: Type of cheat
            address: Successful memory address
            module_name: Module containing the address
            signature_context: 16 bytes surrounding the address
        """
        module_base = self._module_bases.get(module_name, 0)
        module_offset = address - module_base
        
        history_entry = AddressHistory(
            cheat_type=cheat_type,
            module_name=module_name,
            module_offset=module_offset,
            signature_context=signature_context or b'',
            address=address,
            session_id=self._current_session_id,
            timestamp=datetime.now().isoformat(),
        )
        
        # Add to history
        if cheat_type not in self._history:
            self._history[cheat_type] = []
        
        self._history[cheat_type].append(history_entry)
        
        # Trim history if needed
        if len(self._history[cheat_type]) > self.max_history_per_cheat:
            self._history[cheat_type] = self._history[cheat_type][-self.max_history_per_cheat:]
        
        # Save to disk
        self._save_history()
        
        logger.debug(
            "Recorded address for %s: 0x%X (offset=0x%X in %s)",
            cheat_type, address, module_offset, module_name
        )
    
    def predict_address(
        self,
        cheat_type: str,
        module_name: str = 'napoleon.exe',
        memory_scanner: Optional[Any] = None,
    ) -> Optional[int]:
        """
        Predict an address for a cheat type based on historical data.
        
        Args:
            cheat_type: Type of cheat
            module_name: Module to search in
            memory_scanner: Optional scanner for signature validation
            
        Returns:
            Predicted address or None
        """
        if cheat_type not in self._history:
            logger.debug("No history for cheat type: %s", cheat_type)
            return None
        
        module_base = self._module_bases.get(module_name)
        if module_base is None:
            logger.warning("Module base not set for %s", module_name)
            return None
        
        histories = self._history[cheat_type]
        if not histories:
            return None
        
        # Use the most recent entry with highest success count
        best_history = max(histories, key=lambda h: h.success_count)
        
        # Calculate predicted address
        predicted_address = module_base + best_history.module_offset
        
        logger.info(
            "Predicted address for %s: 0x%X (based on %d successful uses)",
            cheat_type, predicted_address, best_history.success_count
        )
        
        # Validate with signature if scanner provided
        if memory_scanner and best_history.signature_context:
            if not self._validate_signature(
                memory_scanner,
                predicted_address,
                best_history.signature_context,
            ):
                logger.warning("Signature validation failed for predicted address")
                return None
        
        return predicted_address
    
    def _validate_signature(
        self,
        memory_scanner: Any,
        address: int,
        expected_context: bytes,
        context_size: int = 16,
    ) -> bool:
        """
        Validate a predicted address by checking surrounding bytes.
        
        Args:
            memory_scanner: MemoryScanner instance
            address: Predicted address
            expected_context: Expected byte pattern
            context_size: Size of context to check
            
        Returns:
            bool: True if signature matches
        """
        if not memory_scanner.backend:
            return False
        
        try:
            # Read surrounding bytes
            context_bytes = memory_scanner.backend.read_bytes(address, context_size)
            
            if not context_bytes or len(context_bytes) < len(expected_context):
                return False
            
            # Simple byte comparison (could be enhanced with fuzzy matching)
            return context_bytes[:len(expected_context)] == expected_context
            
        except Exception:
            return False
    
    def teach_from_scan_results(
        self,
        cheat_type: str,
        scan_results: List[Tuple[int, Any]],
        module_name: str = 'napoleon.exe',
        memory_scanner: Optional[Any] = None,
    ) -> int:
        """
        Learn from manual scan results.
        
        Args:
            cheat_type: Type of cheat
            scan_results: List of (address, value) tuples from scanner
            module_name: Module name
            memory_scanner: Optional scanner for context
            
        Returns:
            Number of addresses recorded
        """
        if not scan_results:
            return 0
        
        count = 0
        for address, value in scan_results:
            # Read context bytes
            context = b''
            if memory_scanner and memory_scanner.backend:
                try:
                    context = memory_scanner.backend.read_bytes(address, 16) or b''
                except Exception:
                    pass
            
            self.record_successful_address(
                cheat_type=cheat_type,
                address=address,
                module_name=module_name,
                signature_context=context,
            )
            count += 1
        
        logger.info("Taught %d addresses for %s", count, cheat_type)
        return count
    
    def increment_success_count(self, cheat_type: str, address: int) -> None:
        """
        Increment success count for a recorded address.
        
        Args:
            cheat_type: Cheat type
            address: Address that was successful
        """
        if cheat_type not in self._history:
            return
        
        # Find matching history entry
        for history in self._history[cheat_type]:
            if history.address == address:
                history.success_count += 1
                break
        
        # Save updated history
        self._save_history()
    
    def clear_history(self, cheat_type: Optional[str] = None) -> None:
        """
        Clear prediction history.
        
        Args:
            cheat_type: Specific cheat type to clear, or None for all
        """
        if cheat_type:
            if cheat_type in self._history:
                del self._history[cheat_type]
                logger.info("Cleared history for %s", cheat_type)
        else:
            self._history.clear()
            logger.info("Cleared all prediction history")
        
        self._save_history()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get predictor statistics."""
        return {
            'total_cheat_types': len(self._history),
            'total_entries': sum(len(h) for h in self._history.values()),
            'session_id': self._current_session_id,
            'module_bases': len(self._module_bases),
        }
    
    def _load_history(self) -> None:
        """Load history from disk."""
        if not self.data_file.exists():
            return
        
        try:
            with open(self.data_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            for cheat_type, entries in data.items():
                self._history[cheat_type] = []
                for entry in entries:
                    # FIX: Convert hex string back to bytes
                    if 'signature_context' in entry and entry['signature_context']:
                        entry['signature_context'] = bytes.fromhex(entry['signature_context'])
                    else:
                        entry['signature_context'] = b''
                    
                    self._history[cheat_type].append(AddressHistory(**entry))
            
            logger.info(
                "Loaded ML prediction history: %d cheat types, %d total entries",
                len(self._history),
                sum(len(h) for h in self._history.values())
            )
            
        except Exception as e:
            logger.error("Failed to load ML history: %s", e)
    
    def _save_history(self) -> None:
        """Save history to disk."""
        try:
            data = {}
            for cheat_type, entries in self._history.items():
                data[cheat_type] = [
                    {
                        'cheat_type': e.cheat_type,
                        'module_name': e.module_name,
                        'module_offset': e.module_offset,
                        'signature_context': e.signature_context.hex() if e.signature_context else '',
                        'address': e.address,
                        'session_id': e.session_id,
                        'timestamp': e.timestamp,
                        'success_count': e.success_count,
                    }
                    for e in entries
                ]
            
            self.data_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
            
            logger.debug("Saved ML prediction history to %s", self.data_file)
            
        except Exception as e:
            logger.error("Failed to save ML history: %s", e)

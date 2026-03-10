"""
Machine Learning Predictor for Memory Addresses.
Uses multi-factor analysis (module offsets, contextual signatures, and value types)
to predict and locate dynamic memory addresses across game sessions.
"""

import json
import logging
import struct
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from src.memory.scanner import MemoryScanner, ValueType

logger = logging.getLogger('napoleon.memory.ml_predictor')

_MODEL_FILE = Path(__file__).resolve().parents[2] / 'tables' / 'ml_model.json'

class MLPredictor:
    """
    Tracks and predicts memory addresses based on historical patterns.
    Analyzes module offsets and surrounding memory bytes (signatures).
    """

    def __init__(self, model_file: Path = _MODEL_FILE):
        self.model_file = model_file
        self.models: Dict[str, Dict[str, Any]] = {}
        self.load_model()

    def load_model(self) -> None:
        """Load the trained models from disk."""
        if not self.model_file.exists():
            self.models = {}
            return

        try:
            with open(self.model_file, 'r', encoding='utf-8') as f:
                self.models = json.load(f)
            logger.info("Loaded ML model from %s", self.model_file)
        except Exception as e:
            logger.error("Failed to load ML model: %s", e)
            self.models = {}

    def save_model(self) -> None:
        """Save the trained models to disk."""
        try:
            self.model_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.model_file, 'w', encoding='utf-8') as f:
                json.dump(self.models, f, indent=4)
            logger.info("Saved ML model to %s", self.model_file)
        except Exception as e:
            logger.error("Failed to save ML model: %s", e)

    def _get_module_base(self, scanner: MemoryScanner, module_name: str = 'napoleon.exe') -> Optional[int]:
        """Get the base address of a module."""
        if not scanner.is_attached() or not scanner.backend:
            return None

        try:
            import psutil
            process = psutil.Process(scanner.process_manager.pid)
            for mmap in process.memory_maps(grouped=False):
                path_lower = mmap.path.lower() if mmap.path else ''
                if module_name.lower() in path_lower:
                    base = int(mmap.addr.split('-')[0], 16) if isinstance(mmap.addr, str) else mmap.addr
                    return base
        except Exception as e:
            logger.error("Failed to get module base for %s: %s", module_name, e)
        return None

    def _compute_signature(self, address: int, scanner: MemoryScanner, window: int = 16) -> Optional[str]:
        """
        Read `window` bytes before and after the address to create a contextual signature.
        Returns a hex string representation with wildcards for dynamic parts if necessary.
        """
        if not scanner.is_attached() or not scanner.backend:
            return None

        try:
            # Read 16 bytes before, the value itself (assume 4 bytes), and 16 bytes after
            start_addr = address - window
            read_size = window * 2 + 4
            data = scanner.backend.read_bytes(start_addr, read_size)

            if not data or len(data) < read_size:
                return None

            # Convert to hex string, replacing the target value with wildcards
            hex_parts = []
            for i, b in enumerate(data):
                if window <= i < window + 4:  # Mask out the actual value
                    hex_parts.append('??')
                else:
                    hex_parts.append(f'{b:02X}')

            return ' '.join(hex_parts)
        except Exception as e:
            logger.debug("Failed to compute signature for 0x%08X: %s", address, e)
            return None

    def learn(self, name: str, address: int, value_type: ValueType, scanner: MemoryScanner) -> bool:
        """
        Train the model on a known good address.
        Records the offset from module base and the contextual memory signature.
        """
        base_addr = self._get_module_base(scanner)
        if base_addr is None:
            logger.warning("MLPredictor: Cannot learn %s, module base not found.", name)
            return False

        offset = address - base_addr
        signature = self._compute_signature(address, scanner)

        if name not in self.models:
            self.models[name] = {
                'offsets': {},
                'signatures': {},
                'value_type': value_type.value,
                'successful_uses': 0
            }

        model = self.models[name]

        # Track offset frequency
        offset_key = str(offset)
        model['offsets'][offset_key] = model['offsets'].get(offset_key, 0) + 1

        # Track signature frequency
        if signature:
            model['signatures'][signature] = model['signatures'].get(signature, 0) + 1

        model['successful_uses'] += 1
        self.save_model()
        logger.info("MLPredictor: Learned %s at offset +0x%X", name, offset)
        return True

    def predict(self, name: str, scanner: MemoryScanner) -> Optional[int]:
        """
        Attempt to predict the address for a given name using historical data.
        Returns the predicted address if confident, or None.
        """
        if name not in self.models:
            return None

        model = self.models[name]
        base_addr = self._get_module_base(scanner)

        if base_addr is None:
            return None

        # 1. Try the most frequent offset first
        if not model['offsets']:
            return None

        # Get offset with highest frequency
        best_offset_str = max(model['offsets'].items(), key=lambda x: x[1])[0]
        best_offset = int(best_offset_str)
        predicted_addr = base_addr + best_offset

        # Verify the signature matches if we have one
        if model['signatures']:
            current_sig = self._compute_signature(predicted_addr, scanner)
            if current_sig:
                # Simple exact match for now; could be enhanced with fuzziness
                if current_sig in model['signatures']:
                    logger.info("MLPredictor: Confident prediction for %s at 0x%08X (Offset + Signature match)", name, predicted_addr)
                    return predicted_addr

            # If signature fails at the exact offset, we could fall back to AOB scanning
            # using the most frequent signature around the base_addr + offset area.
            best_sig = max(model['signatures'].items(), key=lambda x: x[1])[0]
            logger.info("MLPredictor: Offset signature mismatch for %s. Attempting AOB fallback scan.", name)

            # Simple AOB fallback scan using the signature
            matches = scanner.scan_aob(best_sig, max_results=1, timeout=5.0)
            if matches:
                found_addr = matches[0]
                logger.info("MLPredictor: Recovered %s via signature scan at 0x%08X", name, found_addr)
                # Auto-learn the new offset
                self.learn(name, found_addr, ValueType(model['value_type']), scanner)
                return found_addr

        logger.info("MLPredictor: Basic prediction for %s at 0x%08X (Offset only)", name, predicted_addr)
        return predicted_addr

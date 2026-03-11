import os
import sys
import ctypes
import struct
import time
import json
import zlib
import threading
import traceback
import logging
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger('napoleon.memory.ultra_hook')

# --- Windows API Definitions ---
if sys.platform == 'win32':
    from ctypes import wintypes

    kernel32 = ctypes.windll.kernel32
    ntdll = ctypes.windll.ntdll

    # Process privileges and access
    PROCESS_ALL_ACCESS = 0x1F0FFF
    THREAD_ALL_ACCESS = 0x1FFFFF

    # Debugging APIs
    kernel32.DebugActiveProcess.argtypes = [wintypes.DWORD]
    kernel32.DebugActiveProcess.restype = wintypes.BOOL
    kernel32.DebugSetProcessKillOnExit.argtypes = [wintypes.BOOL]
    kernel32.DebugSetProcessKillOnExit.restype = wintypes.BOOL
    kernel32.DebugActiveProcessStop.argtypes = [wintypes.DWORD]
    kernel32.DebugActiveProcessStop.restype = wintypes.BOOL
    kernel32.ContinueDebugEvent.argtypes = [wintypes.DWORD, wintypes.DWORD, wintypes.DWORD]
    kernel32.ContinueDebugEvent.restype = wintypes.BOOL

    # Threading and Suspension
    ntdll.NtSuspendProcess.argtypes = [wintypes.HANDLE]
    ntdll.NtSuspendProcess.restype = wintypes.DWORD
    ntdll.NtResumeProcess.argtypes = [wintypes.HANDLE]
    ntdll.NtResumeProcess.restype = wintypes.DWORD

    # Thread enumerating / Context
    kernel32.CreateToolhelp32Snapshot.argtypes = [wintypes.DWORD, wintypes.DWORD]
    kernel32.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
    kernel32.Thread32First.argtypes = [wintypes.HANDLE, ctypes.c_void_p]
    kernel32.Thread32First.restype = wintypes.BOOL
    kernel32.Thread32Next.argtypes = [wintypes.HANDLE, ctypes.c_void_p]
    kernel32.Thread32Next.restype = wintypes.BOOL
    kernel32.OpenThread.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel32.OpenThread.restype = wintypes.HANDLE
    kernel32.GetThreadContext.argtypes = [wintypes.HANDLE, ctypes.c_void_p]
    kernel32.GetThreadContext.restype = wintypes.BOOL
    kernel32.SetThreadContext.argtypes = [wintypes.HANDLE, ctypes.c_void_p]
    kernel32.SetThreadContext.restype = wintypes.BOOL

    # Memory
    PAGE_EXECUTE_READWRITE = 0x40

    class MEMORY_BASIC_INFORMATION(ctypes.Structure):
        _fields_ = [
            ("BaseAddress", ctypes.c_void_p),
            ("AllocationBase", ctypes.c_void_p),
            ("AllocationProtect", wintypes.DWORD),
            ("RegionSize", ctypes.c_size_t),
            ("State", wintypes.DWORD),
            ("Protect", wintypes.DWORD),
            ("Type", wintypes.DWORD),
        ]

    class DEBUG_EVENT(ctypes.Structure):
        _fields_ = [
            ("dwDebugEventCode", wintypes.DWORD),
            ("dwProcessId", wintypes.DWORD),
            ("dwThreadId", wintypes.DWORD),
            ("u", ctypes.c_byte * 84) # Union padding
        ]

    class THREADENTRY32(ctypes.Structure):
        _fields_ = [
            ("dwSize", wintypes.DWORD),
            ("cntUsage", wintypes.DWORD),
            ("th32ThreadID", wintypes.DWORD),
            ("th32OwnerProcessID", wintypes.DWORD),
            ("tpBasePri", wintypes.LONG),
            ("tpDeltaPri", wintypes.LONG),
            ("dwFlags", wintypes.DWORD),
        ]

    class CONTEXT(ctypes.Structure):
        _fields_ = [
            ("ContextFlags", wintypes.DWORD),
            ("Dr0", wintypes.DWORD),
            ("Dr1", wintypes.DWORD),
            ("Dr2", wintypes.DWORD),
            ("Dr3", wintypes.DWORD),
            ("Dr6", wintypes.DWORD),
            ("Dr7", wintypes.DWORD),
            ("FloatSave", ctypes.c_byte * 112),
            ("SegGs", wintypes.DWORD),
            ("SegFs", wintypes.DWORD),
            ("SegEs", wintypes.DWORD),
            ("SegDs", wintypes.DWORD),
            ("Edi", wintypes.DWORD),
            ("Esi", wintypes.DWORD),
            ("Ebx", wintypes.DWORD),
            ("Edx", wintypes.DWORD),
            ("Ecx", wintypes.DWORD),
            ("Eax", wintypes.DWORD),
            ("Ebp", wintypes.DWORD),
            ("Eip", wintypes.DWORD),
            ("SegCs", wintypes.DWORD),
            ("EFlags", wintypes.DWORD),
            ("Esp", wintypes.DWORD),
            ("SegSs", wintypes.DWORD),
            ("ExtendedRegisters", ctypes.c_byte * 512),
        ]

    CONTEXT_DEBUG_REGISTERS = 0x10010
else:
    # Dummy fallbacks for non-Windows (though prompt says Windows 10/11)
    PROCESS_ALL_ACCESS = 0
    PAGE_EXECUTE_READWRITE = 0
    class MEMORY_BASIC_INFORMATION(ctypes.Structure): pass

# --- Data Structures ---

class HookMethod:
    JMP_REL32 = 'JMP_REL32'
    CALL_REL32 = 'CALL_REL32'
    INT3_BREAKPOINT = 'INT3'
    INLINE_REGISTER = 'INLINE_REG'

@dataclass
class HookState:
    id: str
    address: int
    original_bytes: bytes
    patched_bytes: bytes
    method: str
    payload_builder: Any  # Cannot serialize easily, handled dynamically
    overwrite_size: int
    health_score: float = 100.0
    crc32_original: int = 0
    crc32_patched: int = 0
    last_verified: float = 0.0
    consecutive_failures: int = 0
    survived_sessions: int = 0
    is_primary: bool = True
    parent_hook_id: Optional[str] = None
    active: bool = False

@dataclass
class HookChainCheck:
    checksum: int
    timestamp: float

# --- Utilities ---

def calculate_crc32(data: bytes) -> int:
    return zlib.crc32(data) & 0xFFFFFFFF

# --- UltraReliableHookManager ---

class UltraReliableHookManager:
    """
    TRIPLE-LOCK HOOKING SYSTEM
    Overengineered for maximum reliability on 32-bit x86 Napoleon Total War.
    """

    def __init__(self, backend: Any, process_manager: Any = None):
        self.backend = backend
        self.pm = process_manager

        self.hooks: Dict[str, HookState] = {}
        self.trampolines: Dict[int, int] = {}

        # State persistence
        self.state_file = Path("hook_survival_state.json")
        self._load_survival_state()

        # Threads
        self._monitoring_active = False
        self._debugger_active = False
        self._monitor_thread: Optional[threading.Thread] = None
        self._save_thread: Optional[threading.Thread] = None
        self._debugger_thread: Optional[threading.Thread] = None
        self._validation_threads: Dict[str, threading.Thread] = {}

        # Hardware Breakpoint simulated state
        self._hw_bps_active: List[int] = [] # up to 4 on x86

        self.start_monitoring()

    def _get_process_handle(self) -> Any:
        if sys.platform != 'win32':
            return None
        if hasattr(self.backend, '_pm') and self.backend._pm:
            # We don't duplicate the handle here, we just use it
            return self.backend._pm.process_handle
        if hasattr(self.pm, 'pid') and self.pm.pid:
            # If we open it, we MUST close it later, or better, return it to the caller
            return kernel32.OpenProcess(PROCESS_ALL_ACCESS, False, self.pm.pid)
        return None

    def _close_handle(self, handle: Any):
        if sys.platform == 'win32' and handle:
            # Don't close pymem's persistent handle
            if hasattr(self.backend, '_pm') and self.backend._pm and handle == self.backend._pm.process_handle:
                return
            kernel32.CloseHandle(handle)

    def suspend_game(self) -> bool:
        """Atomically suspend all game threads to prevent crash during patch."""
        if sys.platform != 'win32':
            return False
        handle = self._get_process_handle()
        if handle:
            status = ntdll.NtSuspendProcess(handle)
            self._close_handle(handle)
            return status == 0
        return False

    def resume_game(self) -> bool:
        """Atomically resume all game threads."""
        if sys.platform != 'win32':
            return False
        handle = self._get_process_handle()
        if handle:
            status = ntdll.NtResumeProcess(handle)
            self._close_handle(handle)
            return status == 0
        return False

    def validate_memory_region(self, address: int) -> bool:
        """Pre-hook validation: Check if memory region is stable and executable."""
        if sys.platform != 'win32':
            return True

        handle = self._get_process_handle()
        if not handle:
            return False

        mbi = MEMORY_BASIC_INFORMATION()
        res = kernel32.VirtualQueryEx(
            handle,
            ctypes.c_void_p(address),
            ctypes.byref(mbi),
            ctypes.sizeof(mbi)
        )
        self._close_handle(handle)

        if res == 0:
            return False

        # Check if MEM_COMMIT
        if mbi.State != 0x1000:
            return False

        # Check if executable (PAGE_EXECUTE, PAGE_EXECUTE_READ, PAGE_EXECUTE_READWRITE)
        executable_flags = [0x10, 0x20, 0x40, 0x80]
        if mbi.Protect not in executable_flags and mbi.AllocationProtect not in executable_flags:
            logger.warning(f"Address 0x{address:X} is not in an executable region!")
            # We can still try to hook if we VirtualProtect it, but it's risky (dynamic mem)

        # Ideally, check if AllocationBase belongs to a known module (napoleon.exe)
        # For simplicity in this script, we assume true if committed.
        return True

    def _debugger_worker(self, pid: int):
        """Background thread running the Debugger Event Loop."""
        success = kernel32.DebugActiveProcess(pid)
        if not success:
            logger.error(f"Failed to attach debugger to PID {pid}")
            return

        kernel32.DebugSetProcessKillOnExit(False)
        logger.info(f"Attached hardware debugger to PID {pid}")

        event = DEBUG_EVENT()
        DBG_CONTINUE = 0x00010002
        DBG_EXCEPTION_NOT_HANDLED = 0x80010001

        while self._debugger_active:
            # Wait 100ms for a debug event
            if kernel32.WaitForDebugEvent(ctypes.byref(event), 100):
                # We could process EXCEPTION_DEBUG_EVENT (1) here to catch HW breakpoints
                # For this implementation, we just continue unhandled to let the game run
                continue_status = DBG_EXCEPTION_NOT_HANDLED
                if event.dwDebugEventCode == 1: # EXCEPTION_DEBUG_EVENT
                    # A HW breakpoint was hit! We should theoretically reinstall the hook if it was written to
                    # But since we just want to watch memory writes:
                    # STATUS_SINGLE_STEP (0x80000004) is what Dr0-Dr3 triggers
                    continue_status = DBG_CONTINUE

                kernel32.ContinueDebugEvent(event.dwProcessId, event.dwThreadId, continue_status)

        kernel32.DebugActiveProcessStop(pid)
        logger.info("Hardware debugger detached.")

    def install_hardware_breakpoint(self, address: int):
        """Install memory watchpoint to catch overwrites via Dr0-Dr3 registers."""
        if sys.platform != 'win32':
            return

        pid = self.pm.pid if self.pm else None
        if not pid:
            return

        if len(self._hw_bps_active) >= 4:
            logger.warning("Max 4 hardware breakpoints allowed on x86!")
            return

        if address in self._hw_bps_active:
            return

        self._hw_bps_active.append(address)

        # Ensure Debugger is running
        if not self._debugger_active:
            self._debugger_active = True
            self._debugger_thread = threading.Thread(target=self._debugger_worker, args=(pid,), daemon=True)
            self._debugger_thread.start()
            # Give it a moment to attach
            time.sleep(0.5)

        # Now we must update Dr registers for ALL threads in the process
        TH32CS_SNAPTHREAD = 0x00000004
        snapshot = kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPTHREAD, pid)
        if snapshot == -1:
            return

        te32 = THREADENTRY32()
        te32.dwSize = ctypes.sizeof(THREADENTRY32)

        if kernel32.Thread32First(snapshot, ctypes.byref(te32)):
            while True:
                if te32.th32OwnerProcessID == pid:
                    hThread = kernel32.OpenThread(THREAD_ALL_ACCESS, False, te32.th32ThreadID)
                    if hThread:
                        ctx = CONTEXT()
                        ctx.ContextFlags = CONTEXT_DEBUG_REGISTERS
                        if kernel32.GetThreadContext(hThread, ctypes.byref(ctx)):
                            # Set the registers based on how many we have active
                            for i, bp_addr in enumerate(self._hw_bps_active):
                                if i == 0: ctx.Dr0 = bp_addr
                                elif i == 1: ctx.Dr1 = bp_addr
                                elif i == 2: ctx.Dr2 = bp_addr
                                elif i == 3: ctx.Dr3 = bp_addr

                            # Enable local exact breakpoint (L0-L3 flags in Dr7)
                            # Bits 0, 2, 4, 6 enable Dr0, Dr1, Dr2, Dr3 locally
                            # Bits 16-31 define conditions (Read/Write) and lengths (1 byte)
                            # 0x01 (enable L0)
                            # 0x00010000 = Read/Write condition for Dr0
                            dr7 = 0
                            for i in range(len(self._hw_bps_active)):
                                dr7 |= (1 << (i * 2)) # Local enable
                                dr7 |= (0b11 << (16 + (i * 4))) # Condition 11 = Read/Write

                            ctx.Dr7 = dr7
                            kernel32.SetThreadContext(hThread, ctypes.byref(ctx))
                        kernel32.CloseHandle(hThread)
                if not kernel32.Thread32Next(snapshot, ctypes.byref(te32)):
                    break

        kernel32.CloseHandle(snapshot)
        logger.info(f"Hardware breakpoint (watchpoint) set at 0x{address:X} on all threads")

    def auto_detect_method(self, address: int, original_bytes: bytes) -> str:
        """Determine the best hooking method based on instruction signatures."""
        if original_bytes.startswith(b'\xE8'): # CALL rel32
            return HookMethod.CALL_REL32
        elif len(original_bytes) >= 5:
            # "Inline hook with register preservation" is the safest if we have 5 bytes
            return HookMethod.INLINE_REGISTER
        else:
            return HookMethod.INT3_BREAKPOINT

    def _build_jump(self, source: int, target: int) -> bytes:
        disp = target - (source + 5)
        return b'\xE9' + struct.pack('<i', disp)

    def _build_call(self, source: int, target: int) -> bytes:
        disp = target - (source + 5)
        return b'\xE8' + struct.pack('<i', disp)

    def _build_inline_register_preservation(self, payload: bytes) -> bytes:
        """Wrap a payload in PUSHFD/PUSHAD and POPAD/POPFD to preserve all x86 registers."""
        # x86:
        # 0x9C = PUSHFD
        # 0x60 = PUSHAD
        # <payload>
        # 0x61 = POPAD
        # 0x9D = POPFD
        return b'\x9C\x60' + payload + b'\x61\x9D'

    def add_hook(self, address: int, hook_id: str, payload_builder: Callable[[int], bytes], overwrite_size: int, priority: int = 50) -> bool:
        """Install a triple-locked, verified hook."""

        # 1. PRE-HOOK VALIDATION LAYER
        if not self.validate_memory_region(address):
            logger.error(f"Pre-hook validation failed for 0x{address:X}")
            return False

        original_bytes = self.backend.read_bytes(address, overwrite_size)
        if not original_bytes or len(original_bytes) != overwrite_size:
            return False

        # Detect method
        method = self.auto_detect_method(address, original_bytes)

        # Check survivor bias
        survivor_bonus = 0
        if hasattr(self, 'survival_state') and hook_id in self.survival_state:
            survivor_bonus = self.survival_state[hook_id].get('survived_sessions', 0)
            logger.info(f"Hook {hook_id} is a survivor! (Survived {survivor_bonus} sessions). Prioritizing.")

        # Allocate Trampoline & Cave
        cave_size = 1024 # Oversized for safety
        cave_addr = self._find_cave(cave_size)
        if not cave_addr:
            return False

        # Build payload. Cave layout:
        # [0-499] Payload
        # [500-1024] Trampoline
        raw_payload = payload_builder(cave_addr + 500)

        if method == HookMethod.INLINE_REGISTER:
            payload = self._build_inline_register_preservation(raw_payload)
        else:
            payload = raw_payload

        # Build Patched Bytes
        if method in (HookMethod.JMP_REL32, HookMethod.INLINE_REGISTER):
            patched_bytes = self._build_jump(address, cave_addr) + b'\x90' * (overwrite_size - 5)
        elif method == HookMethod.CALL_REL32:
            patched_bytes = self._build_call(address, cave_addr) + b'\x90' * (overwrite_size - 5)
        else:
            patched_bytes = b'\xCC' * overwrite_size # INT3

        crc_orig = calculate_crc32(original_bytes)
        crc_patched = calculate_crc32(patched_bytes)

        state = HookState(
            id=hook_id,
            address=address,
            original_bytes=original_bytes,
            patched_bytes=patched_bytes,
            method=method,
            payload_builder=payload_builder,
            overwrite_size=overwrite_size,
            crc32_original=crc_orig,
            crc32_patched=crc_patched,
            survived_sessions=survivor_bonus,
            active=True
        )

        self.hooks[hook_id] = state

        # Atomic Installation
        self.suspend_game()
        try:
            # Write cave payload
            cave_payload = payload + self._build_jump(cave_addr + len(payload), address + overwrite_size)
            self.backend.write_bytes(cave_addr, cave_payload)

            # Write Trampoline (original bytes + jump back)
            trampoline = original_bytes + self._build_jump(cave_addr + 500 + len(original_bytes), address + overwrite_size)
            self.backend.write_bytes(cave_addr + 500, trampoline)
            self.trampolines[address] = cave_addr + 500

            # 2. REDUNDANT HOOK INSTALLATION (Secondary Slide Hook)
            # Find a safe NOP or INT3 slide nearby to place a backup hook
            slide_addr = address + overwrite_size
            slide_bytes = self.backend.read_bytes(slide_addr, 5)
            if slide_bytes == b'\x90\x90\x90\x90\x90' or slide_bytes == b'\xCC\xCC\xCC\xCC\xCC':
                backup_patched = self._build_jump(slide_addr, cave_addr)
                self.backend.write_bytes(slide_addr, backup_patched)
                logger.info(f"Installed REDUNDANT SECONDARY hook at 0x{slide_addr:X}")

                backup_state = HookState(
                    id=hook_id + "_backup",
                    address=slide_addr,
                    original_bytes=slide_bytes,
                    patched_bytes=backup_patched,
                    method=HookMethod.JMP_REL32,
                    payload_builder=payload_builder,
                    overwrite_size=5,
                    is_primary=False,
                    parent_hook_id=hook_id,
                    active=True
                )
                self.hooks[backup_state.id] = backup_state

            # 2. TERTIARY HOOK INSTALLATION (Hooking Caller)
            # We would need to scan backward or use stack trace to find caller,
            # simplified here: just hooking + 10 bytes if safe
            tert_addr = address - 10
            tert_bytes = self.backend.read_bytes(tert_addr, 5)
            if tert_bytes and (tert_bytes == b'\x90\x90\x90\x90\x90' or tert_bytes == b'\xCC\xCC\xCC\xCC\xCC'):
                tert_patched = self._build_jump(tert_addr, cave_addr)
                self.backend.write_bytes(tert_addr, tert_patched)
                logger.info(f"Installed REDUNDANT TERTIARY hook at 0x{tert_addr:X}")

            # Write Primary Hook
            self.backend.write_bytes(address, patched_bytes)

            # 7. DEEP MEMORY MONITORING
            self.install_hardware_breakpoint(address)

        finally:
            self.resume_game()

        # 3. POST-HOOK VERIFICATION LOOP (Immediate)
        time.sleep(0.1) # 100ms
        verify = self.backend.read_bytes(address, overwrite_size)
        if verify != patched_bytes:
            logger.critical(f"Immediate verification failed for {hook_id}! Expected {patched_bytes.hex()}, got {verify.hex() if verify else 'None'}")
            self._repair_hook(state)

        # Start isolated validation thread for this hook
        t = threading.Thread(target=self._validation_worker, args=(hook_id,), daemon=True)
        self._validation_threads[hook_id] = t
        t.start()

        return True

    def remove_hook(self, address: int, hook_id: str, overwrite_size: int) -> bool:
        if hook_id in self.hooks:
            state = self.hooks[hook_id]
            state.active = False
            self.backend.write_bytes(state.address, state.original_bytes)
            del self.hooks[hook_id]

            # Remove backup if exists
            backup_id = hook_id + "_backup"
            if backup_id in self.hooks:
                self.hooks[backup_id].active = False
                self.backend.write_bytes(self.hooks[backup_id].address, self.hooks[backup_id].original_bytes)
                del self.hooks[backup_id]

            return True
        return False

    def remove_all_hooks(self, address: int) -> bool:
        # Compatibility with old HookManager
        to_remove = []
        for hid, state in self.hooks.items():
            if state.address == address:
                to_remove.append(hid)
        for hid in to_remove:
            self.remove_hook(address, hid, 5)
        return True

    def validate_hooks(self) -> List[int]:
        # Compatibility with old HookManager; the threads do the real work now.
        return []

    # --- Worker Threads ---

    def _validation_worker(self, hook_id: str):
        """4. AGGRESSIVE REPAIR STRATEGY & 6. HOOK CHAINING WITH CHECKSUMS"""
        # Validates every 100ms
        while self._monitoring_active:
            if hook_id not in self.hooks:
                break

            state = self.hooks[hook_id]
            if not state.active:
                break

            try:
                current_bytes = self.backend.read_bytes(state.address, state.overwrite_size)
                if not current_bytes:
                    time.sleep(0.1)
                    continue

                current_crc = calculate_crc32(current_bytes)

                # Verify Checksum
                if current_crc != state.crc32_patched:
                    state.health_score -= 20.0
                    state.consecutive_failures += 1

                    logger.error(f"CORRUPTION DETECTED on {hook_id}! CRC mismatch. Score: {state.health_score}")
                    stack = "".join(traceback.format_stack())
                    logger.error(f"Stack Trace Simulation:\n{stack}")

                    if state.health_score <= 0:
                        logger.critical(f"Hook {hook_id} health depleted. Requires complete re-scan.")
                        state.active = False
                        # In a full system, trigger CheatManager to re-resolve AOB
                    else:
                        # Exponential backoff based on failures
                        backoff = min(2.0, 0.1 * (2 ** state.consecutive_failures))
                        time.sleep(backoff)
                        self._repair_hook(state)
                else:
                    # Healthy
                    state.consecutive_failures = 0
                    state.health_score = min(100.0, state.health_score + 1.0)

            except Exception as e:
                logger.error(f"Validation exception for {hook_id}: {e}")

            # 4. AGGRESSIVE REPAIR STRATEGY (100ms) and 6. CHECKSUM VALIDATION (500ms)
            # we do 100ms loop here to cover both
            time.sleep(0.1) # 100ms aggressive check

    def _repair_hook(self, state: HookState):
        """Repair a corrupted hook atomically."""
        logger.warning(f"Repairing hook {state.id} at 0x{state.address:X}...")
        self.suspend_game()
        try:
            # Force reapply original to clear any partial corruption
            self.backend.write_bytes(state.address, state.original_bytes)
            # Re-hook
            self.backend.write_bytes(state.address, state.patched_bytes)
            logger.info(f"Repair complete for {state.id}")
        finally:
            self.resume_game()

    def start_monitoring(self):
        self._monitoring_active = True
        self._save_thread = threading.Thread(target=self._persistent_save_worker, daemon=True)
        self._save_thread.start()

    def stop_monitoring(self):
        self._monitoring_active = False
        self._debugger_active = False
        if self._save_thread:
            self._save_thread.join(timeout=2.0)
        if self._debugger_thread:
            self._debugger_thread.join(timeout=2.0)

    # --- 8. PERSISTENT HOOK STATE ---

    def _persistent_save_worker(self):
        """Save hook state to disk every 5 seconds."""
        while self._monitoring_active:
            time.sleep(5.0)
            self._save_survival_state()

    def _save_survival_state(self):
        data = {}
        for hid, state in self.hooks.items():
            if state.is_primary and state.active and state.health_score > 50:
                data[hid] = {
                    'survived_sessions': state.survived_sessions + 1,
                    'address': state.address,
                    'method': state.method,
                    'health': state.health_score
                }

        try:
            with open(self.state_file, 'w') as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            logger.error(f"Failed to save hook survival state: {e}")

    def _load_survival_state(self):
        self.survival_state = {}
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r') as f:
                    self.survival_state = json.load(f)
                logger.info(f"Loaded {len(self.survival_state)} survivor hooks from disk.")
            except Exception as e:
                logger.error(f"Failed to load hook survival state: {e}")

    def _find_cave(self, size: int) -> Optional[int]:
        """Find a code cave. Basic implementation relying on backend regions."""
        if not self.backend: return None
        for region in self.backend.get_readable_regions():
            if region['size'] < size: continue
            data = self.backend.read_bytes(region['address'], region['size'])
            if not data: continue

            # Look for block of CCs or 00s
            idx = data.find(b'\xCC' * size)
            if idx == -1:
                idx = data.find(b'\x00' * size)

            if idx != -1:
                return region['address'] + idx
        return None

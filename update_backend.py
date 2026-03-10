import sys

filepath = 'src/memory/backend.py'
with open(filepath, 'r') as f:
    content = f.read()

import_addition = """
import time
import ctypes
from ctypes import POINTER, Structure, byref, c_bool, c_char_p, c_int, c_size_t, c_ubyte, c_uint32, c_uint64, c_void_p

# --- DMA VMM.DLL CTYPES BINDINGS ---
class VMMDLL_SCATTER_DATA(Structure):
    _fields_ = [
        ("qwA", c_uint64),
        ("pb", POINTER(c_ubyte)),
        ("cb", c_uint32),
        ("f", c_uint32),
        ("cbRead", c_uint32),
    ]

class VMMDLL_MAP_PHYSMEM_ENTRY(Structure):
    _fields_ = [
        ("pa", c_uint64),
        ("cb", c_uint64),
    ]

class VMMDLL_MAP_PHYSMEM(Structure):
    _fields_ = [
        ("dwVersion", c_uint32),
        ("cMap", c_uint32),
        ("pMap", POINTER(VMMDLL_MAP_PHYSMEM_ENTRY)),
    ]

try:
    if sys.platform == 'win32':
        _vmm = ctypes.WinDLL('vmm.dll')
    else:
        _vmm = ctypes.CDLL('vmm.so')

    _VMMDLL_Initialize = _vmm.VMMDLL_Initialize
    _VMMDLL_Initialize.argtypes = [c_int, POINTER(c_char_p)]
    _VMMDLL_Initialize.restype = c_void_p

    _VMMDLL_Close = _vmm.VMMDLL_Close
    _VMMDLL_Close.argtypes = [c_void_p]
    _VMMDLL_Close.restype = None

    _VMMDLL_MemReadScatter = _vmm.VMMDLL_MemReadScatter
    _VMMDLL_MemReadScatter.argtypes = [c_void_p, c_uint32, c_uint32, POINTER(VMMDLL_SCATTER_DATA)]
    _VMMDLL_MemReadScatter.restype = c_uint32

    _VMMDLL_MemWrite = _vmm.VMMDLL_MemWrite
    _VMMDLL_MemWrite.argtypes = [c_void_p, c_uint32, c_uint64, POINTER(c_ubyte), c_uint32]
    _VMMDLL_MemWrite.restype = c_bool

    _VMMDLL_Map_GetPhysMem = _vmm.VMMDLL_Map_GetPhysMem
    _VMMDLL_Map_GetPhysMem.argtypes = [c_void_p, POINTER(POINTER(VMMDLL_MAP_PHYSMEM))]
    _VMMDLL_Map_GetPhysMem.restype = c_bool

    _VMMDLL_MemFree = _vmm.VMMDLL_MemFree
    _VMMDLL_MemFree.argtypes = [c_void_p]
    _VMMDLL_MemFree.restype = None

    VMM_AVAILABLE = True
except Exception as e:
    VMM_AVAILABLE = False

"""

dma_backend_class = """
class DMABackend(MemoryBackend):
    \"\"\"
    High-speed DMA backend interfacing with PCIe Leech / FPGA hardware.
    Utilizes scatter/gather for reads and implements page-level caching to
    mitigate hardware latency.
    \"\"\"

    CACHE_TTL = 0.05  # 50ms cache TTL
    PAGE_SIZE = 4096

    def __init__(self) -> None:
        self._hVMM: Optional[c_void_p] = None
        self._pid: Optional[int] = None
        self._cache: dict = {}  # {page_addr: (timestamp, bytes)}

    def open(self, pid: int) -> bool:
        if not VMM_AVAILABLE:
            return False
        try:
            args = [b"-printf", b"-v", b"-device", b"fpga"]
            argv = (c_char_p * len(args))(*args)
            self._hVMM = _VMMDLL_Initialize(len(args), argv)
            if not self._hVMM:
                return False
            self._pid = pid
            logger.info("DMABackend opened PID %d via PCIe FPGA", pid)
            return True
        except Exception as e:
            logger.error("DMABackend open failed: %s", e)
            return False

    def close(self) -> None:
        if self._hVMM:
            try:
                _VMMDLL_Close(self._hVMM)
            except Exception:
                pass
            self._hVMM = None
            self._pid = None
            self._cache.clear()

    @property
    def is_open(self) -> bool:
        return self._hVMM is not None

    def _read_scatter_pages(self, page_addrs: List[int]) -> None:
        if not self._hVMM or not self._pid:
            return

        now = time.monotonic()
        to_read = [p for p in page_addrs if p not in self._cache or (now - self._cache[p][0]) > self.CACHE_TTL]
        if not to_read:
            return

        flags = 0
        scatter_array = (VMMDLL_SCATTER_DATA * len(to_read))()
        buffers = []

        for i, pa in enumerate(to_read):
            buf = (c_ubyte * self.PAGE_SIZE)()
            buffers.append(buf)
            scatter_array[i].qwA = pa
            scatter_array[i].pb = ctypes.cast(buf, POINTER(c_ubyte))
            scatter_array[i].cb = self.PAGE_SIZE
            scatter_array[i].f = flags

        _VMMDLL_MemReadScatter(self._hVMM, self._pid, len(to_read), scatter_array)

        for i, pa in enumerate(to_read):
            if scatter_array[i].cbRead > 0:
                self._cache[pa] = (now, bytes(buffers[i][:scatter_array[i].cbRead]))
            else:
                self._cache[pa] = (now, b'')

    def read_bytes(self, address: int, size: int) -> Optional[bytes]:
        if not self._hVMM or not self._pid:
            return None

        start_page = address & ~(self.PAGE_SIZE - 1)
        end_page = (address + size - 1) & ~(self.PAGE_SIZE - 1)

        needed_pages = []
        p = start_page
        while p <= end_page:
            needed_pages.append(p)
            p += self.PAGE_SIZE

        self._read_scatter_pages(needed_pages)

        result = bytearray()
        curr_addr = address
        remaining = size

        while remaining > 0:
            page = curr_addr & ~(self.PAGE_SIZE - 1)
            page_offset = curr_addr - page
            chunk_size = min(remaining, self.PAGE_SIZE - page_offset)

            cached_data = self._cache.get(page)
            if not cached_data or not cached_data[1]:
                return None

            page_bytes = cached_data[1]
            if page_offset + chunk_size > len(page_bytes):
                return None

            result.extend(page_bytes[page_offset:page_offset + chunk_size])
            curr_addr += chunk_size
            remaining -= chunk_size

        return bytes(result)

    def write_bytes(self, address: int, data: bytes) -> bool:
        if not self._hVMM or not self._pid:
            return False

        buf = (c_ubyte * len(data)).from_buffer_copy(data)
        res = _VMMDLL_MemWrite(self._hVMM, self._pid, address, buf, len(data))

        start_page = address & ~(self.PAGE_SIZE - 1)
        end_page = (address + len(data) - 1) & ~(self.PAGE_SIZE - 1)
        p = start_page
        while p <= end_page:
            self._cache.pop(p, None)
            p += self.PAGE_SIZE

        return bool(res)

    def get_readable_regions(self) -> List[MemoryRegion]:
        if not self._hVMM:
            return []
        return [
            {'address': 0x00400000, 'size': 0x02000000},
            {'address': 0x10000000, 'size': 0x10000000},
        ]

    def get_physical_regions(self) -> List[MemoryRegion]:
        if not self._hVMM:
            return []

        pMap = POINTER(VMMDLL_MAP_PHYSMEM)()
        if not _VMMDLL_Map_GetPhysMem(self._hVMM, byref(pMap)):
            return []

        regions = []
        map_struct = pMap.contents
        for i in range(map_struct.cMap):
            entry = map_struct.pMap[i]
            regions.append({'address': entry.pa, 'size': entry.cb})

        _VMMDLL_MemFree(pMap)
        return regions

    def read_physical_bytes(self, address: int, size: int) -> Optional[bytes]:
        if not self._hVMM:
            return None
        flags = 0
        buf = (c_ubyte * size)()
        scatter = VMMDLL_SCATTER_DATA(address, ctypes.cast(buf, POINTER(c_ubyte)), size, flags, 0)
        _VMMDLL_MemReadScatter(self._hVMM, 4, 1, byref(scatter))
        if scatter.cbRead == size:
            return bytes(buf)
        return None

class PymemBackend(MemoryBackend):
"""

content = content.replace("class PymemBackend(MemoryBackend):", dma_backend_class)

import_target = "logger = logging.getLogger('napoleon.memory.backend')"
content = content.replace(import_target, import_addition + "\n" + import_target)

candidate_linux_proton = """    if get_platform() == 'linux':
        if is_proton():
            return [
                DMABackend,
                PymemBackend,"""

content = content.replace("""    if get_platform() == 'linux':
        if is_proton():
            return [
                PymemBackend,""", candidate_linux_proton)

candidate_linux_native = """        return [
            DMABackend,
            ProcMemBackend,"""

content = content.replace("""        return [
            ProcMemBackend,""", candidate_linux_native)

candidate_windows = """    return [
        DMABackend,
        PymemBackend,"""

content = content.replace("""    return [
        PymemBackend,""", candidate_windows)

with open(filepath, 'w') as f:
    f.write(content)

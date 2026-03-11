import re

def sort_regions(regions):
    """
    Sorts regions based on heuristic priorities.
    Priority 1: .exe regions
    Priority 2: other likely game modules / heap (often no name or standard shared libs)
    Skip/Deprioritize: video driver memory, massive system blocks (NVIDIA, AMD, etc.)
    """
    pass

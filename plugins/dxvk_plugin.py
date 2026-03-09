"""
DXVK installation plugin.
"""

import logging

from src.files.dxvk_installer import install_dxvk
from src.plugins.manager import PluginBase, PluginMetadata


logger = logging.getLogger('napoleon.plugins.dxvk')


class DXVKPlugin(PluginBase):
    """Ensure DXVK is installed when the application loads plugins."""

    metadata = PluginMetadata(
        name="DXVK Installer",
        version="1.0.0",
        author="Napoleon Cheat Engine",
        description="Ensures DXVK wrapper DLLs are available for Vulkan translation.",
    )

    def on_load(self, engine) -> None:
        logger.info("[DXVK Plugin] Checking DXVK installation...")
        if install_dxvk():
            logger.info("[DXVK Plugin] DXVK is ready.")

    def on_unload(self) -> None:
        pass

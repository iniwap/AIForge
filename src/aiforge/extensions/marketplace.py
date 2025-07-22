from typing import Dict, List
from .extension_manager import ExtensionManager


# 预留插件市场接口
class PluginMarketplace:
    """插件市场接口"""

    def __init__(self, extension_manager: ExtensionManager):
        self.extension_manager = extension_manager

    def search_extensions(self, query: str) -> List[Dict]:
        """搜索可用扩展"""
        pass

    def install_extension(self, extension_id: str) -> bool:
        """安装扩展"""
        # 下载并安装扩展，然后注册到 extension_manager
        pass

    def update_extension(self, extension_id: str) -> bool:
        """更新扩展"""
        pass

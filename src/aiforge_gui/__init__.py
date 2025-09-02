# 包初始化和导出
"""AIForge GUI - webview 桌面应用"""

from .main import AIForgeGUIApp, main
from .core.engine_manager import EngineManager
from .core.webview_bridge import WebViewBridge
from .config.settings import GUISettings
from .config.connection_config import ConnectionConfig

__version__ = "0.0.15"
__all__ = [
    "AIForgeGUIApp",
    "main",
    "EngineManager",
    "WebViewBridge",
    "GUISettings",
    "ConnectionConfig",
]


# 便捷启动函数
def launch_gui(**config):
    """便捷启动 GUI 的函数"""
    app = AIForgeGUIApp(config)
    app.run()

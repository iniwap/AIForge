# 包初始化和导出
"""AIForge Web - FastAPI Web 应用"""

from .main import app, cleanup_on_exit
from .core.resource_monitor import ResourceMonitor
from .core.session_manager import SessionManager
from .api.routers import core, metadata, config, health
from .api.middleware.cors import setup_cors

__version__ = "0.0.15"
__all__ = [
    "app",
    "cleanup_on_exit",
    "ResourceMonitor",
    "SessionManager",
    "core",
    "metadata",
    "config",
    "health",
    "setup_cors",
    "launch_web",
]


# 便捷启动函数
def launch_web(host="127.0.0.1", port=8000, **config):
    """便捷启动 Web 服务器的函数"""
    try:
        import uvicorn

        uvicorn.run(app, host=host, port=port, **config)
    except ImportError:
        raise ImportError("Web 服务需要安装 fastapi 和 uvicorn")

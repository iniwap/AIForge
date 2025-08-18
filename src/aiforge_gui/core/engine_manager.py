# 引擎管理器（本地/远程）
import os
from typing import Dict, Any, Optional
from enum import Enum
from pathlib import Path


class ConnectionMode(Enum):
    LOCAL = "local"
    REMOTE = "remote"


class EngineManager:
    """引擎管理器 - 统一管理本地和远程引擎访问"""

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        # GUI模式下强制设置正确的工作目录
        self._setup_gui_workdir()

        self.mode = self._determine_mode()
        self.engine = None
        self._initialize_engine()

    def _setup_gui_workdir(self):
        """设置GUI模式下的工作目录"""
        # 强制设置GUI模式下的工作目录为用户主目录
        gui_workdir = Path.home() / "aiforge_work"
        gui_workdir.mkdir(exist_ok=True)

        # 确保配置中有正确的工作目录
        if "workdir" not in self.config:
            self.config["workdir"] = str(gui_workdir)

    def _determine_mode(self) -> ConnectionMode:
        """确定连接模式"""
        if self.config.get("remote_url"):
            return ConnectionMode.REMOTE
        return ConnectionMode.LOCAL

    def _initialize_engine(self):
        """初始化引擎"""
        if self.mode == ConnectionMode.LOCAL:
            self._initialize_local_engine()
        # 远程模式不需要初始化本地引擎

    def _initialize_local_engine(self):
        """初始化本地引擎"""
        try:
            from aiforge import AIForgeEngine

            # 构建引擎配置，包含GUI特定的工作目录
            engine_config = {"workdir": self.config.get("workdir")}  # 传递GUI设置的工作目录

            # API Key 处理
            api_key = (
                self.config.get("api_key")
                or os.environ.get("OPENROUTER_API_KEY")
                or os.environ.get("DEEPSEEK_API_KEY")
                or os.environ.get("AIFORGE_API_KEY")
            )

            if api_key:
                engine_config["api_key"] = api_key

            if self.config.get("provider"):
                engine_config["provider"] = self.config["provider"]

            if self.config.get("config_file"):
                engine_config["config_file"] = self.config["config_file"]

            # 传递其他GUI相关配置
            for key in ["max_rounds", "max_tokens", "locale"]:
                if key in self.config:
                    engine_config[key] = self.config[key]

            # 初始化引擎
            self.engine = AIForgeEngine(**engine_config)

        except Exception as e:
            print(f"❌ 本地引擎初始化失败: {e}")
            raise

    def is_local_mode(self) -> bool:
        """是否为本地模式"""
        return self.mode == ConnectionMode.LOCAL

    def is_remote_mode(self) -> bool:
        """是否为远程模式"""
        return self.mode == ConnectionMode.REMOTE

    def get_engine(self):
        """获取引擎实例（仅本地模式）"""
        if self.mode == ConnectionMode.LOCAL:
            return self.engine
        return None

    def get_remote_url(self) -> Optional[str]:
        """获取远程服务器地址（仅远程模式）"""
        if self.mode == ConnectionMode.REMOTE:
            return self.config.get("remote_url")
        return None

    def get_connection_info(self) -> Dict[str, Any]:
        """获取连接信息"""
        info = {
            "mode": self.mode.value,
            "local_engine_available": self.engine is not None,
            "remote_url": self.get_remote_url(),
            "features": self._get_supported_features(),
            "workdir": self.config.get("workdir"),
        }

        # 添加本地 API 服务器 URL 信息
        if self.mode == ConnectionMode.LOCAL:
            api_server = getattr(self, "_api_server", None)
            if api_server and hasattr(api_server, "port") and api_server.port:
                info["api_server_url"] = f"http://127.0.0.1:{api_server.port}"
            else:
                info["api_server_url"] = None
        else:
            info["api_server_url"] = None

        return info

    def _get_supported_features(self) -> Dict[str, bool]:
        """获取支持的功能"""
        if self.mode == ConnectionMode.LOCAL:
            return {
                "file_operations": True,
                "code_execution": True,
                "system_commands": True,
                "offline_mode": True,
            }
        else:
            return {
                "file_operations": False,
                "code_execution": False,
                "system_commands": False,
                "offline_mode": False,
            }

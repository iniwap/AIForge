import os
import json
import threading
from typing import Dict, Any, Optional
from enum import Enum
from .streaming_execution_manager import GUIStreamingExecutionManager
from aiforge import AIForgePathManager


class ConnectionMode(Enum):
    LOCAL = "local"
    REMOTE = "remote"


class EngineManager:
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}

        # 加载持久化配置
        self._load_persistent_config()

        self.mode = self._determine_mode()
        self.engine = None
        self._api_server = None  # 添加API服务器引用

        # 延迟初始化相关属性
        self._engine_initialized = False
        self._initialization_lock = threading.Lock()

    def _load_persistent_config(self):
        """加载持久化配置"""
        settings_file = AIForgePathManager.get_workdir() / ".aiforge" / "gui" / "settings.json"
        if settings_file.exists():
            try:
                with open(settings_file, "r", encoding="utf-8") as f:
                    persistent_config = json.load(f)
                    # 合并持久化配置到当前配置（不覆盖命令行参数）
                    for key, value in persistent_config.items():
                        if key not in self.config or key == "last_updated":
                            self.config[key] = value
            except Exception as e:
                print(f"Failed to load persistent config: {e}")

    def _ensure_engine_initialized(self):
        """确保引擎已初始化（延迟初始化）"""
        if not self._engine_initialized and self.mode == ConnectionMode.LOCAL:
            with self._initialization_lock:
                if not self._engine_initialized:  # 双重检查
                    # 检查是否有API密钥
                    api_key = self._get_current_api_key()
                    if not api_key:
                        raise RuntimeError("未配置API密钥，请先在界面中配置")

                    self._initialize_local_engine()
                    self._engine_initialized = True

    def _get_current_api_key(self) -> Optional[str]:
        """获取当前API密钥（优先级：配置 > 环境变量）"""
        return (
            self.config.get("api_key")
            or os.environ.get("OPENROUTER_API_KEY")
            or os.environ.get("DEEPSEEK_API_KEY")
            or os.environ.get("AIFORGE_API_KEY")
        )

    def has_valid_api_key(self) -> bool:
        """检查是否有有效的API密钥"""
        api_key = self._get_current_api_key()
        return bool(api_key and api_key.strip())

    def get_engine(self):
        """获取引擎实例（延迟初始化）"""
        if self.mode == ConnectionMode.LOCAL:
            self._ensure_engine_initialized()
            return self.engine
        return None

    def get_streaming_manager(self):
        """获取流式执行管理器（延迟初始化）"""
        if self.mode == ConnectionMode.LOCAL:
            self._ensure_engine_initialized()
            return self.streaming_manager
        return None

    def update_config(self, new_config: Dict[str, Any]):
        """更新配置并重新初始化引擎（如果需要）"""
        old_config = self.config.copy()
        self.config.update(new_config)

        # 如果引擎已初始化且关键配置发生变化，重新初始化
        if (
            self._engine_initialized
            and self.mode == ConnectionMode.LOCAL
            and self._config_requires_engine_restart(old_config, self.config)
        ):
            with self._initialization_lock:
                self._initialize_local_engine()

    def _config_requires_engine_restart(self, old_config: Dict, new_config: Dict) -> bool:
        """检查配置变化是否需要重启引擎"""
        restart_keys = ["api_key", "provider", "max_rounds", "max_tokens"]
        for key in restart_keys:
            if old_config.get(key) != new_config.get(key):
                return True
        return False

    def get_effective_config(self) -> Dict[str, Any]:
        """获取有效配置（包含环境变量）"""
        effective_config = self.config.copy()

        # API Key 优先级：配置 > 环境变量
        if not effective_config.get("api_key"):
            api_key = self._get_current_api_key()
            if api_key:
                effective_config["api_key"] = api_key

        return effective_config

    def get_connection_info(self) -> Dict[str, Any]:
        """获取连接信息"""
        info = {
            "mode": self.mode.value,
            "local_engine_available": self._engine_initialized and self.engine is not None,
            "remote_url": self.get_remote_url(),
            "features": self._get_supported_features(),
            "has_api_key": self.has_valid_api_key(),
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

    # 其他方法保持不变...
    def set_api_server_reference(self, api_server):
        """设置API服务器引用"""
        self._api_server = api_server

    def _determine_mode(self) -> ConnectionMode:
        """确定连接模式"""
        if self.config.get("remote_url"):
            return ConnectionMode.REMOTE
        return ConnectionMode.LOCAL

    def _initialize_local_engine(self):
        """初始化本地引擎"""
        try:
            from aiforge import AIForgeEngine

            # 构建引擎配置
            engine_config = {}

            # API Key 处理
            api_key = self._get_current_api_key()
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
            # 初始化 GUI 专用流式执行管理器
            self.streaming_manager = GUIStreamingExecutionManager(self.engine)

        except Exception as e:
            print(f"❌ 本地引擎初始化失败: {e}")
            raise

    def is_local_mode(self) -> bool:
        """是否为本地模式"""
        return self.mode == ConnectionMode.LOCAL

    def is_remote_mode(self) -> bool:
        """是否为远程模式"""
        return self.mode == ConnectionMode.REMOTE

    def get_shutdown_manager(self):
        """从引擎获取shutdown_manager"""
        if self.engine and hasattr(self.engine, "component_manager"):
            return self.engine.component_manager.components.get("shutdown_manager")
        return None

    def get_remote_url(self) -> Optional[str]:
        """获取远程服务器地址（仅远程模式）"""
        if self.mode == ConnectionMode.REMOTE:
            return self.config.get("remote_url")
        return None

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

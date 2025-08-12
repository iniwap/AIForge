from typing import Dict, Any, Optional
from pathlib import Path
from ...config.config import AIForgeConfig


class AIForgeConfigManager:
    """配置管理器 - 负责所有配置相关操作"""

    def __init__(self):
        self.config: Optional[AIForgeConfig] = None
        self._runtime_overrides: Dict[str, Any] = {}

    def _is_docker_environment(self) -> bool:
        """检测是否在 Docker 环境中运行"""
        import os

        return os.path.exists("/.dockerenv") or os.environ.get("DOCKER_CONTAINER") == "true"

    def initialize_config(
        self,
        config_file: str | None = None,
        api_key: str | None = None,
        provider: str = "openrouter",
        **kwargs,
    ) -> AIForgeConfig:
        """初始化配置"""
        # Docker 环境检测
        if self._is_docker_environment():
            config_file = config_file or "/app/config/aiforge.toml"

        # 情况3：传入配置文件，以此文件为准
        if config_file:
            self.config = AIForgeConfig(config_file)
        # 情况2：传入key+provider，以此创建
        elif api_key and provider != "openrouter":
            default_config = AIForgeConfig.get_builtin_default_config()
            if provider not in default_config.get("llm", {}):
                raise ValueError(f"Provider '{provider}' not found in default configuration")
            self.config = AIForgeConfig.from_api_key(api_key, provider, **kwargs)
        # 情况1：只传apikey，使用默认配置创建openrouter
        elif api_key:
            self.config = AIForgeConfig.from_api_key(api_key, "openrouter", **kwargs)
        else:
            raise ValueError(
                "Must provide either: 1) api_key only, 2) api_key + provider, or 3) config_file"
            )

        # 应用运行时覆盖
        if self._runtime_overrides:
            self.config.update(self._runtime_overrides)

        return self.config

    def get_searxng_config(self) -> Dict[str, Any]:
        """获取 SearXNG 配置"""
        import os

        remote_url = os.environ.get("SEARXNG_REMOTE_URL")
        if remote_url:
            return {
                "url": remote_url,
                "timeout": 10,
            }
        else:
            return {
                "url": "http://localhost:55510",
                "timeout": 10,
            }

    def is_searxng_available(self) -> bool:
        """检查 SearXNG 服务是否可用"""
        import os

        # 默认的SearXNG服务地址（由--searxng参数启动的服务）
        searxng_urls = [
            "http://localhost:55510",  # 本地Nginx代理地址
            "http://aiforge-searxng:8080",  # Docker内部服务地址
        ]

        # 添加远程服务支持
        remote_url = os.environ.get("SEARXNG_REMOTE_URL")
        if remote_url:
            searxng_urls.append(remote_url)

        for url in searxng_urls:
            try:
                import requests

                response = requests.get(f"{url}/search?q=test&format=json", timeout=5)
                if response.status_code == 200:
                    return True
            except Exception:
                continue

        return False

    def get_config(self) -> AIForgeConfig:
        """获取当前配置"""
        if not self.config:
            raise RuntimeError("Configuration not initialized")
        return self.config

    def update_runtime_config(self, updates: Dict[str, Any]):
        """更新运行时配置"""
        self._runtime_overrides.update(updates)
        if self.config:
            self.config.update(updates)

    def get_workdir(self) -> Path:
        """获取工作目录"""
        return self.config.get_workdir()

    def get_cache_config(self, cache_type: str) -> Dict[str, Any]:
        """获取缓存配置"""
        return self.config.get_cache_config(cache_type)

    def get_optimization_config(self) -> Dict[str, Any]:
        """获取优化配置"""
        return self.config.get_optimization_config()

    def get_security_config(self) -> Dict[str, Any]:
        """获取安全配置"""
        return self.config.get_security_config()

    def get_security_file_access_config(self) -> Dict[str, Any]:
        """获取安全-文件配置"""
        return self.config.get_security_file_access_config()

    def get_network_policy_level(self) -> str:
        """获取网络策略级别"""
        return self.config.get_security_network_config().get("policy", "filtered")

    def get_network_policy_config(
        self, context: str = "execution", task_type: str = None
    ) -> Dict[str, Any]:
        """获取特定上下文的网络策略配置"""
        return self.config.get_network_policy_config(context, task_type)

    def get_generated_code_network_config(self) -> Dict[str, Any]:
        """获取生成代码专用网络配置"""
        return self.get_network_policy_config(context="execution")

    def get_cache_validation_network_config(self, task_type: str = None) -> Dict[str, Any]:
        """获取缓存验证专用网络配置"""
        return self.get_network_policy_config(context="validation", task_type=task_type)

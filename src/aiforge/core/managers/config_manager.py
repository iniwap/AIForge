from typing import Dict, Any, Optional
from pathlib import Path
import os
from ..path_manager import AIForgePathManager
import tomlkit
from ...config.config import AIForgeConfig


class AIForgeConfigManager:
    """配置管理器 - 负责所有配置相关操作"""

    def __init__(self):
        self.config: Optional[AIForgeConfig] = None
        self._runtime_overrides: Dict[str, Any] = {}

    def _ensure_user_config_file(
        self, config_dir: Path, api_key: str = None, provider: str = "openrouter", **kwargs
    ) -> Path:
        """确保用户配置文件存在，如果不存在则从默认配置创建"""
        user_config_file = config_dir / "aiforge.toml"

        # 获取默认配置作为基础
        merged_config = AIForgeConfig.get_builtin_default_config()

        # 如果用户已有配置文件，先加载并合并
        if user_config_file.exists():
            try:
                with open(user_config_file, "r", encoding="utf-8") as f:
                    user_config = tomlkit.load(f)
                # 深度合并用户配置到默认配置
                self._deep_merge_config(merged_config, user_config)
            except Exception as e:
                print(f"加载用户配置文件失败，使用默认配置: {e}")

        # 如果提供了API key，更新相应的配置
        if api_key:
            if provider in merged_config.get("llm", {}):
                merged_config["llm"][provider]["api_key"] = api_key
                merged_config["default_llm_provider"] = provider

            # 应用其他参数
            core_params = [
                "max_rounds",
                "max_tokens",
                "max_optimization_attempts",
                "locale",
            ]
            for key, value in kwargs.items():
                if key in core_params:
                    merged_config[key] = value

        # 在非Docker环境下，清空敏感信息（API keys由环境变量提供）
        if not AIForgePathManager.is_docker_environment():
            for provider_config in merged_config.get("llm", {}).values():
                if isinstance(provider_config, dict):
                    provider_config["api_key"] = ""

        # 保存合并后的完整配置
        with open(user_config_file, "w", encoding="utf-8") as f:
            tomlkit.dump(merged_config, f)

        return user_config_file

    def _deep_merge_config(self, base_config: dict, user_config: dict):
        """深度合并配置"""
        for key, value in user_config.items():
            if (
                key in base_config
                and isinstance(base_config[key], dict)
                and isinstance(value, dict)
            ):
                self._deep_merge_config(base_config[key], value)
            else:
                base_config[key] = value

    def initialize_config(
        self,
        config_file: str | None = None,
        api_key: str | None = None,
        provider: str = "openrouter",
        **kwargs,
    ) -> AIForgeConfig:
        """初始化配置"""

        # 优先级1：如果直接传递了api_key，使用直接模式
        if api_key:
            if provider != "openrouter":
                default_config = AIForgeConfig.get_builtin_default_config()
                if provider not in default_config.get("llm", {}):
                    raise ValueError(f"Provider '{provider}' not found in default configuration")
                self.config = AIForgeConfig.from_api_key(api_key, provider, **kwargs)
            else:
                self.config = AIForgeConfig.from_api_key(api_key, "openrouter", **kwargs)

        # 优先级2：如果指定了配置文件，使用配置文件模式
        elif config_file and Path(config_file).exists():
            self.config = AIForgeConfig(config_file)

        # 优先级3：自动查找或创建配置文件
        else:
            config_dir = AIForgePathManager.get_config_dir()
            potential_config = config_dir / "aiforge.toml"

            if potential_config.exists():
                self.config = AIForgeConfig(str(potential_config))
            else:
                # 创建默认配置文件
                config_file = str(self._ensure_user_config_file(config_dir, **kwargs))
                self.config = AIForgeConfig(config_file)

        # 应用运行时覆盖
        if self._runtime_overrides:
            self.config.update(self._runtime_overrides)

        return self.config

    def get_searxng_config(self) -> Dict[str, Any]:
        """获取 SearXNG 配置"""
        remote_url = os.environ.get("SEARXNG_REMOTE_URL")
        if remote_url:
            return {"url": remote_url, "timeout": 10}

        # 检查是否在 Docker 环境中
        if AIForgePathManager.is_docker_environment():
            return {"url": "http://aiforge-searxng:8080", "timeout": 10}
        else:
            return {"url": "http://localhost:55510", "timeout": 10}

    def is_searxng_available(self) -> bool:
        """检查 SearXNG 服务是否可用"""
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

    def save_config_to_file(self, file_path: str = None):
        """保存当前配置到文件"""
        if not self.config:
            raise RuntimeError("Configuration not initialized")

        if not file_path:
            # 使用默认配置文件路径
            config_dir = AIForgePathManager.get_config_dir()
            file_path = str(config_dir / "aiforge.toml")

        self.config.save_to_file(file_path)

    def update_and_save_config(self, updates: Dict[str, Any], save_to_file: bool = True):
        """更新配置并可选择保存到文件"""
        self.update_runtime_config(updates)

        if save_to_file:
            self.save_config_to_file()

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

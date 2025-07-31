from typing import Dict, Any, Optional
from pathlib import Path
from ...config.config import AIForgeConfig


class AIForgeConfigManager:
    """配置管理器 - 负责所有配置相关操作"""

    def __init__(self):
        self.config: Optional[AIForgeConfig] = None
        self._runtime_overrides: Dict[str, Any] = {}

    def initialize_config(
        self,
        config_file: str | None = None,
        api_key: str | None = None,
        provider: str = "openrouter",
        **kwargs,
    ) -> AIForgeConfig:
        """初始化配置 - 整合原有的 _init_config 逻辑"""
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

    def get_llm_config(self, provider_name: str = None) -> Dict[str, Any]:
        """获取LLM配置"""
        return self.config.get_llm_config(provider_name)

    def validate_provider_config(self, provider: str) -> bool:
        """验证提供商配置"""
        llm_configs = self.config.get("llm", {})
        return provider in llm_configs and llm_configs[provider].get("enable", True)

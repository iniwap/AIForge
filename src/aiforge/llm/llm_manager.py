from typing import Dict, Optional, Any
from .llm_client import AIForgeLLMClient, AIForgeOllamaClient
from ..config.config import AIForgeConfig
from rich.console import Console


class AIForgeLLMManager:
    """LLM客户端管理器"""

    def __init__(self, config: AIForgeConfig, components: Dict[str, Any] = None):
        self._config = config
        self.console = Console()
        self.components = components or {}
        self._i18n_manager = self.components.get("i18n_manager")

        self.clients = {}  # 缓存已创建的客户端
        self.current_client = None
        self._init_default_client()

    @property
    def config(self) -> AIForgeConfig:
        """获取配置"""
        return self._config

    @config.setter
    def config(self, value: AIForgeConfig):
        """设置配置"""
        if not isinstance(value, AIForgeConfig):
            raise TypeError("config must be an instance of AIForgeConfig")
        self._config = value
        config_updated_message = self._i18n_manager.t("llm_manager.config_updated")
        self.console.print(f"[green]{config_updated_message}[/green]")
        # 重新初始化默认客户端
        self._init_default_client()

    def _init_default_client(self):
        """只初始化默认LLM客户端"""
        llm_configs = self._config.config.get("llm", {})
        default_provider_name = self._config.config.get("default_llm_provider")

        # 尝试创建指定的默认客户端
        if default_provider_name and default_provider_name in llm_configs:
            default_config = llm_configs[default_provider_name]
            client = self._create_client(default_provider_name, default_config)
            if client and client.is_usable():
                self.clients[default_provider_name] = client
                self.current_client = client
                return
            else:
                error_message = self._i18n_manager.t(
                    "llm_manager.default_client_unavailable", provider=default_provider_name
                )
                self.console.print(f"[red]{error_message}[/red]")
        else:
            config_missing_message = self._i18n_manager.t(
                "llm_manager.config_missing", provider=default_provider_name
            )
            self.console.print(f"[yellow]{config_missing_message}[/yellow]")

        no_client_message = self._i18n_manager.t("llm_manager.no_available_client")
        self.console.print(f"[red]{no_client_message}[/red]")

    def _create_client(self, name: str, config: Dict) -> Optional[AIForgeLLMClient]:
        """创建LLM客户端"""
        client_type = config.get("type", "openai")

        # 创建适配器进行配置验证
        from .adapters.adapter_factory import AdapterFactory

        adapter = AdapterFactory.create_adapter(config)

        if not adapter.validate_config():
            validation_failed_message = self._i18n_manager.t(
                "llm_manager.validation_failed", name=name, client_type=client_type
            )
            self.console.print(f"[red]{validation_failed_message}[/red]")
            return None

        # 根据客户端类型创建相应的客户端
        if client_type in [
            "openai",
            "deepseek",
            "grok",
            "gemini",
            "qwen",
            "claude",
            "cohere",
            "mistral",
        ]:
            return AIForgeLLMClient(
                name=name,
                api_key=config.get("api_key", ""),
                base_url=config.get("base_url"),
                model=config.get("model"),
                timeout=config.get("timeout", 60),
                max_tokens=config.get("max_tokens", 8192),
                client_type=client_type,
                components=self.components,
            )
        elif client_type == "ollama":
            return AIForgeOllamaClient(
                name=name,
                base_url=config.get("base_url", "http://localhost:11434"),
                model=config.get("model"),
                timeout=config.get("timeout", 60),
                max_tokens=config.get("max_tokens", 8192),
                components=self.components,
            )
        else:
            unsupported_message = self._i18n_manager.t(
                "llm_manager.unsupported_type", client_type=client_type
            )
            self.console.print(f"[yellow]{unsupported_message}[/yellow]")
            return None

    def get_client(self, name: str | None = None) -> Optional[AIForgeLLMClient]:
        """获取客户端"""
        # 如果没有指定名称，返回当前客户端
        if not name:
            return self.current_client

        # 如果客户端已经创建，直接返回
        if name in self.clients:
            return self.clients[name]

        # 懒加载：按需创建客户端
        llm_configs = self._config.config.get("llm", {})
        if name in llm_configs:
            llm_config = llm_configs[name]
            try:
                client = self._create_client(name, llm_config)
                if client and client.is_usable():
                    self.clients[name] = client
                    lazy_load_message = self._i18n_manager.t(
                        "llm_manager.lazy_load_create", name=name
                    )
                    self.console.print(f"[green]{lazy_load_message}[/green]")
                    return client
                else:
                    unavailable_message = self._i18n_manager.t(
                        "llm_manager.client_unavailable", name=name
                    )
                    self.console.print(f"[yellow]{unavailable_message}[/yellow]")
            except Exception as e:
                create_failed_message = self._i18n_manager.t(
                    "llm_manager.create_failed", name=name, error=str(e)
                )
                self.console.print(f"[red]{create_failed_message}[/red]")

        return None

    def switch_client(self, name: str) -> bool:
        """切换当前客户端"""
        client = self.get_client(name)
        if client:
            self.current_client = client
            switch_success_message = self._i18n_manager.t("llm_manager.switch_success", name=name)
            self.console.print(f"[green]{switch_success_message}[/green]")
            return True
        else:
            switch_failed_message = self._i18n_manager.t("llm_manager.switch_failed", name=name)
            self.console.print(f"[red]{switch_failed_message}[/red]")
            return False

    def list_available_providers(self) -> Dict[str, str]:
        """列出所有配置的提供商（不创建客户端）"""
        llm_configs = self._config.config.get("llm", {})
        providers = {}
        for name, config in llm_configs.items():
            providers[name] = config.get("model", "unknown")
        return providers

    def list_active_clients(self) -> Dict[str, str]:
        """列出已创建的客户端"""
        return {name: client.model for name, client in self.clients.items()}

    def preload_clients(self, client_names: list | None = None):
        """预加载指定的客户端"""
        if client_names is None:
            # 预加载所有可用的客户端
            llm_configs = self._config.config.get("llm", {})
            client_names = [name for name, config in llm_configs.items()]

        for name in client_names:
            if name not in self.clients:
                self.get_client(name)  # 触发懒加载

    def cleanup_unused_clients(self):
        """清理未使用的客户端（保留当前客户端）"""
        if self.current_client:
            current_name = self.current_client.name
            self.clients = {current_name: self.current_client}
            cleanup_message = self._i18n_manager.t(
                "llm_manager.cleanup_unused", current_name=current_name
            )
            self.console.print(f"[green]{cleanup_message}[/green]")

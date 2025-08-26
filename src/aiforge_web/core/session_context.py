import time
from typing import Dict, Any, Optional
from dataclasses import dataclass, field


@dataclass
class SessionConfig:
    """会话级配置"""

    api_key: Optional[str] = None
    provider: str = "openrouter"
    locale: str = "zh"
    max_rounds: Optional[int] = None
    max_tokens: Optional[int] = None

    def to_aiforge_config_dict(self) -> Dict[str, Any]:
        config_dict = {}
        if self.api_key:
            config_dict["api_key"] = self.api_key
        if self.provider:
            config_dict["provider"] = self.provider
        if self.locale:
            config_dict["locale"] = self.locale
        if self.max_rounds:
            config_dict["max_rounds"] = self.max_rounds
        if self.max_tokens:
            config_dict["max_tokens"] = self.max_tokens
        return config_dict


@dataclass
class SessionContext:
    """会话上下文"""

    session_id: str
    user_id: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    last_activity: float = field(default_factory=time.time)
    language: str = "zh"
    components: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    config: SessionConfig = field(default_factory=SessionConfig)  # 添加配置字段

    def update_config(self, **config_updates):
        """更新会话配置"""
        for key, value in config_updates.items():
            if hasattr(self.config, key) and value is not None:
                setattr(self.config, key, value)

    def update_activity(self):
        """更新最后活动时间"""
        self.last_activity = time.time()

    def is_expired(self, timeout: int = 7200) -> bool:
        """检查会话是否过期（默认2小时）"""
        return time.time() - self.last_activity > timeout

    def get_component(self, name: str) -> Optional[Any]:
        """获取组件实例"""
        return self.components.get(name)

    def set_component(self, name: str, component: Any):
        """设置组件实例"""
        self.components[name] = component

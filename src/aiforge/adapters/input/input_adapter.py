from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from enum import Enum


class InputSource(Enum):
    """输入源类型"""

    CLI = "cli"
    GUI = "gui"
    WEB = "web"
    MOBILE = "mobile"
    API = "api"
    VOICE = "voice"


class InputContext:
    """输入上下文信息"""

    def __init__(
        self,
        source: InputSource,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        device_info: Optional[Dict[str, Any]] = None,
        preferences: Optional[Dict[str, Any]] = None,
    ):
        self.source = source
        self.user_id = user_id
        self.session_id = session_id
        self.device_info = device_info or {}
        self.preferences = preferences or {}


class StandardizedInput:
    """标准化输入结构"""

    def __init__(
        self,
        instruction: str,
        context: InputContext,
        metadata: Optional[Dict[str, Any]] = None,
        attachments: Optional[Dict[str, Any]] = None,
    ):
        self.instruction = instruction
        self.context = context
        self.metadata = metadata or {}
        self.attachments = attachments or {}


class InputAdapter(ABC):
    """输入适配器基类"""

    @abstractmethod
    def can_handle(self, raw_input: Any, source: InputSource) -> bool:
        """检查是否能处理特定类型的输入"""
        pass

    @abstractmethod
    def adapt(self, raw_input: Any, context: InputContext) -> StandardizedInput:
        """将原始输入适配为标准化输入"""
        pass

    @abstractmethod
    def validate(self, standardized_input: StandardizedInput) -> bool:
        """验证标准化输入的有效性"""
        pass

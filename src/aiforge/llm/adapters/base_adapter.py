from abc import ABC, abstractmethod
from typing import Dict, Any, Tuple


class LLMProviderAdapter(ABC):
    """LLM提供商适配器基类"""

    def __init__(self, client_config: Dict[str, Any]):
        self.client_config = client_config
        self.client_type = client_config.get("type", "openai")

    @abstractmethod
    def prepare_request(
        self, messages: list, payload: Dict[str, Any]
    ) -> Tuple[Dict[str, Any], Dict[str, str]]:
        """准备请求数据和头部"""
        pass

    @abstractmethod
    def parse_response(self, response_data: Dict[str, Any]) -> str:
        """解析响应数据"""
        pass

    @abstractmethod
    def get_endpoint(self, base_url: str) -> str:
        """获取API端点"""
        pass

    @abstractmethod
    def handle_error(self, status_code: int, response_data: Dict[str, Any]) -> Tuple[bool, str]:
        """处理错误响应，返回(是否可重试, 错误信息)"""
        pass

    def validate_config(self) -> bool:
        """验证配置是否完整"""
        return True

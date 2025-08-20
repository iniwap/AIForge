from typing import Dict, Any, Tuple
from .base_adapter import LLMProviderAdapter


class OpenAIAdapter(LLMProviderAdapter):
    """OpenAI兼容提供商适配器"""

    def prepare_request(
        self, messages: list, payload: Dict[str, Any]
    ) -> Tuple[Dict[str, Any], Dict[str, str]]:
        headers = {
            "Authorization": f"Bearer {self.client_config['api_key']}",
            "Content-Type": "application/json",
        }
        return payload, headers

    def parse_response(self, response_data: Dict[str, Any]) -> str:
        return response_data["choices"][0]["message"]["content"]

    def get_endpoint(self, base_url: str) -> str:
        return f"{base_url}/chat/completions"

    def handle_error(self, status_code: int, response_data: Dict[str, Any]) -> Tuple[bool, str]:
        if status_code >= 500:
            return True, f"服务器错误: {status_code}"
        elif status_code == 429:
            return True, "请求频率限制"
        else:
            return False, f"客户端错误: {status_code}"

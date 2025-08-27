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
        if status_code == 429:
            # 从 OpenRouter 响应中提取实际错误消息
            error_msg = "请求频率限制"
            if "error" in response_data and "metadata" in response_data["error"]:
                raw_msg = response_data["error"]["metadata"].get("raw", "")
                if raw_msg:
                    error_msg = raw_msg

            return True, error_msg  # 返回表示允许重试的元组

        # 处理其他错误情况并始终返回元组
        return False, f"HTTP {status_code} error"

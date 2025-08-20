from typing import Dict, Any, Tuple
from .base_adapter import LLMProviderAdapter


class GrokAdapter(LLMProviderAdapter):
    """X.AI Grok适配器"""

    def prepare_request(
        self, messages: list, payload: Dict[str, Any]
    ) -> Tuple[Dict[str, Any], Dict[str, str]]:
        headers = {
            "Authorization": f"Bearer {self.client_config['api_key']}",
            "Content-Type": "application/json",
        }

        # Grok可能需要特殊的模型名称格式
        grok_payload = payload.copy()
        model = self.client_config.get("model", "grok-beta")
        if not model.startswith("xai/"):
            model = f"xai/{model}"
        grok_payload["model"] = model

        return grok_payload, headers

    def parse_response(self, response_data: Dict[str, Any]) -> str:
        return response_data["choices"][0]["message"]["content"]

    def get_endpoint(self, base_url: str) -> str:
        return f"{base_url}/chat/completions"

    def handle_error(self, status_code: int, response_data: Dict[str, Any]) -> Tuple[bool, str]:
        if status_code >= 500:
            return True, f"Grok服务器错误: {status_code}"
        elif status_code == 429:
            # Grok的频率限制可能更严格
            return True, "Grok API频率限制，建议延长重试间隔"
        else:
            return False, f"Grok客户端错误: {status_code}"

    def validate_config(self) -> bool:
        # Grok可能需要特定格式的API密钥验证
        api_key = self.client_config.get("api_key", "")
        return bool(api_key and len(api_key) > 10)

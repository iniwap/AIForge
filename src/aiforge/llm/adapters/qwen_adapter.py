from typing import Dict, Any, Tuple
from .base_adapter import LLMProviderAdapter


class QwenAdapter(LLMProviderAdapter):
    """阿里云通义千问适配器"""

    def prepare_request(
        self, messages: list, payload: Dict[str, Any]
    ) -> Tuple[Dict[str, Any], Dict[str, str]]:
        # 修正模型名称格式
        model = self.client_config.get("model", "qwen-plus")
        if model.startswith("openai/"):
            model = model.replace("openai/", "")

        qwen_payload = payload.copy()
        qwen_payload["model"] = model

        headers = {
            "Authorization": f"Bearer {self.client_config['api_key']}",
            "Content-Type": "application/json",
            "X-DashScope-SSE": "disable",  # 阿里云特殊头部
        }

        return qwen_payload, headers

    def parse_response(self, response_data: Dict[str, Any]) -> str:
        return response_data["choices"][0]["message"]["content"]

    def get_endpoint(self, base_url: str) -> str:
        return f"{base_url}/chat/completions"

    def handle_error(self, status_code: int, response_data: Dict[str, Any]) -> Tuple[bool, str]:
        if status_code >= 500:
            return True, f"通义千问服务器错误: {status_code}"
        elif status_code == 429:
            return True, "通义千问请求频率限制"
        else:
            error_code = response_data.get("error", {}).get("code", "unknown")
            error_msg = response_data.get("error", {}).get("message", f"状态码: {status_code}")
            return False, f"通义千问错误[{error_code}]: {error_msg}"

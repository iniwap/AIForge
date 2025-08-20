from typing import Dict, Any, Tuple
from .base_adapter import LLMProviderAdapter


class GeminiAdapter(LLMProviderAdapter):
    """Google Gemini适配器"""

    def prepare_request(
        self, messages: list, payload: Dict[str, Any]
    ) -> Tuple[Dict[str, Any], Dict[str, str]]:
        # 转换消息格式为Gemini格式
        gemini_messages = []
        for msg in messages:
            if msg["role"] == "system":
                continue  # Gemini在请求中不支持system消息

            role = "model" if msg["role"] == "assistant" else "user"
            gemini_messages.append({"role": role, "parts": [{"text": msg["content"]}]})

        gemini_payload = {
            "contents": gemini_messages,
            "generationConfig": {
                "temperature": payload.get("temperature", 0.7),
                "maxOutputTokens": payload.get("max_tokens", 8192),
            },
        }

        headers = {
            "Authorization": f"Bearer {self.client_config['api_key']}",
            "Content-Type": "application/json",
        }

        return gemini_payload, headers

    def parse_response(self, response_data: Dict[str, Any]) -> str:
        return response_data["candidates"][0]["content"]["parts"][0]["text"]

    def get_endpoint(self, base_url: str) -> str:
        model = self.client_config.get("model", "gemini-pro")
        return f"{base_url}/models/{model}:generateContent"

    def handle_error(self, status_code: int, response_data: Dict[str, Any]) -> Tuple[bool, str]:
        if status_code >= 500:
            return True, f"Gemini服务器错误: {status_code}"
        elif status_code == 429:
            return True, "Gemini API配额限制"
        else:
            error_msg = response_data.get("error", {}).get("message", f"未知错误: {status_code}")
            return False, f"Gemini错误: {error_msg}"

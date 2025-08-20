from typing import Dict, Any, Tuple
from .base_adapter import LLMProviderAdapter


class ClaudeAdapter(LLMProviderAdapter):
    """Anthropic Claude适配器"""

    def prepare_request(
        self, messages: list, payload: Dict[str, Any]
    ) -> Tuple[Dict[str, Any], Dict[str, str]]:
        # Claude使用不同的消息格式
        claude_messages = []
        system_prompt = None

        for msg in messages:
            if msg["role"] == "system":
                system_prompt = msg["content"]
            else:
                claude_messages.append({"role": msg["role"], "content": msg["content"]})

        claude_payload = {
            "model": self.client_config.get("model", "claude-3-sonnet-20240229"),
            "messages": claude_messages,
            "max_tokens": payload.get("max_tokens", 4096),
            "temperature": payload.get("temperature", 0.7),
        }

        if system_prompt:
            claude_payload["system"] = system_prompt

        headers = {
            "Authorization": f"Bearer {self.client_config['api_key']}",
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01",
        }

        return claude_payload, headers

    def parse_response(self, response_data: Dict[str, Any]) -> str:
        return response_data["content"][0]["text"]

    def get_endpoint(self, base_url: str) -> str:
        return f"{base_url}/messages"

    def handle_error(self, status_code: int, response_data: Dict[str, Any]) -> Tuple[bool, str]:
        if status_code >= 500:
            return True, f"Claude服务器错误: {status_code}"
        elif status_code == 429:
            return True, "Claude API速率限制"
        else:
            error_msg = response_data.get("error", {}).get("message", f"状态码: {status_code}")
            return False, f"Claude错误: {error_msg}"

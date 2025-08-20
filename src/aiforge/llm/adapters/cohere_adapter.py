from typing import Dict, Any, Tuple
from .base_adapter import LLMProviderAdapter


class CohereAdapter(LLMProviderAdapter):
    """Cohere适配器"""

    def prepare_request(
        self, messages: list, payload: Dict[str, Any]
    ) -> Tuple[Dict[str, Any], Dict[str, str]]:
        # Cohere使用chat格式
        chat_history = []
        message = ""

        for msg in messages:
            if msg["role"] == "system":
                continue  # 系统消息可以作为preamble
            elif msg["role"] == "user":
                message = msg["content"]
            elif msg["role"] == "assistant":
                chat_history.append({"role": "CHATBOT", "message": msg["content"]})

        cohere_payload = {
            "model": self.client_config.get("model", "command-r-plus"),
            "message": message,
            "chat_history": chat_history,
            "temperature": payload.get("temperature", 0.7),
            "max_tokens": payload.get("max_tokens", 4096),
        }

        headers = {
            "Authorization": f"Bearer {self.client_config['api_key']}",
            "Content-Type": "application/json",
        }

        return cohere_payload, headers

    def parse_response(self, response_data: Dict[str, Any]) -> str:
        return response_data["text"]

    def get_endpoint(self, base_url: str) -> str:
        return f"{base_url}/chat"

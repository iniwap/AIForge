from typing import Dict, Any, Tuple
from .base_adapter import LLMProviderAdapter


class MistralAdapter(LLMProviderAdapter):
    """Mistral AI适配器"""

    def prepare_request(
        self, messages: list, payload: Dict[str, Any]
    ) -> Tuple[Dict[str, Any], Dict[str, str]]:
        # Mistral基本兼容OpenAI格式，但有细微差异
        headers = {
            "Authorization": f"Bearer {self.client_config['api_key']}",
            "Content-Type": "application/json",
        }

        mistral_payload = payload.copy()
        # 确保模型名称正确
        model = self.client_config.get("model", "mistral-large-latest")
        mistral_payload["model"] = model

        return mistral_payload, headers

    def parse_response(self, response_data: Dict[str, Any]) -> str:
        return response_data["choices"][0]["message"]["content"]

    def get_endpoint(self, base_url: str) -> str:
        return f"{base_url}/chat/completions"

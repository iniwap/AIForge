from typing import Dict, Any

from .openai_adapter import OpenAIAdapter
from .gemini_adapter import GeminiAdapter
from .qwen_adapter import QwenAdapter
from .grok_adapter import GrokAdapter
from .claude_adapter import ClaudeAdapter
from .cohere_adapter import CohereAdapter
from .mistral_adapter import MistralAdapter
from .base_adapter import LLMProviderAdapter


class AdapterFactory:
    """适配器工厂"""

    ADAPTERS = {
        "openai": OpenAIAdapter,
        "deepseek": OpenAIAdapter,
        "gemini": GeminiAdapter,
        "qwen": QwenAdapter,
        "grok": GrokAdapter,
        "claude": ClaudeAdapter,
        "cohere": CohereAdapter,
        "mistral": MistralAdapter,
    }

    @classmethod
    def create_adapter(cls, client_config: Dict[str, Any]) -> LLMProviderAdapter:
        client_type = client_config.get("type", "openai")
        adapter_class = cls.ADAPTERS.get(client_type, OpenAIAdapter)
        return adapter_class(client_config)

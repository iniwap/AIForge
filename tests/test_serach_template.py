import pytest
import os

from src.aiforge.templates.search_template import (
    search_web,
    get_free_form_ai_search_instruction,
    get_template_guided_search_instruction,
)
from src.aiforge.core import AIForgeEngine


@pytest.mark.skipif(
    "OPENROUTER_API_KEY" not in os.environ, reason="需要设置 OPENROUTER_API_KEY 环境变量"
)
def test_search():
    forge = AIForgeEngine(api_key=os.environ["OPENROUTER_API_KEY"])
    result, _ = forge.generate_and_execute(
        get_template_guided_search_instruction("获取5条日本海啸的最新新闻", 10)
    )
    print("test_search result:", result)
    assert result is not None


def test_search_web():
    print(search_web("CHATGPT 5 RELEASE"))

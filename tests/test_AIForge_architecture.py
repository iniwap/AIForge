import os
import pytest
from aiforge import AIForgeEngine


class TestAIForgeArchitecture:
    """AIForge 架构全面测试套件"""

    @pytest.fixture(scope="class")
    def forge(self):
        """测试用的 AIForge 实例"""
        api_key = os.environ.get("OPENROUTER_API_KEY")
        if not api_key:
            pytest.skip("需要设置 OPENROUTER_API_KEY 环境变量")
        return AIForgeEngine(api_key=api_key)

    @pytest.fixture(scope="class")
    def forge_deepseek(self):
        """DeepSeek 提供商测试实例"""
        api_key = os.environ.get("DEEPSEEK_API_KEY")
        if not api_key:
            pytest.skip("需要设置 DEEPSEEK_API_KEY 环境变量")
        return AIForgeEngine(api_key=api_key, provider="deepseek")

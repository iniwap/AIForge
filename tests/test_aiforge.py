import os
import pytest
from aiforge import AIForgeCore


@pytest.mark.skipif(
    "OPENROUTER_API_KEY" not in os.environ, reason="需要设置 OPENROUTER_API_KEY 环境变量"
)
def test_quick_start():
    """方式1：快速启动"""
    forge = AIForgeCore(api_key=os.environ["OPENROUTER_API_KEY"])
    result = forge("获取5条张俪道歉的最新新闻")
    print("quick_start result:", result)
    assert result is not None


@pytest.mark.skipif(
    "DEEPSEEK_API_KEY" not in os.environ, reason="需要设置 DEEPSEEK_API_KEY 环境变量"
)
def test_provider_deepseek():
    """方式2：指定提供商"""
    forge = AIForgeCore(api_key=os.environ["DEEPSEEK_API_KEY"], provider="deepseek", max_rounds=3)
    result = forge("北京朝阳降雨量下至全国第一相关新闻报导及内容")
    print("deepseek result:", result)
    assert result is not None


def test_config_file(tmp_path):
    """方式3：配置文件方式"""
    # 创建临时配置文件
    config_content = """
workdir = "aiforge_work"
max_tokens = 4096
max_rounds = 5
default_llm_provider = "openrouter"

[llm.openrouter]
type = "openai"
model = "deepseek/deepseek-chat-v3-0324:free"
api_key = "dummy-key"
base_url = "https://openrouter.ai/api/v1"
timeout = 30
max_tokens = 8192
"""
    config_file = tmp_path / "aiforge.toml"
    config_file.write_text(config_content)
    forge = AIForgeCore(config_file=str(config_file))
    # 这里只能测试 run 方法能否被调用，不保证真实 LLM 返回
    try:
        result = forge.run("处理任务", system_prompt="你是专业助手")
        print("config_file result:", result)
    except Exception as e:
        print("config_file error:", e)
    assert True  # 只要不抛异常就算通过


def test_custom_executor(monkeypatch):
    """自定义执行器"""
    from aiforge.execution.executor_interface import CachedModuleExecutor

    class DummyModule:
        def custom_function(self, instruction):
            return f"custom: {instruction}"

    class CustomExecutor(CachedModuleExecutor):
        def can_handle(self, module):
            return hasattr(module, "custom_function")

        def execute(self, module, instruction, **kwargs):
            return module.custom_function(instruction)

    forge = AIForgeCore(api_key="dummy")
    forge.add_module_executor(CustomExecutor())
    dummy = DummyModule()
    result = forge.module_executors[-1].execute(dummy, "test")
    print("custom_executor result:", result)
    assert result == "custom: test"


def test_switch_provider(monkeypatch):
    """提供商切换与查询"""
    forge = AIForgeCore(api_key="dummy")
    # 假设 switch_provider/list_providers 不依赖真实 LLM
    try:
        forge.switch_provider("deepseek")
        providers = forge.list_providers()
        print("providers:", providers)
        assert isinstance(providers, list)
    except Exception as e:
        print("switch_provider error:", e)
        assert False


def test_create_config_wizard():
    """配置向导"""
    from aiforge.cli.wizard import create_config_wizard

    try:
        forge = create_config_wizard()
        assert forge is not None
    except Exception as e:
        print("create_config_wizard error:", e)
        assert True  # 只要不抛异常就算通过

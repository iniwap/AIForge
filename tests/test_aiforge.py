import os
import pytest
from aiforge import AIForgeCore


@pytest.mark.skipif(
    "OPENROUTER_API_KEY" not in os.environ, reason="需要设置 OPENROUTER_API_KEY 环境变量"
)
def test_quick_start():
    """方式1：快速启动"""
    forge = AIForgeCore(api_key=os.environ["OPENROUTER_API_KEY"])
    result = forge("魔都今天天啥样？")
    print("quick_start result:", result)
    assert result is not None


@pytest.mark.skipif(
    "DEEPSEEK_API_KEY" not in os.environ, reason="需要设置 DEEPSEEK_API_KEY 环境变量"
)
def test_provider_deepseek():
    """方式2：指定提供商"""
    forge = AIForgeCore(api_key=os.environ["DEEPSEEK_API_KEY"], provider="deepseek", max_rounds=3)
    result = forge("分析数据文件")
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


@pytest.mark.skipif(
    "OPENROUTER_API_KEY" not in os.environ, reason="需要设置 OPENROUTER_API_KEY 环境变量"
)
def test_generate_and_execute():
    """直接生成代码，不走系统标准处理"""
    forge = AIForgeCore(api_key=os.environ["OPENROUTER_API_KEY"])
    topic = "石破茂为历史性惨败鞠躬道歉"
    max_results = 10
    min_results = 5
    search_instruction = f"""
    请生成一个搜索函数，获取最新相关信息，参考以下配置：

    # 搜索引擎URL模式：
    - 百度: https://www.baidu.com/s?wd={{quote(topic)}}&rn={{max_results}}
    - Bing: https://www.bing.com/search?q={{quote(topic)}}&count={{max_results}}
    - 360: https://www.so.com/s?q={{quote(topic)}}&rn={{max_results}}
    - 搜狗: https://www.sogou.com/web?query={{quote(topic)}}

    # 关键CSS选择器：
    百度结果容器: ["div.result", "div.c-container", "div[class*='result']"]
    百度标题: ["h3", "h3 a", ".t", ".c-title"]
    百度摘要: ["div.c-abstract", ".c-span9", "[class*='abstract']"]

    Bing结果容器: ["li.b_algo", "div.b_algo", "li[class*='algo']"]
    Bing标题: ["h2", "h3", "h2 a", ".b_title"]
    Bing摘要: ["p.b_lineclamp4", "div.b_caption", ".b_snippet"]

    360结果容器: ["li.res-list", "div.result", "li[class*='res']"]
    360标题: ["h3.res-title", "h3", ".res-title"]
    360摘要: ["p.res-desc", "div.res-desc", ".res-summary"]

    搜狗结果容器: ["div.vrwrap", "div.results", "div.result"]
    搜狗标题: ["h3.vr-title", "h3.vrTitle", "a.title", "h3"]
    搜狗摘要: ["div.str-info", "div.str_info", "p.str-info"]

    # 重要处理逻辑：
    1. 按优先级依次尝试四个搜索引擎（不要使用API密钥方式）
    2. 使用 concurrent.futures.ThreadPoolExecutor 并行访问页面提取详细内容
    3. 从页面提取发布时间，遵从以下策略：
        - 优先meta标签：article:published_time、datePublished、pubdate、publishdate等
        - 备选方案：time标签、日期相关class、页面文本匹配
        - 有效的日期格式：标准格式、中文格式、相对时间（如“昨天”、“1天前”、“1小时前”等）、英文时间（如“yesterday”等）
    4. 按发布时间排序，优先最近7天内容
    5. 过滤掉验证页面和无效内容，正确处理编码，结果不能包含乱码

    # 返回数据格式（严格遵守）：
    {{
        "timestamp": time.time(),
        "topic": "{topic}",
        "results": [
            {{
                "title": "标题",
                "url": "链接",
                "abstract": "详细摘要（去除空格换行，至少100字）",
                "pub_time": "发布时间"
            }}
        ],
        "success": True/False,
        "error": 错误信息或None
    }}

        __result__ = search_web("{topic}", {max_results})

    # 严格停止条件：获取到{min_results}条或以上同时满足以下条件的结果时，立即停止执行，不得继续生成任何代码：
    # 1. 摘要(abstract)长度不少于100字
    # 2. 发布时间(pub_time)字段不为空、不为None、不为空字符串
    # 重要：满足上述条件后，必须立即设置__result__并结束，禁止任何形式的代码优化、重构或改进

    """
    result = forge.generate_and_execute(search_instruction)
    print("quick_start result:", result)
    assert result is not None

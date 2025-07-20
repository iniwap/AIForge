import os
import pytest

from aiforge import AIForgeCore


@pytest.mark.skipif(
    "OPENROUTER_API_KEY" not in os.environ, reason="需要设置 OPENROUTER_API_KEY 环境变量"
)
def test_direct_register():
    forge = AIForgeCore(api_key=os.environ["OPENROUTER_API_KEY"])

    # 执行任务
    result = forge.run("杭州今天的天气怎么样")

    # 为不同UI适配结果
    web_result = forge.adapt_result_for_ui(result, "web_table")
    mobile_result = forge.adapt_result_for_ui(result, "mobile_list")
    terminal_result = forge.adapt_result_for_ui(result, "terminal_text")

    print(web_result, mobile_result, terminal_result)

    # 查看适配统计
    stats = forge.get_ui_adaptation_stats()
    print(f"适配统计: {stats}")

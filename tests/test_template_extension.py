import os
import pytest

from aiforge import AIForgeEngine
from aiforge.extensions.template_extension import FinancialTemplateExtension


@pytest.mark.skipif(
    "OPENROUTER_API_KEY" not in os.environ, reason="需要设置 OPENROUTER_API_KEY 环境变量"
)
def test_direct_register():
    forge = AIForgeEngine(api_key=os.environ["OPENROUTER_API_KEY"])
    # 方式1: 直接注册扩展类
    financial_extension = FinancialTemplateExtension(
        "financial", {"priority": 100, "data_source": "yahoo_finance"}
    )
    forge.register_extension(
        {
            "type": "template",
            "class": FinancialTemplateExtension,
            "domain": "financial",
            "priority": 100,
        }
    )

    result = forge("分析AAPL股票的技术指标")
    print("quick_start result:", result)
    assert result is not None

    """
    # 方式2: 从配置文件加载
    forge.register_extension({"type": "template", "config_file": "extensions.toml"})

    # 方式3: 直接注册领域模板
    forge.register_extension(
        {
            "type": "template",
            "domain_templates": {
                "scientific": {
                    "keywords": ["科学计算", "数值分析"],
                    "templates": {
                        "numerical_analysis": {
                            "pattern": r"数值.*分析",
                            "parameters": ["method", "data"],
                            "template_code": "# 数值分析代码模板",
                        }
                    },
                }
            },
        }
    )
    """

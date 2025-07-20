from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import re


class DomainTemplateExtension(ABC):
    """领域模板扩展基类"""

    def __init__(self, domain_name: str, config: Dict[str, Any]):
        self.domain_name = domain_name
        self.config = config
        self.templates = {}
        self.load_templates()

    @abstractmethod
    def can_handle(self, standardized_instruction: Dict[str, Any]) -> bool:
        """判断是否能处理该标准化指令"""
        pass

    @abstractmethod
    def get_template_match(self, standardized_instruction: Dict[str, Any]) -> Optional[Dict]:
        """获取匹配的模板信息"""
        pass

    @abstractmethod
    def load_templates(self):
        """加载领域特定模板"""
        pass

    def get_priority(self) -> int:
        """获取扩展优先级，数值越高优先级越高"""
        return self.config.get("priority", 0)


class FinancialTemplateExtension(DomainTemplateExtension):
    """金融领域模板扩展示例"""

    def load_templates(self):
        self.templates = {
            "stock_analysis": {
                "pattern": r"股票.*分析|stock.*analysis",
                "keywords": ["股票", "stock", "分析", "analysis", "技术指标", "AAPL"],
                "template_code": """
    import yfinance as yf
    import pandas as pd

    def analyze_stock(symbol, period="1mo"):
        stock = yf.Ticker(symbol)
        data = stock.history(period=period)

        # 基础分析
        current_price = data['Close'][-1]
        avg_price = data['Close'].mean()
        volatility = data['Close'].std()

        __result__ = {
            "symbol": symbol,
            "current_price": current_price,
            "average_price": avg_price,
            "volatility": volatility,
            "trend": "上涨" if current_price > avg_price else "下跌"
        }

    # 执行分析
    analyze_stock("{{ symbol }}")
    """,
                "parameters": ["symbol", "period"],
                "cache_key_template": "financial_stock_analysis_{symbol}",
            }
        }

    def can_handle(self, standardized_instruction: Dict[str, Any]) -> bool:
        # task_type = standardized_instruction.get("task_type", "")
        target = standardized_instruction.get("target", "")

        # 检查是否为金融相关任务
        financial_keywords = ["股票", "stock", "金融", "financial", "投资", "investment"]
        return any(keyword in target.lower() for keyword in financial_keywords)

    def get_template_match(self, standardized_instruction: Dict[str, Any]) -> Optional[Dict]:
        target = standardized_instruction.get("target", "")

        for template_name, template_config in self.templates.items():
            if re.search(template_config["pattern"], target, re.IGNORECASE):
                return {
                    "template_name": template_name,
                    "template_config": template_config,
                    "domain": self.domain_name,
                }
        return None

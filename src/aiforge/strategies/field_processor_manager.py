from typing import List, Dict

from .field_processor import (
    SemanticFieldStrategy,
    FieldProcessorStrategy,
)


class FieldProcessorManager:
    """字段处理策略管理器"""

    def __init__(self):
        self.strategies = [SemanticFieldStrategy()]
        self.default_strategy = SemanticFieldStrategy()

    def process_field(self, source_data: List[Dict], expected_fields: List[str]) -> List[Dict]:
        """根据数据格式自动选择合适的策略进行处理"""
        if not source_data or not expected_fields:
            return source_data

        # 找到能处理当前数据的策略
        for strategy in self.strategies:
            if strategy.can_handle(source_data):
                print(f"[DEBUG] 使用策略: {strategy.get_strategy_name()}")
                return strategy.process_fields(source_data, expected_fields)

        # 如果没有找到合适的策略，使用默认策略
        print(f"[DEBUG] 使用默认策略: {self.default_strategy.get_strategy_name()}")
        return self.default_strategy.process_fields(source_data, expected_fields)

    def add_strategy(self, strategy: FieldProcessorStrategy):
        """添加新的处理策略"""
        self.strategies.append(strategy)

    def get_available_strategies(self) -> List[str]:
        """获取可用的策略列表"""
        return [strategy.get_strategy_name() for strategy in self.strategies]

from validation_strategy import (
    DataFetchValidationStrategy,
    GeneralValidationStrategy,
    ValidationStrategy,
)


class ValidationStrategyManager:
    """验证策略管理器"""

    def __init__(self):
        self.strategies = [
            DataFetchValidationStrategy(),
            GeneralValidationStrategy(),  # 默认策略放最后
        ]

    def get_strategy(self, task_type: str) -> ValidationStrategy:
        """根据任务类型获取合适的验证策略"""
        for strategy in self.strategies:
            if strategy.can_handle(task_type):
                return strategy

        # 返回默认策略
        return GeneralValidationStrategy()

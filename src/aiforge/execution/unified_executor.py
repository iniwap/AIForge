from typing import Any, Dict
from .executor_interface import CachedModuleExecutor
from ..strategies.execution_strategy_manager import ExecutionStrategyManager
from ..strategies.execution_strategy import ExecutionStrategy


class UnifiedExecutor(CachedModuleExecutor):
    """统一执行器"""

    def __init__(self, components: Dict[str, Any] = None):
        self.strategy_manager = ExecutionStrategyManager(components)

    def can_handle(self, module) -> bool:
        """检查是否有策略能处理该模块"""
        # 使用空指令进行快速检查
        dummy_instruction = {"task_type": "general", "action": "process"}
        return any(
            strategy.can_handle(module, dummy_instruction)
            for strategy in self.strategy_manager.strategies
        )

    def execute(self, module, instruction: str, **kwargs) -> Any:
        """统一执行入口"""
        return self.strategy_manager.execute_module(module, **kwargs)

    def register_custom_strategy(self, strategy: ExecutionStrategy):
        """注册自定义执行策略"""
        self.strategy_manager.register_strategy(strategy)

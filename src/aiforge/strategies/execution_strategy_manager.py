from typing import Any, Dict, Optional
from .execution_strategy import ExecutionStrategy
from .strategy.parameterized_function import ParameterizedFunctionStrategy
from .strategy.file_operation import FileOperationStrategy
from .strategy.class_instantiation import ClassInstantiationStrategy
from .strategy.direct_result import DirectResultStrategy


class ExecutionStrategyManager:
    """执行策略管理器"""

    def __init__(self, components: Dict[str, Any] = None):
        self.components = components or {}
        self.strategies = []
        self._register_default_strategies()

    def _register_default_strategies(self):
        """注册默认策略"""
        parameter_mapping_service = self.components.get("parameter_mapping_service")

        self.register_strategy(ParameterizedFunctionStrategy(parameter_mapping_service))
        self.register_strategy(ClassInstantiationStrategy(parameter_mapping_service))
        self.register_strategy(DirectResultStrategy(parameter_mapping_service))
        self.register_strategy(FileOperationStrategy(parameter_mapping_service))

    def register_strategy(self, strategy: ExecutionStrategy):
        """注册执行策略"""
        self.strategies.append(strategy)
        # 按优先级排序
        self.strategies.sort(key=lambda s: s.get_priority(), reverse=True)

    def execute_module(self, module: Any, **kwargs) -> Optional[Any]:
        """执行模块，使用最合适的策略"""
        standardized_instruction = kwargs.get("standardized_instruction", {})

        for strategy in self.strategies:
            if strategy.can_handle(module, standardized_instruction):
                try:
                    result = strategy.execute(module, **kwargs)
                    if result is not None:
                        return result
                except Exception as e:
                    print(f"[DEBUG] 策略 {strategy.__class__.__name__} 执行失败: {e}")
                    continue
        return None

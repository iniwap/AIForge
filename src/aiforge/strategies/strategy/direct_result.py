from typing import Any, Dict, Optional

from ..execution_strategy import ExecutionStrategy


class DirectResultStrategy(ExecutionStrategy):
    """直接结果执行策略"""

    def __init__(self, components: Dict[str, Any] = None):
        super().__init__(components)

    def can_handle(self, module: Any, standardized_instruction: Dict[str, Any]) -> bool:
        return hasattr(module, "__result__")

    def execute(self, module: Any, **kwargs) -> Optional[Any]:
        standardized_instruction = kwargs.get("standardized_instruction", {})
        result = getattr(module, "__result__")

        security_result = self.perform_security_validation(module, **kwargs)
        if security_result:
            return security_result

        # 如果结果是函数，尝试参数化调用
        if callable(result):
            parameters = self._extract_parameters(standardized_instruction)
            # 使用基类的通用参数映射方法
            return self._invoke_with_parameters_base(
                result,
                parameters,
                standardized_instruction,
                use_advanced_mapping=False,  # 直接结果策略使用基础映射
            )

        return result

    def get_priority(self) -> int:
        return 50

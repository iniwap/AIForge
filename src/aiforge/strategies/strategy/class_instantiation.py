from typing import Any, Dict, Optional
import inspect

from ..execution_strategy import ExecutionStrategy


class ClassInstantiationStrategy(ExecutionStrategy):
    """类实例化执行策略"""

    def __init__(self, components: Dict[str, Any] = None):
        super().__init__(components)

    def can_handle(self, module: Any, standardized_instruction: Dict[str, Any]) -> bool:
        return self._has_executable_classes(module)

    def execute(self, module: Any, **kwargs) -> Optional[Any]:
        standardized_instruction = kwargs.get("standardized_instruction", {})

        security_result = self.perform_security_validation(module, **kwargs)
        if security_result:
            return security_result

        target_class = self._find_target_class(module)
        if not target_class:
            return None

        try:
            # 实例化类
            instance = target_class()

            # 调用execute_task方法
            if hasattr(instance, "execute_task"):
                parameters = self._extract_parameters(standardized_instruction)
                # 使用基类的通用参数映射方法
                return self._invoke_with_parameters_base(
                    instance.execute_task,
                    parameters,
                    standardized_instruction,
                    use_advanced_mapping=False,  # 类策略使用基础映射
                )

        except Exception:
            pass

        return None

    def get_priority(self) -> int:
        return 75

    def _has_executable_classes(self, module: Any) -> bool:
        """检查模块是否包含可执行的类"""
        for attr_name in dir(module):
            if not attr_name.startswith("_"):
                try:
                    attr = getattr(module, attr_name)
                    if inspect.isclass(attr) and hasattr(attr, "execute_task"):
                        return True
                except Exception:
                    continue
        return False

    def _find_target_class(self, module: Any) -> Optional[type]:
        """查找目标类"""
        for attr_name in dir(module):
            if not attr_name.startswith("_"):
                try:
                    attr = getattr(module, attr_name)
                    if inspect.isclass(attr) and hasattr(attr, "execute_task"):
                        return attr
                except Exception:
                    continue
        return None

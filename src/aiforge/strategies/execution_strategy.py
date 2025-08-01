from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
import inspect


class ExecutionStrategy(ABC):
    """执行策略接口"""

    def __init__(self, parameter_mapping_service=None):
        self.parameter_mapping_service = parameter_mapping_service

    @abstractmethod
    def can_handle(self, module: Any, standardized_instruction: Dict[str, Any]) -> bool:
        """判断是否能处理该模块和指令"""
        pass

    @abstractmethod
    def execute(self, module: Any, **kwargs) -> Optional[Any]:
        """执行模块"""
        pass

    @abstractmethod
    def get_priority(self) -> int:
        """获取策略优先级，数字越大优先级越高"""
        pass

    def _extract_parameters(self, standardized_instruction: Dict[str, Any]) -> Dict[str, Any]:
        """从标准化指令中提取参数"""
        required_parameters = standardized_instruction.get("required_parameters", {})
        parameters = {}

        for param_name, param_info in required_parameters.items():
            if isinstance(param_info, dict) and "value" in param_info:
                parameters[param_name] = param_info["value"]
            else:
                parameters[param_name] = param_info

        return parameters

    def _invoke_with_parameters_base(
        self,
        func: callable,
        parameters: Dict[str, Any],
        standardized_instruction: Dict[str, Any] = None,
        use_advanced_mapping: bool = True,
    ) -> Any:
        """基础参数映射和调用逻辑"""
        try:
            if use_advanced_mapping and self.parameter_mapping_service and standardized_instruction:
                # 使用高级参数映射服务
                context = {
                    "task_type": standardized_instruction.get("task_type"),
                    "action": standardized_instruction.get("action"),
                    "function_name": func.__name__,
                }

                mapped_params = self.parameter_mapping_service.map_parameters(
                    func, parameters, context
                )

                # 使用反馈机制执行
                result, success = self._execute_with_feedback(func, mapped_params, context)
                if success:
                    return result

            # 回退到基础参数映射
            return self._basic_parameter_mapping_and_call(func, parameters)

        except Exception as e:
            print(f"[DEBUG] 参数化调用失败: {e}")
            return None

    def _execute_with_feedback(self, func, mapped_params, context=None):
        """执行函数并反馈映射成功率"""
        try:
            result = func(**mapped_params)
            # 执行成功，更新映射成功率
            if self.parameter_mapping_service:
                self.parameter_mapping_service.update_mapping_success(True)
            return result, True
        except Exception:
            # 执行失败，更新映射失败率
            if self.parameter_mapping_service:
                self.parameter_mapping_service.update_mapping_success(False)
            return None, False

    def _basic_parameter_mapping_and_call(self, func: callable, parameters: Dict[str, Any]) -> Any:
        """基础参数映射和调用 - 通用实现"""
        try:
            sig = inspect.signature(func)
            func_params = list(sig.parameters.keys())

            # 映射参数
            mapped_params = {}
            for param_name in func_params:
                if param_name in parameters:
                    mapped_params[param_name] = parameters[param_name]

            if mapped_params:
                return func(**mapped_params)
            else:
                return func()
        except Exception:
            try:
                return func()
            except Exception:
                return None

import asyncio
import inspect
from typing import Any, Dict, List
from .executor_interface import CachedModuleExecutor


class UnifiedParameterizedExecutor(CachedModuleExecutor):
    """统一参数化执行器 - 处理所有执行场景"""

    def can_handle(self, module) -> bool:
        """检查模块是否可执行 - 更全面的检查"""
        # 检查各种可能的执行入口
        execution_candidates = self._find_execution_candidates(module)
        return len(execution_candidates) > 0

    def _find_execution_candidates(self, module) -> List[tuple]:
        """查找所有可能的执行入口"""
        candidates = []

        # 优先级1: 参数化函数
        if hasattr(module, "execute_task"):
            candidates.append(("parameterized", "execute_task", getattr(module, "execute_task")))

        # 优先级2: 标准入口函数
        for func_name in ["main", "run", "process", "handle"]:
            if hasattr(module, func_name) and callable(getattr(module, func_name)):
                candidates.append(("function", func_name, getattr(module, func_name)))

        # 优先级3: 类实例化
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if (
                inspect.isclass(attr)
                and hasattr(attr, "execute_task")
                and not attr_name.startswith("_")
            ):
                candidates.append(("class", attr_name, attr))

        # 优先级4: 直接结果变量
        if hasattr(module, "__result__"):
            candidates.append(("variable", "__result__", getattr(module, "__result__")))

        return candidates

    def _execute_by_type(
        self,
        exec_type: str,
        name: str,
        target: Any,
        parameters: Dict[str, Any],
        instruction: str,
        standardized_instruction: Dict[str, Any],
    ) -> Any:
        """根据类型执行"""
        if exec_type == "parameterized":
            return self._execute_parameterized_function(
                target, parameters, standardized_instruction
            )
        elif exec_type == "function":
            return self._execute_standard_function(target, parameters, instruction)
        elif exec_type == "class":
            return self._execute_class_method(
                target, parameters, instruction, standardized_instruction
            )
        elif exec_type == "variable":
            return target

        return None

    def _execute_parameterized_function(
        self,
        func: callable,
        parameters: Dict[str, Any],
        standardized_instruction: Dict[str, Any] = None,
    ) -> Any:
        """执行参数化函数 - 智能参数映射"""
        import inspect

        # 获取函数签名
        sig = inspect.signature(func)
        func_params = list(sig.parameters.keys())

        # 优先使用 standardized_instruction 中的 required_parameters
        effective_parameters = parameters
        if standardized_instruction:
            required_params = standardized_instruction.get("required_parameters", {})
            if required_params:
                effective_parameters = required_params

        # 智能参数值提取和映射
        param_values = {}

        for param_name in func_params:
            if param_name in effective_parameters:
                param_info = effective_parameters[param_name]
                if isinstance(param_info, dict) and "value" in param_info:
                    param_values[param_name] = param_info["value"]
                else:
                    param_values[param_name] = param_info
            else:
                # 尝试从函数参数默认值获取
                param_obj = sig.parameters[param_name]
                if param_obj.default != inspect.Parameter.empty:
                    param_values[param_name] = param_obj.default

        # 检查是否为异步函数
        if asyncio.iscoroutinefunction(func):
            return asyncio.run(func(**param_values))

        # 执行函数
        try:
            return func(**param_values)
        except TypeError as e:
            # 参数不匹配时的智能处理
            if "unexpected keyword argument" in str(e) or "missing" in str(e):
                # 只传递函数需要且我们有的参数
                filtered_params = {k: v for k, v in param_values.items() if k in func_params}
                try:
                    return func(**filtered_params)
                except TypeError:
                    # 最后回退：无参数调用
                    return func()
            raise e

    def execute(self, module, instruction: str, **kwargs) -> Any:
        """统一执行入口"""
        standardized_instruction = kwargs.get("standardized_instruction", {})

        # 优先使用 required_parameters，回退到 parameters
        parameters = standardized_instruction.get(
            "required_parameters", {}
        ) or standardized_instruction.get("parameters", {})

        candidates = self._find_execution_candidates(module)

        for exec_type, name, target in candidates:
            try:
                result = self._execute_by_type(
                    exec_type, name, target, parameters, instruction, standardized_instruction
                )
                if result is not None:
                    return result
            except Exception:
                continue

        return None

    def _execute_standard_function(
        self, func: callable, parameters: Dict[str, Any], instruction: str
    ) -> Any:
        """执行标准函数"""
        if asyncio.iscoroutinefunction(func):
            return asyncio.run(func())

        # 尝试不同的调用方式
        try:
            # 尝试传入instruction参数
            return func(instruction)
        except TypeError:
            try:
                # 尝试无参数调用
                return func()
            except Exception:
                return None

    def _execute_class_method(
        self,
        cls: type,
        parameters: Dict[str, Any],
        instruction: str,
        standardized_instruction: Dict[str, Any] = None,
    ) -> Any:
        """执行类方法"""
        try:
            # 实例化类
            instance = cls()

            # 调用execute_task方法
            if hasattr(instance, "execute_task"):
                return self._execute_parameterized_function(
                    instance.execute_task, parameters, standardized_instruction
                )

            return None
        except Exception:
            return None

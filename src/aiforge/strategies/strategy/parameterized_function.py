from typing import Any, Dict, Optional, List
import inspect
import asyncio

from ..execution_strategy import ExecutionStrategy


class ParameterizedFunctionStrategy(ExecutionStrategy):
    """参数化函数执行策略"""

    def __init__(self, components: Dict[str, Any] = None):
        super().__init__(components)

    def can_handle(self, module: Any, standardized_instruction: Dict[str, Any]) -> bool:
        return hasattr(module, "execute_task") or self._has_callable_functions(module)

    def execute(self, module: Any, **kwargs) -> Optional[Any]:
        standardized_instruction = kwargs.get("standardized_instruction", {})

        security_result = self.perform_security_validation(module, **kwargs)
        if security_result:
            return security_result

        # 查找可执行函数
        target_func = self._find_target_function(module, standardized_instruction)
        if not target_func:
            return None

        # 提取参数
        parameters = self._extract_parameters(standardized_instruction)

        # 使用基类的通用参数映射和调用方法
        result = self._invoke_with_parameters_base(
            target_func, parameters, standardized_instruction, use_advanced_mapping=True
        )

        if result is not None:
            return result

        # 如果基础映射失败，尝试多种调用策略作为最后回退
        # 检查是否为异步函数
        if asyncio.iscoroutinefunction(target_func):
            return asyncio.run(
                self._try_multiple_call_strategies(
                    target_func, parameters, list(inspect.signature(target_func).parameters.keys())
                )
            )

        # 尝试多种调用策略
        return self._try_multiple_call_strategies(
            target_func, parameters, list(inspect.signature(target_func).parameters.keys())
        )

    def get_priority(self) -> int:
        return 100

    def _has_callable_functions(self, module: Any) -> bool:
        """检查模块是否包含可调用函数"""
        # 检查标准入口函数
        standard_functions = [
            "main",
            "run",
            "process",
            "handle",
            "search_web",
            "fetch_data",
            "get_data",
        ]
        for func_name in standard_functions:
            if hasattr(module, func_name) and callable(getattr(module, func_name)):
                return True

        # 检查其他可调用属性（排除私有方法和内置方法）
        for attr_name in dir(module):
            if not attr_name.startswith("_") and not attr_name.startswith("__"):
                try:
                    attr = getattr(module, attr_name)
                    if callable(attr) and not inspect.isclass(attr):
                        return True
                except Exception:
                    continue

        return False

    def _find_target_function(self, module: Any, instruction: Dict[str, Any]) -> Optional[callable]:
        """根据指令类型智能查找目标函数"""
        task_type = instruction.get("task_type", "")
        action = instruction.get("action", "")

        # 优先级1: execute_task
        if hasattr(module, "execute_task") and callable(getattr(module, "execute_task")):
            return getattr(module, "execute_task")

        # 优先级2: 根据任务类型匹配函数名
        function_candidates = []
        if task_type == "data_fetch":
            function_candidates = ["search_web", "fetch_data", "get_data", "fetch_news", "search"]
        elif task_type == "data_process":
            function_candidates = ["process_data", "analyze_data", "transform_data", "process"]
        elif task_type == "content_generation":
            function_candidates = [
                "generate_content",
                "create_content",
                "write_content",
                "generate",
            ]
        elif task_type == "file_operation":
            function_candidates = ["process_file", "handle_file", "transform_file"]

        # 优先级3: 根据动作匹配
        if action:
            action_lower = action.lower()
            if "search" in action_lower or "fetch" in action_lower:
                function_candidates.extend(["search_web", "search", "fetch"])
            elif "process" in action_lower:
                function_candidates.extend(["process", "handle"])
            elif "generate" in action_lower:
                function_candidates.extend(["generate", "create"])

        # 添加通用候选
        function_candidates.extend(["main", "run", "process", "handle", "execute"])

        # 去重并查找
        seen = set()
        for func_name in function_candidates:
            if func_name not in seen:
                seen.add(func_name)
                if hasattr(module, func_name) and callable(getattr(module, func_name)):
                    return getattr(module, func_name)

        return None

    def _try_multiple_call_strategies(
        self, func, param_values: Dict, func_param_names: List[str]
    ) -> Any:
        """尝试多种调用策略"""
        # 策略1: 完整参数调用
        if len(param_values) == len(func_param_names) and param_values:
            try:
                return func(**param_values)
            except Exception:
                pass

        # 策略2: 部分参数调用（只传递函数需要且我们有的参数）
        if param_values:
            try:
                filtered_params = {k: v for k, v in param_values.items() if k in func_param_names}
                if filtered_params:
                    return func(**filtered_params)
            except Exception:
                pass

        # 策略3: 位置参数调用（按函数参数顺序）
        if param_values:
            try:
                ordered_values = []
                for param_name in func_param_names:
                    if param_name in param_values:
                        ordered_values.append(param_values[param_name])
                    else:
                        break

                if ordered_values:
                    return func(*ordered_values)
            except Exception:
                pass

        # 策略4: 无参数调用
        try:
            return func()
        except Exception:
            return None

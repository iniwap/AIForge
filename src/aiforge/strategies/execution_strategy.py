from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, List
import inspect
import asyncio
from .file_operation_strategy import FileOperationStrategy


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


class ParameterizedFunctionStrategy(ExecutionStrategy):
    """参数化函数执行策略"""

    def __init__(self, parameter_mapping_service=None):
        super().__init__(parameter_mapping_service)

    def can_handle(self, module: Any, standardized_instruction: Dict[str, Any]) -> bool:
        return hasattr(module, "execute_task") or self._has_callable_functions(module)

    def execute(self, module: Any, **kwargs) -> Optional[Any]:
        standardized_instruction = kwargs.get("standardized_instruction", {})

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
        print(f"[DEBUG] 策略执行: 映射后参数 {parameters}")

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
                print(f"[DEBUG] 尝试完整参数调用: {param_values}")
                return func(**param_values)
            except Exception as e:
                print(f"[DEBUG] 完整参数调用失败: {e}")

        # 策略2: 部分参数调用（只传递函数需要且我们有的参数）
        if param_values:
            try:
                filtered_params = {k: v for k, v in param_values.items() if k in func_param_names}
                if filtered_params:
                    print(f"[DEBUG] 尝试部分参数调用: {filtered_params}")
                    return func(**filtered_params)
            except Exception as e:
                print(f"[DEBUG] 部分参数调用失败: {e}")

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
                    print(f"[DEBUG] 尝试位置参数调用: {ordered_values}")
                    return func(*ordered_values)
            except Exception as e:
                print(f"[DEBUG] 位置参数调用失败: {e}")

        # 策略4: 无参数调用
        try:
            print("[DEBUG] 尝试无参数调用")
            return func()
        except Exception as e:
            print(f"[DEBUG] 无参数调用失败: {e}")
            return None


class DirectResultStrategy(ExecutionStrategy):
    """直接结果执行策略"""

    def __init__(self, parameter_mapping_service=None):
        super().__init__(parameter_mapping_service)

    def can_handle(self, module: Any, standardized_instruction: Dict[str, Any]) -> bool:
        return hasattr(module, "__result__")

    def execute(self, module: Any, **kwargs) -> Optional[Any]:
        standardized_instruction = kwargs.get("standardized_instruction", {})
        result = getattr(module, "__result__")

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


class ClassInstantiationStrategy(ExecutionStrategy):
    """类实例化执行策略"""

    def __init__(self, parameter_mapping_service=None):
        super().__init__(parameter_mapping_service)

    def can_handle(self, module: Any, standardized_instruction: Dict[str, Any]) -> bool:
        return self._has_executable_classes(module)

    def execute(self, module: Any, **kwargs) -> Optional[Any]:
        standardized_instruction = kwargs.get("standardized_instruction", {})

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

        except Exception as e:
            print(f"[DEBUG] 类实例化执行失败: {e}")

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

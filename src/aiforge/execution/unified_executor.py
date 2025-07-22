import asyncio
import inspect
from typing import Any, Dict, List
from .executor_interface import CachedModuleExecutor


class UnifiedParameterizedExecutor(CachedModuleExecutor):
    """统一参数化执行器"""

    def can_handle(self, module) -> bool:
        """检查模块是否可执行"""
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
        """执行参数化函数"""
        import inspect

        # 获取函数签名
        sig = inspect.signature(func)
        func_params = list(sig.parameters.keys())

        print(f"[DEBUG] 统一执行器: 函数参数 {func_params}")

        # 优先使用 standardized_instruction 中的 required_parameters
        effective_parameters = parameters
        if standardized_instruction:
            required_params = standardized_instruction.get("required_parameters", {})
            if required_params:
                effective_parameters = required_params

        print(f"[DEBUG] 统一执行器: 有效参数 {list(effective_parameters.keys())}")

        # 智能参数值提取和映射
        param_values = {}

        # 第一步：精确匹配
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

        print(f"[DEBUG] 统一执行器: 精确匹配后参数 {param_values}")

        # 第二步：如果参数不完全匹配，尝试智能映射
        if len(param_values) < len(func_params):
            print(f"[DEBUG] 统一执行器: 参数不完全匹配，尝试智能映射")
            smart_mapped = self._smart_parameter_mapping(
                effective_parameters, func_params, param_values
            )
            param_values.update(smart_mapped)
            print(f"[DEBUG] 统一执行器: 智能映射后参数 {param_values}")

        # 检查是否为异步函数
        if asyncio.iscoroutinefunction(func):
            return asyncio.run(self._try_multiple_call_strategies(func, param_values, func_params))

        # 尝试多种调用策略
        return self._try_multiple_call_strategies(func, param_values, func_params)

    def _smart_parameter_mapping(
        self, ai_params: Dict, func_param_names: List[str], existing_params: Dict
    ) -> Dict:
        """智能参数映射"""

        def calculate_similarity(str1, str2):
            # 标准化字符串
            s1 = str1.lower().replace("_", "").replace("-", "")
            s2 = str2.lower().replace("_", "").replace("-", "")

            # 完全匹配
            if s1 == s2:
                return 1.0

            # 包含关系匹配
            if s1 in s2 or s2 in s1:
                return 0.8

            # 编辑距离相似度
            def levenshtein_distance(a, b):
                if len(a) < len(b):
                    return levenshtein_distance(b, a)
                if len(b) == 0:
                    return len(a)

                previous_row = list(range(len(b) + 1))
                for i, c1 in enumerate(a):
                    current_row = [i + 1]
                    for j, c2 in enumerate(b):
                        insertions = previous_row[j + 1] + 1
                        deletions = current_row[j] + 1
                        substitutions = previous_row[j] + (c1 != c2)
                        current_row.append(min(insertions, deletions, substitutions))
                    previous_row = current_row
                return previous_row[-1]

            max_len = max(len(s1), len(s2))
            if max_len == 0:
                return 1.0

            distance = levenshtein_distance(s1, s2)
            return 1 - (distance / max_len)

        mapped_params = {}
        used_ai_params = set()

        # 为每个未匹配的函数参数找最佳匹配
        for func_param in func_param_names:
            if func_param in existing_params:
                continue  # 已经匹配过的跳过

            best_match = None
            best_score = 0

            for ai_param, ai_value in ai_params.items():
                if ai_param in used_ai_params:
                    continue

                score = calculate_similarity(func_param, ai_param)
                if score > best_score and score > 0.3:  # 相似度阈值
                    best_score = score
                    best_match = (ai_param, ai_value)

            if best_match:
                # 提取参数值
                param_info = best_match[1]
                if isinstance(param_info, dict) and "value" in param_info:
                    mapped_params[func_param] = param_info["value"]
                else:
                    mapped_params[func_param] = param_info

                used_ai_params.add(best_match[0])
                print(
                    f"[DEBUG] 参数映射: {func_param} <- {best_match[0]} (相似度: {best_score:.3f})"
                )

        return mapped_params

    def _try_multiple_call_strategies(
        self, func, param_values: Dict, func_param_names: List[str]
    ) -> Any:
        """尝试多种调用策略"""
        # 策略1: 完整参数调用
        if len(param_values) == len(func_param_names):
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
                # 按函数参数顺序提取值
                ordered_values = []
                for param_name in func_param_names:
                    if param_name in param_values:
                        ordered_values.append(param_values[param_name])
                    else:
                        break  # 如果某个参数缺失，停止添加

                if ordered_values:
                    print(f"[DEBUG] 尝试位置参数调用: {ordered_values}")
                    return func(*ordered_values)
            except Exception as e:
                print(f"[DEBUG] 位置参数调用失败: {e}")

        # 策略4: 无参数调用
        try:
            print(f"[DEBUG] 尝试无参数调用")
            return func()
        except Exception as e:
            print(f"[DEBUG] 无参数调用失败: {e}")
            return None

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

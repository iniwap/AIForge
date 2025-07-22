from typing import Any
from .executor_interface import CachedModuleExecutor


class SimilarityParameterExecutor(CachedModuleExecutor):
    """基于参数名相似度的执行器"""

    def can_handle(self, module) -> bool:
        return hasattr(module, "execute_task") and callable(getattr(module, "execute_task"))

    def execute(self, module, instruction: str, **kwargs) -> Any:
        standardized_instruction = kwargs.get("standardized_instruction", {})
        required_params = standardized_instruction.get("required_parameters", {})

        if not required_params:
            required_params = standardized_instruction.get("parameters", {})

        func = getattr(module, "execute_task")
        func_signature = self._get_function_signature(func)

        # 基于相似度的参数映射
        mapped_params = self._similarity_based_mapping(required_params, func_signature)

        # 尝试调用
        return self._try_call_with_mapping(func, mapped_params, func_signature)

    def _get_function_signature(self, func):
        """获取函数签名"""
        import inspect

        try:
            sig = inspect.signature(func)
            return {"param_names": list(sig.parameters.keys()), "param_count": len(sig.parameters)}
        except Exception:
            return {"param_names": [], "param_count": 0}

    def _similarity_based_mapping(self, ai_params, func_signature):
        """基于相似度的参数映射"""
        # 提取AI参数值
        ai_param_values = {}
        for key, param_info in ai_params.items():
            if isinstance(param_info, dict) and "value" in param_info:
                ai_param_values[key] = param_info["value"]
            else:
                ai_param_values[key] = param_info

        func_params = func_signature["param_names"]
        mapped_params = {}
        used_ai_params = set()

        # 为每个函数参数找最相似的AI参数
        for func_param in func_params:
            best_match = None
            best_score = 0

            for ai_param, ai_value in ai_param_values.items():
                if ai_param in used_ai_params:
                    continue

                score = self._calculate_similarity(func_param, ai_param)
                if score > best_score and score > 0.3:  # 相似度阈值
                    best_score = score
                    best_match = (ai_param, ai_value)

            if best_match:
                mapped_params[func_param] = best_match[1]
                used_ai_params.add(best_match[0])

        return mapped_params

    def _calculate_similarity(self, str1, str2):
        """计算字符串相似度"""

        # 使用编辑距离计算相似度
        def levenshtein_distance(s1, s2):
            if len(s1) < len(s2):
                return levenshtein_distance(s2, s1)

            if len(s2) == 0:
                return len(s1)

            previous_row = list(range(len(s2) + 1))
            for i, c1 in enumerate(s1):
                current_row = [i + 1]
                for j, c2 in enumerate(s2):
                    insertions = previous_row[j + 1] + 1
                    deletions = current_row[j] + 1
                    substitutions = previous_row[j] + (c1 != c2)
                    current_row.append(min(insertions, deletions, substitutions))
                previous_row = current_row

            return previous_row[-1]

        # 标准化字符串（转小写，移除下划线）
        s1 = str1.lower().replace("_", "")
        s2 = str2.lower().replace("_", "")

        # 计算相似度
        max_len = max(len(s1), len(s2))
        if max_len == 0:
            return 1.0

        distance = levenshtein_distance(s1, s2)
        similarity = 1 - (distance / max_len)

        # 额外的匹配规则
        if s1 in s2 or s2 in s1:
            similarity = max(similarity, 0.8)

        return similarity

    def _try_call_with_mapping(self, func, mapped_params, func_signature):
        """尝试调用函数"""
        func_param_count = func_signature["param_count"]
        mapped_count = len(mapped_params)

        print(f"[DEBUG] 函数需要 {func_param_count} 个参数，映射到 {mapped_count} 个")

        # 策略1: 如果映射的参数数量等于函数参数数量，直接调用
        if mapped_count == func_param_count:
            try:
                result = func(**mapped_params)
                print(f"[DEBUG] 完整参数调用成功")
                return result
            except Exception as e:
                print(f"[DEBUG] 完整参数调用失败: {e}")

        # 策略2: 如果映射的参数少于函数参数，尝试位置参数调用
        if mapped_count > 0 and mapped_count <= func_param_count:
            try:
                param_values = list(mapped_params.values())
                result = func(*param_values)
                print(f"[DEBUG] 位置参数调用成功")
                return result
            except Exception as e:
                print(f"[DEBUG] 位置参数调用失败: {e}")

        # 策略3: 尝试无参数调用
        try:
            result = func()
            print(f"[DEBUG] 无参数调用成功")
            return result
        except Exception as e:
            print(f"[DEBUG] 无参数调用失败: {e}")

        return None

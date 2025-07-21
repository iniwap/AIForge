from typing import Any
from .executor_interface import CachedModuleExecutor


class ParameterizedModuleExecutor(CachedModuleExecutor):
    """参数化模块执行器 - 支持动态参数传递"""

    def can_handle(self, module) -> bool:
        """检查模块是否支持参数化执行"""
        return hasattr(module, "execute_task") and callable(getattr(module, "execute_task"))

    def execute(self, module, instruction: str, **kwargs) -> Any:
        """执行参数化模块"""
        standardized_instruction = kwargs.get("standardized_instruction", {})
        parameters = standardized_instruction.get("parameters", {})

        try:
            # 提取参数值
            param_values = {}
            for key, param_info in parameters.items():
                if isinstance(param_info, dict) and "value" in param_info:
                    param_values[key] = param_info["value"]
                else:
                    param_values[key] = param_info

            # 调用参数化函数
            result = module.execute_task(**param_values)
            return result

        except TypeError as e:
            # 参数不匹配，尝试无参数调用
            if "unexpected keyword argument" in str(e):
                try:
                    return module.execute_task()
                except Exception:
                    return None
            return None
        except Exception:
            return None

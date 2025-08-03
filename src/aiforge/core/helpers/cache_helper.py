from typing import Dict, Any


class CacheHelper:
    """缓存操作辅助类"""

    @staticmethod
    def save_standardized_module(
        components: Dict[str, Any], standardized_instruction: Dict[str, Any], code: str
    ) -> str | None:
        """保存标准化模块到缓存"""
        code_cache = components.get("code_cache")
        if not code_cache:
            return None

        # 如果有动态任务类型管理器，注册新的任务类型和动作
        task_type = standardized_instruction.get("task_type", "general")
        action = standardized_instruction.get("action", "")
        task_type_manager = components.get("task_type_manager")

        if task_type_manager:
            task_type_manager.register_task_type(task_type, standardized_instruction)

            # 如果是AI分析来源，注册动态动作
            if standardized_instruction.get("source") == "ai_analysis" and action:
                task_type_manager.register_dynamic_action(
                    action, task_type, standardized_instruction
                )
                # 增加使用计数
                task_type_manager.increment_action_usage(action)

        try:
            # 提取参数化信息用于元数据
            required_params = standardized_instruction.get("required_parameters", {})
            dynamic_params = standardized_instruction.get("dynamic_params", {})
            source = standardized_instruction.get("source", "unknown")

            metadata = {
                "task_type": task_type,
                "is_standardized": True,
                "is_parameterized": bool(required_params),
                "parameter_count": len(required_params),
                "validation_level": "universal",
                "parameter_usage_validated": True,
                "source": source,
                "dynamic_params": dynamic_params,
            }

            # 调用缓存的保存方法
            result = code_cache.save_standardized_module(standardized_instruction, code, metadata)
            return result
        except Exception:
            return None

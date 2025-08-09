import re
from pathlib import Path
from typing import Dict, Any, List


class ParameterExtractor:
    """参数提取器 - 负责参数提取和处理"""

    def __init__(self, components: Dict[str, Any] = None):
        self.components = components or {}
        self._i18n_manager = self.components.get("i18n_manager")

    def smart_infer_action(self, instruction: str, possible_actions: List[str]) -> str:
        """智能推断动作"""
        instruction_lower = instruction.lower()

        # 从 i18n 配置获取动作关键词映射
        action_keywords = self._i18n_manager.t("action_keywords", default={})

        for action in possible_actions:
            if action in action_keywords:
                keywords = action_keywords[action]
                if isinstance(keywords, dict):
                    keywords = list(keywords.values())
                if any(keyword in instruction_lower for keyword in keywords):
                    return action

        return possible_actions[0] if possible_actions else "process"

    def extract_target(self, instruction: str) -> str:
        """提取操作目标"""
        return instruction[:100]  # 取前100个字符作为目标描述

    def smart_extract_parameters(
        self, instruction: str, common_params: List[str]
    ) -> Dict[str, Any]:
        """智能提取参数"""
        params = {}

        # 从 i18n 配置获取参数提取模式
        param_patterns = self._i18n_manager.t("param_patterns", default={})

        for param in common_params:
            if param in param_patterns:
                param_config = param_patterns[param]
                patterns = param_config.get("patterns", [])
                param_type = param_config.get("type", "str")

                for pattern in patterns:
                    match = re.search(pattern, instruction)
                    if match:
                        value = match.group(1).strip()
                        if param_type == "int":
                            try:
                                value = int(value)
                            except ValueError:
                                continue

                        params[param] = {
                            "value": value,
                            "type": param_type,
                        }
                        break

        return params

    def _extract_file_pattern(self, parameters: Dict[str, Any]) -> str:
        """从参数中提取文件路径模式"""
        # 检查各种可能的文件路径参数
        file_path_keys = ["file_path", "source_path", "target_path", "path", "filename"]

        for key in file_path_keys:
            if key in parameters:
                param_info = parameters[key]
                if isinstance(param_info, dict) and "value" in param_info:
                    file_path = param_info["value"]
                else:
                    file_path = str(param_info)

                # 提取文件扩展名和基本模式
                path_obj = Path(file_path)
                if path_obj.suffix:
                    return f"{path_obj.suffix.lower()}_file"
                elif "*" in file_path or "?" in file_path:
                    return "pattern_match"
                else:
                    return "generic_file"

        return "unknown_pattern"

    def generate_semantic_cache_key(
        self, task_type: str, instruction: str, parameters: Dict[str, Any] = None
    ) -> str:
        """基于参数化指令生成语义化缓存键"""
        key_components = [task_type]

        if task_type == "file_operation":
            # 文件操作的缓存键应该考虑操作类型和文件路径模式
            operation = parameters.get("operation", "unknown") if parameters else "unknown"
            file_pattern = (
                self._extract_file_pattern(parameters) if parameters else "unknown_pattern"
            )
            return f"file_op_{operation}_{file_pattern}_{hash(instruction) % 10000}"

        # 优先使用 required_parameters 生成稳定的缓存键
        if parameters:
            # 提取参数值，按参数名排序确保一致性
            param_values = []
            sorted_params = sorted(parameters.items())

            for param_name, param_info in sorted_params:
                if isinstance(param_info, dict) and "value" in param_info:
                    value = param_info["value"]
                    # 标准化参数值
                    if isinstance(value, str):
                        value = value.lower().strip()
                    param_values.append(f"{param_name}:{value}")
                elif param_info is not None:
                    param_values.append(f"{param_name}:{str(param_info).lower()}")

            if param_values:
                key_components.extend(param_values)

        # 如果没有参数，使用指令内容
        if len(key_components) == 1:
            key_components.append(instruction[:50])

        # 生成稳定的哈希
        content = "_".join(key_components)
        return f"{task_type}_{hash(content) % 100000}"

    @staticmethod
    def get_default_expected_output(
        task_type: str, extracted_params: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """获取默认的预期输出规则"""
        defaults = {
            "data_analysis": {
                "required_fields": ["data", "analysis"],
                "validation_rules": {
                    "min_items": 0,
                    "non_empty_fields": ["key_findings"],
                },
            },
            "data_fetch": {
                "required_fields": ["data", "status"],
                "validation_rules": {
                    "min_items": 1,
                    "non_empty_fields": ["data"],
                    "partial_success": True,
                    "min_valid_ratio": 0.3,
                },
            },
            "data_process": {
                "required_fields": ["data", "processed_data"],
                "validation_rules": {
                    "min_items": 0,
                    "non_empty_fields": ["processed_data"],
                },
            },
            "file_operation": {
                "required_fields": ["data", "status"],
                "validation_rules": {
                    "min_items": 0,
                },
            },
            "automation": {
                "required_fields": ["data", "status", "summary"],
                "validation_rules": {
                    "min_items": 0,
                    "non_empty_fields": ["summary"],
                },
            },
            "content_generation": {
                "required_fields": ["data", "generated_content"],
                "validation_rules": {
                    "min_items": 1,
                    "non_empty_fields": ["generated_content"],
                },
            },
            "default": {
                "required_fields": ["data", "status"],
                "validation_rules": {
                    "min_items": 0,
                },
            },
        }

        base_config = defaults.get(task_type, defaults.get("default"))

        # 通用的数量参数调整逻辑
        if extracted_params:
            quantity_params = [
                "required_count",
                "count",
                "limit",
                "num_items",
                "quantity",
                "amount",
            ]
            for param_name in quantity_params:
                if param_name in extracted_params:
                    param_info = extracted_params[param_name]
                    if isinstance(param_info, dict) and "value" in param_info:
                        try:
                            quantity = int(param_info["value"])
                            base_config["validation_rules"]["min_items"] = max(
                                1, min(quantity, 100)
                            )
                            break
                        except (ValueError, TypeError):
                            continue

        return base_config

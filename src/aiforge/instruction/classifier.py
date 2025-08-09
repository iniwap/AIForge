from typing import Dict, Any, List
from difflib import SequenceMatcher


class TaskClassifier:
    """任务分类器 - 负责任务类型分类和验证"""

    def __init__(self, components: Dict[str, Any] = None):
        self.components = components or {}
        self._i18n_manager = self.components.get("i18n_manager")
        self.task_type_manager = self.components.get("task_type_manager")

    def get_task_type_keywords(self, task_type):
        """动态获取任务类型的关键词"""
        if not self._i18n_manager:
            return []

        task_keywords = self._i18n_manager.t("keywords", default={}).get(task_type, {})

        keywords = []
        for key, value in task_keywords.items():
            if key != "exclude":
                keywords.append(value)

        return keywords

    def is_ai_analysis_valid(self, ai_analysis: Dict[str, Any]) -> bool:
        """验证AI分析结果的有效性"""
        # 1. 检查必要字段
        required_fields = ["task_type", "action", "target"]
        if not all(field in ai_analysis for field in required_fields):
            return False

        # 2. 检查task_type是否有效
        task_type = ai_analysis.get("task_type")
        if not task_type or not isinstance(task_type, str) or not task_type.strip():
            return False

        # 3. 检查是否使用了推荐的内置类型（从 i18n 配置获取）
        builtin_types = self._get_builtin_types_from_config()
        is_builtin = task_type in builtin_types

        # 4. 如果不是内置类型，进行额外验证
        if not is_builtin:
            # 检查是否与现有类型过于相似
            if self._is_too_similar_to_existing_types(task_type, builtin_types):
                return False

        # 5. 注册新的任务类型和动作（如果有管理器）
        if hasattr(self, "task_type_manager") and self.task_type_manager:
            task_type = ai_analysis.get("task_type")
            action = ai_analysis.get("action", "")

            # 注册任务类型
            self.task_type_manager.register_task_type(task_type, ai_analysis)

            # 注册动态动作
            if action and task_type:
                self.task_type_manager.register_dynamic_action(action, task_type, ai_analysis)

            # 记录类型使用统计
            builtin_types = self._get_builtin_types_from_config()
            is_builtin = task_type in builtin_types

        return True

    def _get_builtin_types_from_config(self):
        """从 i18n 配置获取内置任务类型列表"""
        if not self._i18n_manager:
            # 回退到硬编码列表
            return [
                "data_fetch",
                "data_process",
                "file_operation",
                "automation",
                "content_generation",
                "direct_response",
            ]

        # 从 i18n 配置中获取所有可用的任务类型
        keywords_config = self._i18n_manager.t("keywords", default={})

        return list(keywords_config.keys()) if keywords_config else []

    def _is_too_similar_to_existing_types(self, task_type: str, builtin_types: List[str]) -> bool:
        """检查是否与现有类型过于相似"""
        try:
            for existing_type in builtin_types:
                similarity = SequenceMatcher(None, task_type.lower(), existing_type.lower()).ratio()
                if similarity > 0.8:  # 相似度阈值
                    return True
            return False
        except Exception:
            return False

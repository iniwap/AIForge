from typing import Dict, Any, List, Tuple
from .rule_based_adapter import RuleBasedAdapter
from .ai_ui_adapter import AIUIAdapter
from .task_type_detector import TaskTypeDetector
from .ui_type_recommender import UITypeRecommender
from ...llm.llm_client import AIForgeLLMClient
from .learning_Interface import LearningInterface


class EnhancedHybridUIAdapter:
    """增强的混合UI适配器"""

    def __init__(self, llm_client: AIForgeLLMClient):
        self.rule_based_adapter = RuleBasedAdapter()
        self.ai_adapter = AIUIAdapter(llm_client)
        self.task_detector = TaskTypeDetector()
        self.ui_recommender = UITypeRecommender()

        # 为阶段3预留的学习接口
        self.learning_interface = LearningInterface()

    def adapt_data(
        self, result: Dict[str, Any], ui_type: str = None, context: str = "web"
    ) -> Dict[str, Any]:
        """智能适配数据为UI格式"""
        data = result.get("data", {})

        # 1. 智能检测任务类型（如果metadata中没有）
        task_type = result.get("metadata", {}).get("task_type")
        if not task_type:
            task_type = self.task_detector.detect_from_data(data)

        # 2. 智能推荐UI类型（如果未指定）
        if not ui_type:
            recommendations = self.ui_recommender.recommend_ui_types(data, task_type, context)
            ui_type = recommendations[0][0] if recommendations else "web_card"

        # 记录适配请求
        self.learning_interface.record_adaptation_request(data, task_type, ui_type)

        # 3. 优先使用规则适配
        if self.rule_based_adapter.can_handle(task_type, ui_type):
            adapted_result = self.rule_based_adapter.adapt(data, task_type, ui_type)
            adapted_result["adaptation_method"] = "rule_based"
            adapted_result["task_type"] = task_type

            # 记录规则适配结果
            self.learning_interface.record_rule_adaptation(task_type, ui_type, adapted_result)

            return adapted_result

        # 4. 回退到AI适配
        adapted_result = self.ai_adapter.adapt_for_display(data, ui_type)
        adapted_result["adaptation_method"] = "ai_based"
        adapted_result["task_type"] = task_type

        # 记录AI适配结果
        self.learning_interface.record_ai_adaptation(task_type, ui_type, data, adapted_result)

        return adapted_result

    def get_supported_combinations(self) -> Dict[str, List[str]]:
        """获取所有支持的任务类型和UI类型组合"""
        return self.rule_based_adapter.get_supported_combinations()

    def recommend_ui_types(
        self, result: Dict[str, Any], context: str = "web"
    ) -> List[Tuple[str, float]]:
        """为结果推荐最适合的UI类型"""
        data = result.get("data", {})
        task_type = result.get("metadata", {}).get("task_type")

        if not task_type:
            task_type = self.task_detector.detect_from_data(data)

        return self.ui_recommender.recommend_ui_types(data, task_type, context)

    def get_adaptation_stats(self) -> Dict[str, Any]:
        """获取适配统计信息"""
        stats = self.learning_interface.get_stats()
        stats["supported_combinations"] = self.get_supported_combinations()
        return stats

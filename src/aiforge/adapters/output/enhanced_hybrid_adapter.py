from typing import Dict, Any, List, Tuple
from .rule_based_adapter import RuleBasedAdapter
from .ai_ui_adapter import AIUIAdapter
from .task_type_detector import TaskTypeDetector
from .ui_type_recommender import UITypeRecommender
from ...llm.llm_client import AIForgeLLMClient
from .learning_Interface import LearningInterface
from ...core.result import AIForgeResult


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
        self, result: AIForgeResult, ui_type: str = None, context: str = "web"
    ) -> Dict[str, Any]:
        """智能适配数据为UI格式"""
        # 正确访问AIForgeResult对象属性
        task_type = result.task_type
        actual_data = result.data

        # 转换为完整字典格式供需要完整结构的组件使用
        result_dict = result.to_dict()

        # 1. 智能检测任务类型 - 使用实际数据内容
        if not task_type:
            task_type = self.task_detector.detect_from_data(actual_data)

        # 2. 智能推荐UI类型 - 使用实际数据内容
        if not ui_type:
            recommendations = self.ui_recommender.recommend_ui_types(
                actual_data, task_type, context
            )
            ui_type = recommendations[0][0] if recommendations else "card"

        # 记录适配请求 - 使用完整字典
        self.learning_interface.record_adaptation_request(result_dict, task_type, ui_type)

        # 3. 优先使用规则适配 - 使用完整字典
        if self.rule_based_adapter.can_handle(task_type, ui_type):
            adapted_result = self.rule_based_adapter.adapt(result_dict, task_type, ui_type)
            adapted_result["adaptation_method"] = "rule_based"
            adapted_result["task_type"] = task_type

            # 记录规则适配结果
            self.learning_interface.record_rule_adaptation(task_type, ui_type, adapted_result)

            return adapted_result

        # 4. 回退到AI适配 - 使用完整字典
        adapted_result = self.ai_adapter.adapt_for_display(result_dict, ui_type)
        adapted_result["adaptation_method"] = "ai_based"
        adapted_result["task_type"] = task_type

        # 记录AI适配结果
        self.learning_interface.record_ai_adaptation(
            task_type, ui_type, result_dict, adapted_result
        )

        return adapted_result

    def get_supported_combinations(self) -> Dict[str, List[str]]:
        """获取所有支持的任务类型和UI类型组合"""
        return self.rule_based_adapter.get_supported_combinations()

    def recommend_ui_types(
        self, result: Dict[str, Any], context: str = "web"
    ) -> List[Tuple[str, float]]:
        """为结果推荐最适合的UI类型"""
        # 修正数据访问：如果是AIForgeResult字典格式，提取实际数据
        if isinstance(result, dict) and "data" in result:
            actual_data = result["data"]
            task_type = result.get("task_type") or result.get("metadata", {}).get("task_type")
        else:
            actual_data = result
            task_type = None

        if not task_type:
            task_type = self.task_detector.detect_from_data(actual_data)

        return self.ui_recommender.recommend_ui_types(actual_data, task_type, context)

    def get_adaptation_stats(self) -> Dict[str, Any]:
        """获取适配统计信息"""
        stats = self.learning_interface.get_stats()
        stats["supported_combinations"] = self.get_supported_combinations()
        return stats

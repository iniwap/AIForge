from typing import Dict, Any, List, Tuple


class UITypeRecommender:
    """UI类型推荐器"""

    def __init__(self):
        self.recommendation_rules = {
            "data_fetch": {
                "web_card": {"score": 8, "conditions": ["single_item", "key_value_data"]},
                "mobile_list": {"score": 6, "conditions": ["mobile_friendly"]},
                "terminal_text": {"score": 7, "conditions": ["simple_display"]},
            },
            "data_analysis": {
                "web_dashboard": {
                    "score": 10,
                    "conditions": ["complex_analysis", "multiple_sections"],
                },
                "web_card": {"score": 6, "conditions": ["simple_summary"]},
                "web_table": {"score": 7, "conditions": ["tabular_metrics"]},
            },
            "file_operation": {
                "web_table": {"score": 9, "conditions": ["multiple_files", "status_tracking"]},
                "web_progress": {"score": 8, "conditions": ["batch_processing"]},
                "mobile_list": {"score": 6, "conditions": ["mobile_friendly"]},
            },
        }

    def recommend_ui_types(
        self, data: Dict[str, Any], task_type: str, context: str = "web"
    ) -> List[Tuple[str, float]]:
        """推荐UI类型，返回按分数排序的列表"""
        if task_type not in self.recommendation_rules:
            return [("web_card", 5.0), ("terminal_text", 4.0)]

        rules = self.recommendation_rules[task_type]
        recommendations = []

        for ui_type, rule in rules.items():
            base_score = rule["score"]
            conditions = rule["conditions"]

            # 计算条件匹配分数
            condition_score = sum(
                1 for condition in conditions if self._check_condition(data, condition, context)
            )
            condition_bonus = (condition_score / len(conditions)) * 2  # 最多+2分

            final_score = base_score + condition_bonus
            recommendations.append((ui_type, final_score))

        return sorted(recommendations, key=lambda x: x[1], reverse=True)

    def _check_condition(self, data: Dict[str, Any], condition: str, context: str) -> bool:
        """检查特定条件是否满足"""
        if condition == "single_item":
            return len(data) <= 5 and not any(isinstance(v, list) for v in data.values())
        elif condition == "multiple_results":
            return any(isinstance(v, list) and len(v) > 1 for v in data.values())
        elif condition == "structured_data":
            return any(isinstance(v, list) and v and isinstance(v[0], dict) for v in data.values())
        elif condition == "mobile_friendly":
            return context == "mobile" or len(str(data)) < 500
        elif condition == "complex_analysis":
            return len(data) > 3 and any(isinstance(v, dict) for v in data.values())
        elif condition == "few_results":
            lists = [v for v in data.values() if isinstance(v, list)]
            return lists and max(len(lst) for lst in lists) <= 3
        elif condition == "batch_processing":
            return "total" in str(data).lower() and "count" in str(data).lower()

        return False

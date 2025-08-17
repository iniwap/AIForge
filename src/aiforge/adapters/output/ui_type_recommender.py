from typing import Dict, Any, List, Tuple, Union


class UITypeRecommender:
    """UI类型推荐器"""

    def __init__(self):
        self.recommendation_rules = {
            # 数据获取任务
            "data_fetch": {
                "card": {"score": 8, "conditions": ["single_item", "key_value_data"]},
                "table": {"score": 9, "conditions": ["structured_data", "multiple_results"]},
                "map": {"score": 10, "conditions": ["location_data"]},
                "mobile_list": {"score": 6, "conditions": ["mobile_friendly"]},
                "terminal_text": {"score": 7, "conditions": ["simple_display"]},
            },
            # 数据分析任务
            "data_analysis": {
                "dashboard": {
                    "score": 10,
                    "conditions": ["complex_analysis", "multiple_sections"],
                },
                "chart": {"score": 9, "conditions": ["numerical_data"]},
                "table": {"score": 7, "conditions": ["tabular_metrics"]},
                "timeline": {"score": 5, "conditions": ["few_results"]},
                "card": {"score": 6, "conditions": ["simple_summary"]},
            },
            # 文件操作任务
            "file_operation": {
                "table": {"score": 9, "conditions": ["multiple_files", "status_tracking"]},
                "progress": {"score": 8, "conditions": ["batch_processing"]},
                "timeline": {"score": 7, "conditions": ["few_results"]},
                "mobile_list": {"score": 6, "conditions": ["mobile_friendly"]},
            },
            # 内容生成任务
            "content_generation": {
                "editor": {"score": 10, "conditions": ["single_item"]},
                "card": {"score": 5, "conditions": ["simple_display"]},
            },
            # 代码生成任务
            "code_generation": {
                "editor": {"score": 10, "conditions": ["single_item"]},
                "card": {"score": 6, "conditions": ["simple_display"]},
            },
            # 数据处理任务
            "data_process": {
                "table": {"score": 8, "conditions": ["structured_data"]},
                "dashboard": {"score": 7, "conditions": ["complex_analysis"]},
                "card": {"score": 6, "conditions": ["simple_summary"]},
            },
            # 自动化任务
            "automation": {
                "timeline": {"score": 9, "conditions": ["few_results"]},
                "calendar": {"score": 8, "conditions": ["time_data"]},
                "progress": {"score": 8, "conditions": ["batch_processing"]},
                "card": {"score": 6, "conditions": ["simple_display"]},
            },
            # 直接响应任务
            "direct_response": {
                "card": {"score": 9, "conditions": ["single_item"]},
                "editor": {"score": 7, "conditions": ["single_item"]},
                "terminal_text": {"score": 6, "conditions": ["simple_display"]},
            },
            # 搜索任务
            "search": {
                "table": {"score": 9, "conditions": ["multiple_results"]},
                "card": {"score": 8, "conditions": ["few_results"]},
                "mobile_list": {"score": 7, "conditions": ["mobile_friendly"]},
            },
            # 图像处理任务
            "image_processing": {
                "gallery": {"score": 10, "conditions": ["image_data"]},
                "card": {"score": 9, "conditions": ["single_item"]},
                "dashboard": {"score": 7, "conditions": ["complex_analysis"]},
            },
            # API集成任务
            "api_integration": {
                "table": {"score": 8, "conditions": ["structured_data"]},
                "card": {"score": 7, "conditions": ["simple_summary"]},
                "dashboard": {"score": 6, "conditions": ["complex_analysis"]},
            },
        }

    def recommend_ui_types(
        self, data: Union[Dict[str, Any], List[Any], str, Any], task_type: str, context: str = "web"
    ) -> List[Tuple[str, float]]:
        """推荐UI类型，返回按分数排序的列表

        Args:
            data: AIForgeResult.data 的实际内容，可能是字典、列表、字符串等
        """
        # 处理非字典类型的数据
        if not isinstance(data, dict):
            return self._recommend_for_non_dict_data(data, task_type, context)

        if task_type not in self.recommendation_rules:
            return [("card", 5.0), ("terminal_text", 4.0)]

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

    def _recommend_for_non_dict_data(
        self, data: Any, task_type: str, context: str
    ) -> List[Tuple[str, float]]:
        """为非字典类型数据推荐UI类型"""
        if isinstance(data, str):
            # 字符串数据推荐
            if len(data) > 500:
                return [("editor", 9.0), ("card", 6.0)]
            else:
                return [("card", 8.0), ("terminal_text", 6.0)]

        elif isinstance(data, list):
            # 列表数据推荐
            if len(data) > 10:
                return [("table", 9.0), ("mobile_list", 7.0)]
            elif len(data) <= 3:
                return [("card", 8.0), ("timeline", 6.0)]
            else:
                return [("table", 8.0), ("card", 7.0)]

        else:
            # 其他类型数据的默认推荐
            return [("card", 6.0), ("terminal_text", 5.0)]

    def _check_condition(self, data: Any, condition: str, context: str) -> bool:
        """检查特定条件是否满足"""
        # 基础数据结构条件
        if condition == "single_item":
            return len(data) <= 5 and not any(isinstance(v, list) for v in data.values())
        elif condition == "multiple_results":
            return any(isinstance(v, list) and len(v) > 1 for v in data.values())
        elif condition == "structured_data":
            return any(isinstance(v, list) and v and isinstance(v[0], dict) for v in data.values())
        elif condition == "few_results":
            lists = [v for v in data.values() if isinstance(v, list)]
            return lists and max(len(lst) for lst in lists) <= 3

        # 上下文相关条件
        elif condition == "mobile_friendly":
            return context == "mobile" or len(str(data)) < 500
        elif condition == "simple_display":
            return len(str(data)) < 1000

        # 数据分析相关条件
        elif condition == "complex_analysis":
            return len(data) > 3 and any(isinstance(v, dict) for v in data.values())
        elif condition == "multiple_sections":
            return len(data) > 5 or any(isinstance(v, dict) and len(v) > 3 for v in data.values())
        elif condition == "simple_summary":
            return "summary" in str(data).lower() or "total" in str(data).lower()
        elif condition == "tabular_metrics":
            return any("metric" in str(k).lower() or "count" in str(k).lower() for k in data.keys())
        elif condition == "numerical_data":
            return any(
                isinstance(v, (int, float)) for v in data.values() if not isinstance(v, bool)
            )

        # 文件操作相关条件
        elif condition == "multiple_files":
            return any("file" in str(k).lower() and isinstance(v, list) for k, v in data.items())
        elif condition == "status_tracking":
            return any("status" in str(k).lower() for k in data.keys())
        elif condition == "batch_processing":
            return "total" in str(data).lower() and "count" in str(data).lower()

        # 内容相关条件
        elif condition == "key_value_data":
            return isinstance(data, dict) and len(data) <= 10
        elif condition == "image_data":
            return any(
                "image" in str(k).lower()
                or "photo" in str(k).lower()
                or "picture" in str(k).lower()
                for k in data.keys()
            )
        elif condition == "location_data":
            return any(
                k.lower()
                in ["location", "address", "coordinates", "lat", "lng", "latitude", "longitude"]
                for k in data.keys()
            )
        elif condition == "time_data":
            return any(
                "time" in str(k).lower() or "date" in str(k).lower() or "schedule" in str(k).lower()
                for k in data.keys()
            )

        # 高级数据类型条件
        elif condition == "chart_data":
            return any(
                isinstance(v, list)
                and len(v) > 0
                and all(isinstance(item, (int, float)) for item in v if not isinstance(item, bool))
                for v in data.values()
            )
        elif condition == "timeline_data":
            return any(
                "step" in str(k).lower() or "phase" in str(k).lower() or "stage" in str(k).lower()
                for k in data.keys()
            )
        elif condition == "progress_data":
            return any(
                k.lower() in ["progress", "percentage", "completed", "done"] for k in data.keys()
            )
        elif condition == "hierarchical_data":
            return any(
                isinstance(v, dict) and any(isinstance(nested_v, dict) for nested_v in v.values())
                for v in data.values()
                if isinstance(v, dict)
            )

        # 内容质量条件
        elif condition == "rich_content":
            return any(len(str(v)) > 200 for v in data.values())
        elif condition == "minimal_content":
            return all(len(str(v)) < 50 for v in data.values())
        elif condition == "formatted_text":
            text_content = str(data)
            return any(marker in text_content for marker in ["#", "*", "_", "`", "```", "**"])

        # 交互性条件
        elif condition == "interactive_data":
            return any(
                "action" in str(k).lower() or "button" in str(k).lower() or "link" in str(k).lower()
                for k in data.keys()
            )
        elif condition == "readonly_data":
            return not any(
                "edit" in str(k).lower() or "modify" in str(k).lower() for k in data.keys()
            )

        return False

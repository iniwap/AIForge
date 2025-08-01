from typing import Dict, Any, List


class TaskTypeDetector:
    """任务类型检测器"""

    MAX_SINGLE_ITEM_KEYS = 5

    def __init__(self):
        self.detection_rules = {
            "data_fetch": {
                "data_patterns": [
                    "content",
                    "source",
                    "location",
                    "weather",
                    "temperature",
                    "title",
                    "abstract",
                    "url",
                    "publish_time",
                    "results",
                    "query",
                ],
                "structure_patterns": [
                    "single_item",
                    "key_value_pairs",
                    "search_results",
                    "result_list",
                ],
            },
            "data_analysis": {
                "data_patterns": ["analysis", "key_findings", "trends", "summary", "metrics"],
                "structure_patterns": ["analysis_report", "statistical_data"],
            },
            "file_operation": {
                "data_patterns": [
                    "processed_files",
                    "file",
                    "status",
                    "size",
                    "operation",
                    "path",
                    "filename",
                    "extension",
                    "created",
                    "modified",
                    "copied",
                    "moved",
                    "deleted",
                    "compressed",
                    "extracted",
                ],
                "structure_patterns": [
                    "file_list",
                    "processing_summary",
                    "operation_result",
                    "batch_result",
                    "file_tree",
                ],
            },
            "api_call": {
                "data_patterns": ["response_data", "status_code", "endpoint", "headers"],
                "structure_patterns": ["api_response", "http_metadata"],
            },
        }

    def detect_from_data(self, data: Dict[str, Any]) -> str:
        """从数据结构检测任务类型"""
        if not isinstance(data, dict):
            return "general"

        scores = {}
        for task_type, rules in self.detection_rules.items():
            score = self._calculate_match_score(data, rules)
            if score > 0:
                scores[task_type] = score

        if scores:
            return max(scores.items(), key=lambda x: x[1])[0]
        return "general"

    def _calculate_match_score(self, data: Dict[str, Any], rules: Dict[str, List[str]]) -> float:
        """计算匹配分数"""
        data_patterns = rules.get("data_patterns", [])
        structure_patterns = rules.get("structure_patterns", [])

        # 数据模式匹配
        data_score = sum(1 for pattern in data_patterns if self._has_data_pattern(data, pattern))

        # 结构模式匹配
        structure_score = sum(
            1 for pattern in structure_patterns if self._has_structure_pattern(data, pattern)
        )

        total_patterns = len(data_patterns) + len(structure_patterns)
        return (data_score + structure_score) / total_patterns if total_patterns > 0 else 0

    def _has_data_pattern(self, data: Dict[str, Any], pattern: str) -> bool:
        """检查是否包含特定数据模式"""
        # 直接键匹配
        if pattern in data:
            return True

        # 嵌套搜索
        for value in data.values():
            if isinstance(value, dict) and pattern in value:
                return True
            elif isinstance(value, list) and value:
                if isinstance(value[0], dict) and pattern in value[0]:
                    return True

        return False

    def _has_structure_pattern(self, data: Dict[str, Any], pattern: str) -> bool:
        """检查是否符合特定结构模式"""
        if pattern == "search_results" or pattern == "result_list":
            # 统一处理搜索结果检测
            if isinstance(data.get("data"), list):
                items = data["data"]
                if items and isinstance(items[0], dict):
                    from ...strategies.semantic_field_strategy import SemanticFieldStrategy

                    field_processor = SemanticFieldStrategy()
                    return field_processor.can_handle(items)
            return False

        if pattern == "single_item":
            return len(data) <= self.MAX_SINGLE_ITEM_KEYS and not any(
                isinstance(v, list) for v in data.values()
            )
        elif pattern == "search_metadata":
            return any(key in data for key in ["query", "total_count", "source"])
        elif pattern == "analysis_report":
            return any(key in data for key in ["analysis", "summary", "findings"])
        elif pattern == "file_list":
            return any(key in data for key in ["files", "processed_files"]) or (
                isinstance(data.get("file"), str) and "." in data.get("file", "")
            )
        elif pattern == "api_response":
            return any(key in data for key in ["status_code", "headers", "endpoint"])

        return False

from typing import Dict, Any, List, Union


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
            "content_generation": {
                "data_patterns": [
                    "generated_content",
                    "content",
                    "text",
                    "article",
                    "document",
                    "title",
                    "summary",
                    "word_count",
                    "markdown",
                    "html",
                ],
                "structure_patterns": ["single_content", "structured_content"],
            },
            "code_generation": {
                "data_patterns": [
                    "generated_code",
                    "code",
                    "script",
                    "function",
                    "class",
                    "language",
                    "syntax",
                    "lines",
                    "comments",
                ],
                "structure_patterns": ["code_block", "code_file", "code_snippet"],
            },
            "data_process": {
                "data_patterns": [
                    "processed_data",
                    "transformed",
                    "filtered",
                    "aggregated",
                    "cleaned",
                    "normalized",
                    "validated",
                ],
                "structure_patterns": ["processing_result", "batch_processing"],
            },
            "automation": {
                "data_patterns": [
                    "automation_steps",
                    "scheduled_tasks",
                    "workflow",
                    "trigger",
                    "condition",
                    "action",
                    "execution_time",
                ],
                "structure_patterns": ["automation_result", "workflow_status"],
            },
            "direct_response": {
                "data_patterns": [
                    "response",
                    "answer",
                    "explanation",
                    "suggestion",
                    "advice",
                    "recommendation",
                    "opinion",
                ],
                "structure_patterns": ["simple_response", "detailed_response"],
            },
            "search": {
                "data_patterns": [
                    "search_results",
                    "query",
                    "results",
                    "snippet",
                    "relevance",
                    "ranking",
                    "total_count",
                ],
                "structure_patterns": ["search_results", "ranked_results"],
            },
            "image_processing": {
                "data_patterns": [
                    "processed_images",
                    "image",
                    "photo",
                    "picture",
                    "thumbnail",
                    "dimensions",
                    "format",
                    "size",
                    "metadata",
                ],
                "structure_patterns": ["image_gallery", "image_metadata"],
            },
            "api_integration": {
                "data_patterns": [
                    "api_response",
                    "endpoint",
                    "method",
                    "status",
                    "response_time",
                    "data_count",
                    "errors",
                    "success_rate",
                ],
                "structure_patterns": ["api_result", "integration_status"],
            },
        }

    def detect_from_data(self, data: Union[Dict[str, Any], List[Any], str, Any]) -> str:
        """从实际数据内容检测任务类型

        Args:
            data: AIForgeResult.data 的实际内容，可能是字典、列表、字符串等
        """
        # 处理非字典类型的数据
        if isinstance(data, str):
            return self._detect_from_string_data(data)
        elif isinstance(data, list):
            return self._detect_from_list_data(data)
        elif not isinstance(data, dict):
            return "general"

        # 字典类型数据的检测
        scores = {}
        for task_type, rules in self.detection_rules.items():
            score = self._calculate_match_score(data, rules)
            if score > 0:
                scores[task_type] = score

        if scores:
            return max(scores.items(), key=lambda x: x[1])[0]
        return "general"

    def _detect_from_string_data(self, data: str) -> str:
        """从字符串数据检测任务类型"""
        data_lower = data.lower()

        # 检查代码生成特征
        if any(
            keyword in data_lower for keyword in ["def ", "function", "class ", "import ", "```"]
        ):
            return "code_generation"

        # 检查内容生成特征
        if len(data) > 100 and any(keyword in data_lower for keyword in ["# ", "## ", "**", "*"]):
            return "content_generation"

        # 默认为直接响应
        return "direct_response"

    def _detect_from_list_data(self, data: List[Any]) -> str:
        """从列表数据检测任务类型"""
        if not data:
            return "general"

        # 检查第一个元素的类型
        first_item = data[0]

        if isinstance(first_item, dict):
            # 使用现有的检测规则进行语义匹配
            scores = {}
            for task_type, rules in self.detection_rules.items():
                score = self._calculate_list_match_score(data, rules)
                if score > 0:
                    scores[task_type] = score

            if scores:
                return max(scores.items(), key=lambda x: x[1])[0]

            # 如果没有明确匹配，尝试使用语义字段策略
            try:
                from ...strategies.semantic_field_strategy import SemanticFieldStrategy

                field_processor = SemanticFieldStrategy()

                # 检查是否符合搜索结果格式
                if field_processor.can_handle(data):
                    return "search"
            except ImportError:
                pass

            # 回退到通用数据获取
            return "data_fetch"

        # 非字典列表，可能是处理结果
        return "data_process"

    def _calculate_list_match_score(self, data: List[Dict], rules: Dict[str, List[str]]) -> float:
        """计算列表数据的匹配分数"""
        if not data or not isinstance(data[0], dict):
            return 0.0

        data_patterns = rules.get("data_patterns", [])
        structure_patterns = rules.get("structure_patterns", [])

        # 对前几个元素进行模式匹配
        sample_items = data[: min(3, len(data))]
        total_data_score = 0

        for item in sample_items:
            item_score = sum(
                1 for pattern in data_patterns if self._has_data_pattern(item, pattern)
            )
            total_data_score += item_score

        # 平均数据模式分数
        avg_data_score = total_data_score / len(sample_items) if sample_items else 0

        # 结构模式匹配（针对列表结构）
        structure_score = 0
        for pattern in structure_patterns:
            if self._has_list_structure_pattern(data, pattern):
                structure_score += 1

        total_patterns = len(data_patterns) + len(structure_patterns)
        return (avg_data_score + structure_score) / total_patterns if total_patterns > 0 else 0

    def _has_list_structure_pattern(self, data: List[Dict], pattern: str) -> bool:
        """检查列表是否符合特定结构模式"""
        if not data or not isinstance(data[0], dict):
            return False

        first_item = data[0]

        if pattern in ["search_results", "result_list"]:
            # 使用语义字段策略进行更准确的判断
            try:
                from ...strategies.semantic_field_strategy import SemanticFieldStrategy

                field_processor = SemanticFieldStrategy()
                return field_processor.can_handle(data)
            except ImportError:
                # 回退到基本字段检查
                return any(
                    key in first_item for key in ["title", "url", "snippet", "source", "content"]
                )

        elif pattern == "file_list":
            return any(
                key in first_item for key in ["filename", "file", "path", "size", "extension"]
            )

        elif pattern == "result_list":
            return len(data) > 1 and isinstance(first_item, dict)

        return False

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

        # 搜索结果检测
        if pattern == "search_results" or pattern == "result_list":
            # 检查数据本身是否为搜索结果列表
            if isinstance(data, list) and data and isinstance(data[0], dict):
                return any(key in data[0] for key in ["title", "url", "snippet", "source"])
            # 检查数据中是否包含搜索结果列表
            for value in data.values():
                if isinstance(value, list) and value and isinstance(value[0], dict):
                    if any(key in value[0] for key in ["title", "url", "snippet", "source"]):
                        return True
            return False

        if pattern == "single_item":
            return len(data) <= self.MAX_SINGLE_ITEM_KEYS and not any(
                isinstance(v, list) for v in data.values()
            )
        elif pattern == "single_content":
            return len(data) <= 3 and any(
                key in data for key in ["content", "generated_content", "text"]
            )
        elif pattern == "structured_content":
            return any(key in data for key in ["title", "summary", "sections"])
        elif pattern == "code_block":
            return any(key in data for key in ["code", "generated_code", "language"])
        elif pattern == "processing_result":
            return any(key in data for key in ["processed", "result", "output"])
        elif pattern == "automation_result":
            return any(key in data for key in ["steps", "workflow", "automation"])
        elif pattern == "simple_response":
            return len(data) <= 2 and "response" in data
        elif pattern == "detailed_response":
            return "response" in data and len(str(data.get("response", ""))) > 100
        elif pattern == "ranked_results":
            return isinstance(data.get("results"), list) and any(
                "relevance" in str(item) or "score" in str(item)
                for item in data.get("results", [])[:3]
                if isinstance(item, dict)
            )
        elif pattern == "image_gallery":
            return any(key in data for key in ["images", "gallery", "photos"])
        elif pattern == "integration_status":
            return any(key in data for key in ["status", "success_rate", "errors"])
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

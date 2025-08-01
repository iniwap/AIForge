from abc import ABC, abstractmethod
from typing import Dict, Any, List
from .semantic_field_strategy import SemanticFieldStrategy


class TemplateGenerationStrategy(ABC):
    """模板生成策略接口"""

    @abstractmethod
    def generate_format(
        self, expected_output: Dict[str, Any], min_abstract_len: int, is_free_form: bool = False
    ) -> str:
        """生成数据格式模板"""
        pass

    @abstractmethod
    def get_strategy_name(self) -> str:
        """获取策略名称"""
        pass


class StandardTemplateStrategy(TemplateGenerationStrategy):
    """标准模板生成策略"""

    def __init__(self):
        self.field_processor = SemanticFieldStrategy()

    def get_strategy_name(self) -> str:
        return "standard_template_strategy"

    def generate_format(
        self, expected_output: Dict[str, Any], min_abstract_len: int, is_free_form: bool = False
    ) -> str:
        """生成标准化的数据格式模板"""
        abstract_len = min_abstract_len / 2 if not is_free_form else min_abstract_len / 4

        # 如果没有expected_output，使用基本格式
        if not expected_output or not expected_output.get("required_fields"):
            return self._get_default_format(abstract_len, is_free_form)

        expected_fields = expected_output["required_fields"]
        result_fields = []

        # 处理每个期望字段
        for field_name in expected_fields:
            description = self._get_field_description(field_name, abstract_len, is_free_form)
            result_fields.append(f'"{field_name}": "{description}"')

        # 确保必要字段存在
        self._ensure_required_fields(result_fields, expected_fields, abstract_len, is_free_form)

        return "{\n                " + ",\n                ".join(result_fields) + "\n            }"

    def _get_default_format(self, abstract_len: float, is_free_form: bool) -> str:
        """获取默认格式"""
        return """{{
                "title": "标题",
                "url": "链接",
                "content": "详细内容（去除空格换行，至少{}字）",
                "pub_time": "发布时间" + ("（可以为空）" if {} else "")
            }}""".format(
            abstract_len, is_free_form
        )

    def _get_field_description(
        self, field_name: str, abstract_len: float, is_free_form: bool
    ) -> str:
        """根据字段名获取描述"""

        if self.field_processor._matches_semantic(field_name, "title"):
            return "标题"
        elif self.field_processor._matches_semantic(field_name, "url"):
            return "链接"
        elif self.field_processor._matches_semantic(field_name, "content"):
            return f"详细内容（去除空格换行，至少{abstract_len}字）"
        elif self.field_processor._matches_semantic(field_name, "time"):
            return "发布时间" + ("（可以为''）" if is_free_form else "")
        else:
            return "对应值"

    def _ensure_required_fields(
        self,
        result_fields: List[str],
        expected_fields: List[str],
        abstract_len: float,
        is_free_form: bool,
    ):
        """确保必要字段存在"""

        # 检查并补充URL字段
        if not any(
            self.field_processor._matches_semantic(field, "url") for field in expected_fields
        ):
            result_fields.append('"url": "链接"')

        # 检查并补充内容字段
        if not any(
            self.field_processor._matches_semantic(field, "content") for field in expected_fields
        ):
            content_desc = f"详细内容（去除空格换行，至少{abstract_len}字）"
            result_fields.append(f'"content": "{content_desc}"')

        # 检查并补充时间字段
        if not any(
            self.field_processor._matches_semantic(field, "time") for field in expected_fields
        ):
            time_desc = "发布时间" + ("（可以为''）" if is_free_form else "")
            result_fields.append(f'"pub_time": "{time_desc}"')


class SearchParameterExtractor:
    def __init__(self):
        self.parameter_mappings = {
            "min_items": ["quantity", "count", "min_count", "min_items"],
            "max_results": ["max_results", "limit", "max_count"],
            "search_query": ["search_query", "query", "keyword"],
            "min_abstract_len": ["min_abstract_len", "min_content_len"],
            "max_abstract_len": ["max_abstract_len", "max_content_len"],
        }

    def extract_parameter(self, target_param: str, parameters: Dict[str, Any]) -> Any:
        """通用参数提取方法"""
        candidates = self.parameter_mappings.get(target_param, [])
        for param_name in candidates:
            if param_name in parameters:
                return self._extract_value(parameters[param_name])
        return None

    def _extract_value(self, param_info: Any) -> Any:
        """提取参数值"""
        if isinstance(param_info, dict) and "value" in param_info:
            return param_info["value"]
        return param_info

    def extract_search_params(
        self, standardized_instruction: Dict[str, Any], original_instruction: str
    ) -> Dict[str, Any]:
        """提取搜索参数的主要方法"""
        parameters = standardized_instruction.get("required_parameters", {})
        expected_output = standardized_instruction.get("expected_output", {})

        # 使用映射提取参数
        search_query = self.extract_parameter("search_query", parameters) or original_instruction
        min_items = self.extract_parameter("min_items", parameters) or 1
        max_results = self.extract_parameter("max_results", parameters) or 10

        # 从 validation_rules 获取 min_items
        if min_items == 1:
            validation_rules = expected_output.get("validation_rules", {})
            if "min_items" in validation_rules:
                try:
                    min_items = max(1, int(validation_rules["min_items"]))
                except (ValueError, TypeError):
                    pass

        # 确保 max_results 至少等于 min_items
        max_results = max(max_results, min_items)

        return {
            "search_query": search_query,
            "max_results": max_results,
            "min_items": min_items,
            "min_abstract_len": self.extract_parameter("min_abstract_len", parameters) or 300,
            "max_abstract_len": self.extract_parameter("max_abstract_len", parameters) or 500,
        }

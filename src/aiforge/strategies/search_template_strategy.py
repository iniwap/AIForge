from abc import ABC, abstractmethod
from typing import Dict, Any, List
from .semantic_field_strategy import SemanticFieldStrategy
from ..i18n.manager import AIForgeI18nManager


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

    def __init__(self, i18n_manager: AIForgeI18nManager):
        self.field_processor = SemanticFieldStrategy()
        self._i18n_manager = i18n_manager

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
        title_label = self._i18n_manager.t("template.title_label")
        url_label = self._i18n_manager.t("template.url_label")
        content_description = self._i18n_manager.t(
            "template.content_description", length=abstract_len
        )
        time_label = self._i18n_manager.t("template.time_label")
        optional_suffix = self._i18n_manager.t("template.optional_empty") if is_free_form else ""

        return f"""{{
                    "{title_label}": "{title_label}",
                    "{url_label}": "{url_label}",
                    "content": "{content_description}",
                    "pub_time": "{time_label}{optional_suffix}"
                }}"""

    def _get_field_description(
        self, field_name: str, abstract_len: float, is_free_form: bool
    ) -> str:
        """根据字段名获取描述"""

        if self.field_processor._matches_semantic(field_name, "title"):
            return self._i18n_manager.t("template.title_label")
        elif self.field_processor._matches_semantic(field_name, "url"):
            return self._i18n_manager.t("template.url_label")
        elif self.field_processor._matches_semantic(field_name, "content"):
            return self._i18n_manager.t("template.content_description", length=abstract_len)
        elif self.field_processor._matches_semantic(field_name, "time"):
            time_label = self._i18n_manager.t("template.time_label")
            optional_suffix = (
                self._i18n_manager.t("template.optional_empty_quotes") if is_free_form else ""
            )
            return time_label + optional_suffix
        else:
            return self._i18n_manager.t("template.corresponding_value")

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
            url_label = self._i18n_manager.t("template.url_label")
            result_fields.append(f'"url": "{url_label}"')

        # 检查并补充内容字段
        if not any(
            self.field_processor._matches_semantic(field, "content") for field in expected_fields
        ):
            content_desc = self._i18n_manager.t("template.content_description", length=abstract_len)
            result_fields.append(f'"content": "{content_desc}"')

        # 检查并补充时间字段
        if not any(
            self.field_processor._matches_semantic(field, "time") for field in expected_fields
        ):
            time_label = self._i18n_manager.t("template.time_label")
            optional_suffix = (
                self._i18n_manager.t("template.optional_empty_quotes") if is_free_form else ""
            )
            time_desc = time_label + optional_suffix
            result_fields.append(f'"pub_time": "{time_desc}"')

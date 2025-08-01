from abc import ABC, abstractmethod
from typing import Dict, List, Tuple
from .semantic_field_strategy import SemanticFieldStrategy


class ValidationStrategy(ABC):
    """验证策略接口"""

    @abstractmethod
    def validate_data_items(
        self, data: List[Dict], required_fields: List[str], non_empty_fields: List[str]
    ) -> Tuple[List[Dict], int]:
        """验证数据项并返回有效项和有效数量"""
        pass

    @abstractmethod
    def can_handle(self, task_type: str) -> bool:
        """判断是否能处理该任务类型"""
        pass


class DataFetchValidationStrategy(ValidationStrategy):
    """数据获取任务验证策略"""

    def can_handle(self, task_type: str) -> bool:
        return task_type == "data_fetch"

    def validate_data_items(
        self, data: List[Dict], required_fields: List[str], non_empty_fields: List[str]
    ) -> Tuple[List[Dict], int]:
        """使用语义字段处理进行验证"""
        from .semantic_field_strategy import SemanticFieldStrategy

        field_processor = SemanticFieldStrategy()
        valid_items = []

        for item in data:
            if isinstance(item, dict):
                # 检查必需字段 - 使用语义匹配
                has_required_fields = self._check_required_fields_semantic(
                    item, required_fields, field_processor
                )

                # 检查非空字段 - 使用语义匹配
                has_valid_content = self._check_non_empty_fields_semantic(
                    item, non_empty_fields, field_processor
                )

                if has_required_fields and has_valid_content:
                    valid_items.append(item)

        return valid_items, len(valid_items)

    def _check_required_fields_semantic(
        self, item: Dict, required_fields: List[str], field_processor: "SemanticFieldStrategy"
    ) -> bool:
        """使用语义匹配检查必需字段"""
        for required_field in required_fields:
            # 找到语义匹配的字段
            matched_field = field_processor._find_best_source_field(item, required_field)
            if matched_field not in item:
                return False
        return True

    def _check_non_empty_fields_semantic(
        self, item: Dict, non_empty_fields: List[str], field_processor: "SemanticFieldStrategy"
    ) -> bool:
        """使用语义匹配检查非空字段"""
        for field in non_empty_fields:
            matched_field = field_processor._find_best_source_field(item, field)
            if matched_field in item:
                value = item[matched_field]
                if not value or (isinstance(value, str) and len(value.strip()) < 10):
                    return False
        return True


class GeneralValidationStrategy(ValidationStrategy):
    """通用验证策略"""

    def can_handle(self, task_type: str) -> bool:
        return True  # 作为默认策略

    def validate_data_items(
        self, data: List[Dict], required_fields: List[str], non_empty_fields: List[str]
    ) -> Tuple[List[Dict], int]:
        """标准验证逻辑"""
        valid_items = []

        for item in data:
            if isinstance(item, dict):
                # 直接字段名匹配
                has_required_fields = all(field in item for field in required_fields)

                has_valid_content = True
                for field in non_empty_fields:
                    if field in item:
                        value = item[field]
                        if not value or (isinstance(value, str) and len(value.strip()) < 10):
                            has_valid_content = False
                            break

                if has_required_fields and has_valid_content:
                    valid_items.append(item)

        return valid_items, len(valid_items)


class ValidationStrategyManager:
    """验证策略管理器"""

    def __init__(self):
        self.strategies = [
            DataFetchValidationStrategy(),
            GeneralValidationStrategy(),  # 默认策略放最后
        ]

    def get_strategy(self, task_type: str) -> ValidationStrategy:
        """根据任务类型获取合适的验证策略"""
        for strategy in self.strategies:
            if strategy.can_handle(task_type):
                return strategy

        # 返回默认策略
        return GeneralValidationStrategy()

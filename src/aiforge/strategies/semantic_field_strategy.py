from abc import ABC, abstractmethod
from typing import Dict, List, Optional
import threading


class FieldProcessorStrategy(ABC):
    """字段处理策略接口"""

    @abstractmethod
    def process_fields(self, source_data: List[Dict], expected_fields: List[str]) -> List[Dict]:
        """处理字段数据"""
        pass

    @abstractmethod
    def can_handle(self, source_data: List[Dict]) -> bool:
        """判断是否能处理该数据格式"""
        pass

    @abstractmethod
    def get_strategy_name(self) -> str:
        """获取策略名称"""
        pass


class SemanticFieldStrategy(FieldProcessorStrategy):
    """基于语义的字段处理策略"""

    def __init__(self):
        self._model = None
        self._model_lock = threading.RLock()

        # 定义字段语义模式
        self.field_semantics = {
            "title": ["title", "标题", "headline", "subject", "name", "heading", "caption"],
            "url": ["url", "link", "source", "href", "source_url", "web_url", "address", "链接"],
            "content": [
                "content",
                "abstract",
                "article",
                "summary",
                "摘要",
                "内容",
                "正文",
                "description",
                "excerpt",
                "text",
                "body",
                "detail",
                "info",
            ],
            "date": [
                "date",
                "time",
                "pub_time",
                "publish_time",
                "publish_date",
                "created_at",
                "updated_at",
                "timestamp",
                "datetime",
                "时间",
                "日期",
                "publish",
                "created",
                "updated",
                "发布时间",
            ],
            "time": [
                "time",
                "date",
                "pub_time",
                "publish_time",
                "publish_date",
                "created_at",
                "updated_at",
                "timestamp",
                "datetime",
                "时间",
                "日期",
                "publish",
                "created",
                "updated",
            ],
        }

        # 字段优先级权重
        self.field_weights = {
            "title": {"title": 1.0, "headline": 0.9, "subject": 0.8, "name": 0.7},
            "url": {"url": 1.0, "link": 0.9, "source": 0.8, "href": 0.7},
            "content": {"content": 1.0, "abstract": 0.9, "article": 0.8, "summary": 0.7},
            "time": {"pub_time": 1.0, "date": 0.9, "time": 0.8, "timestamp": 0.7},
        }

    @property
    def model(self):
        """延迟加载语义模型"""
        if self._model is None:
            with self._model_lock:
                if self._model is None:
                    from ..models.model_manager import ModelManager

                    self._model = ModelManager().get_semantic_model()
        return self._model

    def _calculate_semantic_similarity(self, text1: str, text2: str) -> float:
        """计算语义相似度"""
        if not self.model:
            # 如果模型加载失败，回退到字符串匹配
            return 0.5 if text1.lower() in text2.lower() or text2.lower() in text1.lower() else 0.0

        try:
            embeddings = self.model.encode([text1, text2])
            from sklearn.metrics.pairwise import cosine_similarity

            similarity = cosine_similarity([embeddings[0]], [embeddings[1]])[0][0]
            return float(similarity)
        except Exception:
            return 0.0

    def get_strategy_name(self) -> str:
        return "semantic_field_strategy"

    def can_handle(self, source_data: List[Dict]) -> bool:
        """检查是否能处理该数据格式"""
        if not source_data or not isinstance(source_data[0], dict):
            return False

        first_item = source_data[0]
        source_fields = set(first_item.keys())

        # 检查是否至少包含标题和内容类型的字段
        has_title = any(self._matches_semantic(field, "title") for field in source_fields)
        has_content = any(self._matches_semantic(field, "content") for field in source_fields)

        return has_title and has_content

    def _matches_semantic(self, field_name: str, semantic_type: str) -> bool:
        """检查字段名是否匹配某个语义类型"""
        field_lower = field_name.lower().strip()
        patterns = self.field_semantics.get(semantic_type, [])

        # 完全匹配
        if field_lower in patterns:
            return True

        # 包含匹配
        return any(pattern in field_lower or field_lower in pattern for pattern in patterns)

    def _get_field_confidence(self, field_name: str, semantic_type: str) -> float:
        """计算字段匹配置信度"""
        field_lower = field_name.lower().strip()
        weights = self.field_weights.get(semantic_type, {})

        # 检查权重表中的匹配
        for pattern, weight in weights.items():
            if pattern == field_lower:
                return weight
            elif pattern in field_lower or field_lower in pattern:
                return weight * 0.8

        # 检查语义模式匹配
        patterns = self.field_semantics.get(semantic_type, [])
        for pattern in patterns:
            if pattern == field_lower:
                return 0.6
            elif pattern in field_lower or field_lower in pattern:
                return 0.4

        return 0.0

    def process_fields(self, source_data: List[Dict], expected_fields: List[str]) -> List[Dict]:
        """处理字段数据"""
        processed_results = []

        for item in source_data:
            if not isinstance(item, dict):
                processed_results.append(item)
                continue

            processed_item = {}

            # 为每个期望字段找到最佳匹配的源字段
            for field_name in expected_fields:
                best_match = self._find_best_source_field(item, field_name)
                processed_item[field_name] = item.get(best_match, "")

            processed_results.append(processed_item)

        return processed_results

    def _find_best_source_field(self, source_item: Dict, target_field: str) -> str:
        """为目标字段找到最佳匹配的源字段"""
        target_lower = target_field.lower().strip()

        # 首先尝试直接匹配
        if target_field in source_item:
            return target_field

        # 确定目标字段的语义类型
        target_semantic = self._determine_semantic_type(target_lower)

        if not target_semantic:
            return target_field

        # 在源数据中找到匹配该语义的最佳字段
        best_field = target_field
        best_confidence = 0.0

        for source_field in source_item.keys():
            confidence = self._get_field_confidence(source_field, target_semantic)
            if confidence > best_confidence:
                best_confidence = confidence
                best_field = source_field

        return best_field if best_confidence > 0.3 else target_field

    def _determine_semantic_type(self, field_name: str) -> Optional[str]:
        """确定字段的语义类型"""
        best_type = None
        best_confidence = 0.0

        for semantic_type in self.field_semantics.keys():
            confidence = self._get_field_confidence(field_name, semantic_type)
            if confidence > best_confidence:
                best_confidence = confidence
                best_type = semantic_type

        return best_type if best_confidence > 0.3 else None


class FieldProcessorManager:
    """字段处理策略管理器"""

    def __init__(self):
        self.strategies = [SemanticFieldStrategy()]
        self.default_strategy = SemanticFieldStrategy()

    def process_field(self, source_data: List[Dict], expected_fields: List[str]) -> List[Dict]:
        """根据数据格式自动选择合适的策略进行处理"""
        if not source_data or not expected_fields:
            return source_data

        # 找到能处理当前数据的策略
        for strategy in self.strategies:
            if strategy.can_handle(source_data):
                return strategy.process_fields(source_data, expected_fields)

        # 如果没有找到合适的策略，使用默认策略
        return self.default_strategy.process_fields(source_data, expected_fields)

    def add_strategy(self, strategy: FieldProcessorStrategy):
        """添加新的处理策略"""
        self.strategies.append(strategy)

    def get_available_strategies(self) -> List[str]:
        """获取可用的策略列表"""
        return [strategy.get_strategy_name() for strategy in self.strategies]

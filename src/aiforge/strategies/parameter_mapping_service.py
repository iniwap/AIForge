from typing import Dict, Any, Optional
import inspect
from abc import ABC, abstractmethod
from peewee import CharField, DoubleField, IntegerField, Model
from playhouse.sqlite_ext import SqliteExtDatabase
import time
import threading
from ..core.path_manager import AIForgePathManager


class ParameterMappingService:
    """统一参数映射服务"""

    def __init__(self):
        self.strategies = []
        self.cache_dir = AIForgePathManager.get_cache_dir()
        self.enhanced_semantic_strategy = None
        self.mapping_records = []  # 存储映射记录用于后续统计更新
        self._register_default_strategies()

    def _extract_with_strategy(self, param_name: str, available_params: Dict[str, Any]) -> Any:
        """使用策略提取参数值"""

        # 1. 首先尝试精确匹配
        if param_name in available_params:
            param_value = available_params[param_name]
            if isinstance(param_value, dict) and "value" in param_value:
                return param_value["value"]
            return param_value

        # 2. 然后使用策略匹配
        for strategy in self.strategies:
            if strategy.can_handle(param_name):
                result = strategy.map_parameter(param_name, available_params)
                if result is not None:
                    return result
        return None

    def _register_default_strategies(self):
        """注册默认映射策略"""
        # 硬编码策略优先级最高（稳定性）
        self.register_strategy(SearchParameterMappingStrategy())
        self.register_strategy(FileOperationMappingStrategy())

        # 增强语义策略作为重要补充
        self.enhanced_semantic_strategy = EnhancedSemanticMappingStrategy()
        self.register_strategy(self.enhanced_semantic_strategy)

        # 通用相似度策略作为兜底
        self.register_strategy(GeneralParameterMappingStrategy())

    def register_strategy(self, strategy: "ParameterMappingStrategy"):
        """注册参数映射策略"""
        self.strategies.append(strategy)
        # 按优先级排序
        self.strategies.sort(key=lambda s: s.get_priority(), reverse=True)

    def map_parameters(
        self,
        func: callable,
        available_params: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """统一参数映射入口"""
        sig = inspect.signature(func)
        func_params = list(sig.parameters.keys())

        mapped_params = {}
        self.mapping_records = []  # 重置映射记录

        # 关键改进：遍历函数的实际参数名，而不是输入参数名
        for param_name in func_params:
            for strategy in self.strategies:
                if strategy.can_handle(param_name, context):
                    mapped_value = strategy.map_parameter(param_name, available_params, context)
                    if mapped_value is not None:
                        # 使用函数的实际参数名作为键
                        mapped_params[param_name] = mapped_value

                        # 记录增强语义策略的映射信息
                        if isinstance(strategy, EnhancedSemanticMappingStrategy):
                            source_param = self._find_source_param(mapped_value, available_params)
                            if source_param:
                                self.mapping_records.append(
                                    {
                                        "source_param": source_param,
                                        "target_param": param_name,
                                        "context": context,
                                        "strategy": strategy,
                                    }
                                )
                        break

        # 2. 精确匹配（仅对未映射的参数）
        for param_name in func_params:
            if param_name not in mapped_params and param_name in available_params:
                mapped_params[param_name] = available_params[param_name]

        # 3. 应用默认值（增强逻辑）
        for param_name in func_params:
            if param_name not in mapped_params:
                # 首先尝试从函数签名获取默认值
                param_obj = sig.parameters[param_name]
                if param_obj.default != inspect.Parameter.empty:
                    mapped_params[param_name] = param_obj.default
                    continue

                # 然后尝试系统级默认值
                default_value = self._get_default_value(param_name, param_obj)
                if default_value is not None:
                    mapped_params[param_name] = default_value

        return mapped_params

    def _find_source_param(
        self, param_value: Any, available_params: Dict[str, Any]
    ) -> Optional[str]:
        """找到参数值对应的源参数名"""
        for param_name, value in available_params.items():
            if value == param_value:
                return param_name
        return None

    def update_mapping_success(self, success: bool):
        """更新所有映射记录的成功率"""
        for record in self.mapping_records:
            if isinstance(record["strategy"], EnhancedSemanticMappingStrategy):
                record["strategy"].update_mapping_success(
                    record["target_param"], record["source_param"], record["context"], success
                )

        # 清空映射记录
        self.mapping_records = []

    def _get_default_value(self, param_name: str, param_obj) -> Any:
        """获取参数默认值"""
        # 1. 从函数签名获取默认值
        if param_obj.default != inspect.Parameter.empty:
            return param_obj.default

        # 2. 系统级默认值
        system_defaults = {
            "max_results": 10,  # 默认最大结果数
            "min_items": 1,
            "timeout": 30,
            "limit": 10,
            "min_abstract_len": 300,
            "max_abstract_len": 1000,
            "page_size": 20,
            "retry_count": 3,
            "query": "",
            "search_query": "",
        }

        default_value = system_defaults.get(param_name)
        if default_value is not None:
            return default_value

        # 3. 基于参数名模式的智能默认值
        param_lower = param_name.lower()
        if "max" in param_lower and (
            "result" in param_lower or "count" in param_lower or "size" in param_lower
        ):
            return 10
        elif "min" in param_lower and ("item" in param_lower or "count" in param_lower):
            return 1
        elif "timeout" in param_lower or "delay" in param_lower:
            return 30
        elif "page" in param_lower and "size" in param_lower:
            return 20

        return None

    def extract_search_parameters(
        self, standardized_instruction: Dict[str, Any], original_instruction: str
    ) -> Dict[str, Any]:
        """专门用于搜索参数提取的方法"""
        parameters = standardized_instruction.get("required_parameters", {})
        expected_output = standardized_instruction.get("expected_output", {})
        # 使用现有的映射策略
        search_query = (
            self._extract_with_strategy("search_query", parameters) or original_instruction
        )

        # 正确提取 max_results
        max_results = 10  # 默认值
        max_results_candidates = [
            "max_results",
            "max_limit",
            "max_count",
            "max_size",
            "max_num_results",
        ]
        for candidate in max_results_candidates:
            if candidate in parameters:
                param_value = parameters[candidate]
                if isinstance(param_value, dict) and "value" in param_value:
                    max_results = param_value["value"]
                else:
                    max_results = param_value
                break

        # 直接从 validation_rules 获取 min_items
        validation_rules = expected_output.get("validation_rules", {})
        min_items = validation_rules.get("min_items", 1)

        # 确保都是整数类型再进行比较
        try:
            max_results = int(max_results)
            min_items = int(min_items)
            max_results = max(max_results, min_items)
        except (ValueError, TypeError):
            max_results = 10

        return {
            "search_query": search_query,
            "max_results": max_results,
            "min_items": min_items,
            "min_abstract_len": self._extract_with_strategy("min_abstract_len", parameters) or 300,
            "max_abstract_len": self._extract_with_strategy("max_abstract_len", parameters) or 1000,
        }


class ParameterMappingStrategy(ABC):
    """参数映射策略接口"""

    @abstractmethod
    def can_handle(self, param_name: str, context: Optional[Dict[str, Any]] = None) -> bool:
        """判断是否能处理该参数"""
        pass

    @abstractmethod
    def map_parameter(
        self,
        param_name: str,
        available_params: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """映射参数"""
        pass

    @abstractmethod
    def get_priority(self) -> int:
        """获取策略优先级"""
        pass


class SearchParameterMappingStrategy(ParameterMappingStrategy):
    """搜索参数映射策略"""

    def can_handle(self, param_name: str, context: Optional[Dict[str, Any]] = None) -> bool:
        search_params = [
            "search_query",
            "query",
            "keyword",
            "q",
            "max_results",
            "min_items",
            "topic",
        ]

        if param_name in search_params:
            return True

        if context:
            task_type = context.get("task_type", "")
            if task_type == "data_fetch" and param_name in search_params:
                return True

        return False

    def map_parameter(
        self,
        param_name: str,
        available_params: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> Any:
        mappings = {
            "query": ["search_query", "keyword", "q", "topic"],  # query 接受 search_query
            "search_query": ["query", "keyword", "q", "search_query", "topic"],
            # max_results 只接受明确表示"最大"语义的参数，不包括 quantity
            "max_results": ["max_results", "max_limit", "max_count", "max_size"],
            "min_items": ["min_items", "min_count", "quantity"],
            "min_abstract_len": [
                "min_abstract_len",
                "min_content_len",
                "min_article_len",
                "abstract_len",
                "content_len",
                "article_len",
            ],
            "max_abstract_len": ["max_abstract_len", "max_content_len", "max_article_len"],
        }

        candidates = mappings.get(param_name, [])
        for candidate in candidates:
            if candidate in available_params:
                result = available_params[candidate]
                if isinstance(result, dict) and "value" in result:
                    return result["value"]
                return result

        # 对于 max_results，使用默认值
        if param_name == "max_results":
            return 10
        elif param_name == "min_items":
            return 1

        return None

    def get_priority(self) -> int:
        return 100


class FileOperationMappingStrategy(ParameterMappingStrategy):
    """文件操作参数映射策略"""

    def __init__(self):
        # 扩展参数映射覆盖范围
        self.extended_mappings = {
            "file_path": [
                "path",
                "filename",
                "file",
                "source_path",
                "input_file",
                "src",
                "filepath",
            ],
            "source_path": ["file_path", "path", "filename", "source", "from", "input"],
            "target_path": ["output_path", "destination", "dest", "target", "to", "output"],
            "output_path": ["target_path", "destination", "output", "dest", "result_path"],
            "operation": ["action", "op", "command", "task", "method"],
            "recursive": ["recursive", "r", "deep", "recurse", "subdirs"],
            "force": ["force", "f", "overwrite", "replace", "confirm"],
            "encoding": ["encoding", "charset", "enc", "character_set"],
            "new_name": ["target_path", "name", "filename", "rename_to", "new_filename"],
            "dir_path": ["path", "directory", "folder", "dir", "location"],
            "directory": ["dir_path", "path", "folder", "dir", "location"],
            "extract_to": ["target_path", "output_path", "destination", "extract_path"],
            "content": ["data", "text", "body", "contents", "payload"],
            "mode": ["write_mode", "file_mode", "access_mode", "open_mode"],
            "max_size": ["size_limit", "max_file_size", "limit", "max_bytes"],
            "format": ["compression_format", "archive_format", "type", "file_type"],
            "file_list": ["files", "file_paths", "sources", "file_array", "paths"],
            "pattern": ["glob_pattern", "file_pattern", "match_pattern", "filter"],
            # 新增边缘情况参数
            "backup_dir": ["backup_path", "backup_location", "backup_folder"],
            "temp_dir": ["temp_path", "temporary_dir", "tmp_dir"],
            "permissions": ["mode", "chmod", "access_rights", "file_permissions"],
            "owner": ["user", "uid", "file_owner"],
            "group": ["gid", "file_group"],
            "preserve_metadata": ["preserve", "keep_metadata", "maintain_attrs"],
            "follow_symlinks": ["follow_links", "dereference", "resolve_links"],
        }

    def can_handle(self, param_name: str, context: Optional[Dict[str, Any]] = None) -> bool:
        if context:
            task_type = context.get("task_type", "")
            return param_name in self.extended_mappings and task_type == "file_operation"
        return param_name in self.extended_mappings

    def map_parameter(
        self,
        param_name: str,
        available_params: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> Any:
        candidates = self.extended_mappings.get(param_name, [])

        # 优先级映射：精确匹配 > 语义相似 > 默认值
        for candidate in candidates:
            if candidate in available_params:
                return available_params[candidate]

        # 语义相似度匹配
        semantic_match = self._semantic_match(param_name, available_params)
        if semantic_match is not None:
            return semantic_match

        # 智能默认值
        return self._get_intelligent_default(param_name, context)

    def _semantic_match(self, param_name: str, available_params: Dict[str, Any]) -> Any:
        """语义相似度匹配"""
        from difflib import SequenceMatcher

        best_match = None
        best_score = 0.6  # 提高阈值

        for available_param in available_params:
            score = SequenceMatcher(None, param_name.lower(), available_param.lower()).ratio()
            if score > best_score:
                best_score = score
                best_match = available_params[available_param]

        return best_match

    def _get_intelligent_default(self, param_name: str, context: Optional[Dict[str, Any]]) -> Any:
        """智能默认值生成"""
        defaults = {
            "recursive": False,
            "force": False,
            "encoding": "utf-8",
            "mode": "w",
            "max_size": 10 * 1024 * 1024,
            "format": "zip",
            "preserve_metadata": True,
            "follow_symlinks": False,
            "permissions": 0o644,
        }

        # 基于上下文的动态默认值
        if context:
            action = context.get("action", "").lower()
            if "backup" in action:
                defaults["preserve_metadata"] = True
                defaults["recursive"] = True
            elif "temp" in action:
                defaults["force"] = True

        return defaults.get(param_name)

    def get_priority(self) -> int:
        return 95  # 提高优先级


class GeneralParameterMappingStrategy(ParameterMappingStrategy):
    """通用参数映射策略（使用相似度算法）"""

    def can_handle(self, param_name: str, context: Optional[Dict[str, Any]] = None) -> bool:
        return True  # 作为兜底策略

    def map_parameter(
        self,
        param_name: str,
        available_params: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> Any:
        return self._smart_similarity_mapping(param_name, available_params)

    def get_priority(self) -> int:
        return 10  # 最低优先级

    def _smart_similarity_mapping(self, target_param: str, available_params: Dict[str, Any]) -> Any:
        """基于相似度的智能映射（复用现有逻辑）"""

        def calculate_similarity(str1, str2):
            s1 = str1.lower().replace("_", "").replace("-", "")
            s2 = str2.lower().replace("_", "").replace("-", "")

            if s1 == s2:
                return 1.0
            if s1 in s2 or s2 in s1:
                return 0.8

            # 编辑距离计算
            def levenshtein_distance(a, b):
                if len(a) < len(b):
                    return levenshtein_distance(b, a)
                if len(b) == 0:
                    return len(a)

                previous_row = list(range(len(b) + 1))
                for i, c1 in enumerate(a):
                    current_row = [i + 1]
                    for j, c2 in enumerate(b):
                        insertions = previous_row[j + 1] + 1
                        deletions = current_row[j] + 1
                        substitutions = previous_row[j] + (c1 != c2)
                        current_row.append(min(insertions, deletions, substitutions))
                    previous_row = current_row
                return previous_row[-1]

            max_len = max(len(s1), len(s2))
            if max_len == 0:
                return 1.0

            distance = levenshtein_distance(s1, s2)
            return 1 - (distance / max_len)

        best_match = None
        best_score = 0

        for param_name, param_value in available_params.items():
            score = calculate_similarity(target_param, param_name)
            if score > best_score and score > 0.3:  # 相似度阈值
                best_score = score
                best_match = param_value

        return best_match


class EnhancedSemanticMappingStrategy(ParameterMappingStrategy):
    """增强语义映射策略"""

    def __init__(self):
        self.cache_dir = AIForgePathManager.get_cache_dir()
        self.lock = threading.RLock()

        # 延迟加载语义模型
        self._semantic_model = None
        self._model_lock = threading.RLock()

        # 复用现有的语义字段策略
        from ..strategies.semantic_field_strategy import SemanticFieldStrategy

        self.field_strategy = SemanticFieldStrategy()

        # 初始化数据库
        self._init_database()

        # 上下文相关的语义权重
        self.context_weights = {
            "data_fetch": {
                "search_terms": ["query", "search", "keyword", "term", "find"],
                "count_terms": ["count", "num", "quantity", "amount", "size"],
                "limit_terms": ["limit", "max", "maximum", "top", "cap"],
            },
            "file_operation": {
                "path_terms": ["path", "file", "location", "dir", "folder"],
                "name_terms": ["name", "filename", "title", "label"],
            },
        }

    @property
    def semantic_model(self):
        """延迟加载语义模型"""
        if self._semantic_model is None:
            with self._model_lock:
                if self._semantic_model is None:
                    from ..models.model_manager import ModelManager

                    self._semantic_model = ModelManager().get_semantic_model()
        return self._semantic_model

    def _init_database(self):
        """初始化Peewee数据库和模型（复用code_cache模式）"""
        # 复用相同的数据库配置
        self.db_path = self.cache_dir / "parameter_mapping.db"
        self.db = SqliteExtDatabase(
            str(self.db_path),
            pragmas={
                "journal_mode": "wal",
                "cache_size": -1024 * 64,  # 64MB
                "foreign_keys": 1,
                "ignore_check_constraints": 0,
                "synchronous": 0,
            },
        )

        # 定义基础模型类
        class BaseModel(Model):
            class Meta:
                database = self.db

        # 参数映射统计模型
        class ParameterMappingStats(BaseModel):
            mapping_id = CharField(primary_key=True)
            source_param = CharField(index=True)
            target_param = CharField(index=True)
            context_hash = CharField(index=True)
            task_type = CharField(default="general", index=True)
            success_count = IntegerField(default=0)
            failure_count = IntegerField(default=0)
            confidence_score = DoubleField(default=0.0)
            created_at = DoubleField(default=time.time)
            last_used = DoubleField(default=time.time)

            @property
            def success_rate(self):
                total = self.success_count + self.failure_count
                return self.success_count / total if total > 0 else 0.5

            @property
            def total_attempts(self):
                return self.success_count + self.failure_count

            class Meta:
                table_name = "parameter_mapping_stats"
                indexes = (
                    (("source_param", "target_param", "context_hash"), True),
                    (("success_count", "failure_count"), False),
                    (("task_type", "context_hash"), False),
                )

        self.ParameterMappingStats = ParameterMappingStats

        # 创建表
        with self.db:
            self.db.create_tables([ParameterMappingStats], safe=True)

    def can_handle(self, param_name: str, context: Optional[Dict[str, Any]] = None) -> bool:
        return True  # 作为语义补充策略

    def get_priority(self) -> int:
        return 50  # 介于硬编码策略和通用策略之间

    def map_parameter(
        self,
        param_name: str,
        available_params: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """增强的参数映射方法"""
        context_hash = self._generate_context_hash(context)
        task_type = context.get("task_type", "general") if context else "general"

        # 1. 检查历史最佳映射
        cached_result = self._get_best_historical_mapping(
            param_name, available_params, context_hash, task_type
        )
        if cached_result:
            return cached_result

        # 2. 使用语义相似度计算
        best_match = self._semantic_similarity_with_context(param_name, available_params, context)

        # 3. 记录映射尝试
        if best_match is not None:
            source_param = self._find_source_param(best_match, available_params)
            if source_param:
                self._record_mapping_attempt(param_name, source_param, context_hash, task_type)

        return best_match

    def _get_best_historical_mapping(
        self, param_name: str, available_params: Dict[str, Any], context_hash: str, task_type: str
    ) -> Any:
        """获取历史最佳映射（使用Peewee ORM查询）"""
        with self.lock:
            try:
                # 查询历史成功率最高的映射
                best_mapping = (
                    self.ParameterMappingStats.select()
                    .where(
                        self.ParameterMappingStats.target_param == param_name,
                        self.ParameterMappingStats.context_hash == context_hash,
                        self.ParameterMappingStats.source_param.in_(list(available_params.keys())),
                    )
                    .order_by(
                        # 按成功率和置信度排序
                        (
                            self.ParameterMappingStats.success_count
                            / (
                                self.ParameterMappingStats.success_count
                                + self.ParameterMappingStats.failure_count
                            )
                        ).desc(),
                        self.ParameterMappingStats.confidence_score.desc(),
                    )
                    .first()
                )

                if best_mapping and best_mapping.total_attempts >= 3:
                    success_rate = best_mapping.success_rate
                    if success_rate > 0.6:
                        return available_params.get(best_mapping.source_param)

            except Exception:
                pass

        return None

    def _semantic_similarity_with_context(
        self, target_param: str, available_params: Dict[str, Any], context: Optional[Dict[str, Any]]
    ) -> Any:
        """结合上下文的语义相似度计算（复用现有算法）"""
        task_type = context.get("task_type") if context else None

        best_match = None
        best_score = 0.0

        for source_param, param_value in available_params.items():
            # 使用现有的字段语义匹配逻辑
            base_score = self._calculate_field_similarity(target_param, source_param)

            # 特殊处理搜索相关参数的语义匹配
            semantic_bonus = self._calculate_search_semantic_bonus(target_param, source_param)

            # 上下文权重调整
            context_bonus = self._calculate_context_bonus(target_param, source_param, task_type)

            final_score = base_score + semantic_bonus + context_bonus

            if final_score > best_score and final_score > 0.4:
                best_score = final_score
                # 正确提取嵌套字典中的值
                if isinstance(param_value, dict) and "value" in param_value:
                    best_match = param_value["value"]
                else:
                    best_match = param_value

        return best_match

    def _calculate_search_semantic_bonus(self, target_param: str, source_param: str) -> float:
        """计算搜索相关参数的语义加分"""

        # 只有明确的语义匹配才给高分
        strong_associations = {
            ("query", "search_query"): 0.9,
            ("search_query", "query"): 0.9,
            # max_results 只与明确表示"最大"的参数关联
            ("max_results", "max_limit"): 0.9,
            ("max_results", "max_count"): 0.9,
            ("max_results", "max_size"): 0.9,
        }

        key = (target_param.lower(), source_param.lower())
        if key in strong_associations:
            return strong_associations[key]

        # 检查包含关系，但更严格
        target_lower = target_param.lower()
        source_lower = source_param.lower()

        if "query" in target_lower and "query" in source_lower:
            return 0.7
        # 只有明确包含"max"的才与max_results关联
        if target_lower == "max_results" and "max" in source_lower:
            return 0.7

        return 0.0

    def _calculate_field_similarity(self, target_param: str, source_param: str) -> float:
        """使用现有字段策略计算相似度"""
        # 复用SemanticFieldStrategy的相似度计算逻辑
        confidence_scores = []

        # 检查各种语义类型的匹配度
        semantic_types = ["title", "url", "content", "date", "time"]
        for semantic_type in semantic_types:
            target_confidence = self.field_strategy._get_field_confidence(
                target_param, semantic_type
            )
            source_confidence = self.field_strategy._get_field_confidence(
                source_param, semantic_type
            )

            if target_confidence > 0 and source_confidence > 0:
                similarity = min(target_confidence, source_confidence) / max(
                    target_confidence, source_confidence
                )
                confidence_scores.append(similarity)

        if confidence_scores:
            return max(confidence_scores)

        # 回退到基础文本相似度（复用GeneralParameterMappingStrategy的实现）
        return self._calculate_text_similarity(target_param, source_param)

    def _calculate_text_similarity(self, str1: str, str2: str) -> float:
        """基础文本相似度计算"""
        # 复用GeneralParameterMappingStrategy中的levenshtein_distance算法
        s1 = str1.lower().replace("_", "").replace("-", "")
        s2 = str2.lower().replace("_", "").replace("-", "")

        if s1 == s2:
            return 1.0
        if s1 in s2 or s2 in s1:
            return 0.8

        def levenshtein_distance(a, b):
            if len(a) < len(b):
                return levenshtein_distance(b, a)
            if len(b) == 0:
                return len(a)

            previous_row = list(range(len(b) + 1))
            for i, c1 in enumerate(a):
                current_row = [i + 1]
                for j, c2 in enumerate(b):
                    insertions = previous_row[j + 1] + 1
                    deletions = current_row[j] + 1
                    substitutions = previous_row[j] + (c1 != c2)
                    current_row.append(min(insertions, deletions, substitutions))
                previous_row = current_row
            return previous_row[-1]

        max_len = max(len(s1), len(s2))
        if max_len == 0:
            return 1.0

        distance = levenshtein_distance(s1, s2)
        return 1 - (distance / max_len)

    def _calculate_context_bonus(
        self, target_param: str, source_param: str, task_type: Optional[str]
    ) -> float:
        """计算上下文相关的权重加成"""
        if not task_type or task_type not in self.context_weights:
            return 0.0

        context_terms = self.context_weights[task_type]
        bonus = 0.0

        target_lower = target_param.lower()
        source_lower = source_param.lower()

        for term_category, terms in context_terms.items():
            for term in terms:
                if term in target_lower and term in source_lower:
                    bonus += 0.3
                elif term in target_lower or term in source_lower:
                    bonus += 0.1

        return min(bonus, 0.5)

    def _generate_context_hash(self, context: Optional[Dict[str, Any]]) -> str:
        """生成上下文哈希"""
        if not context:
            return "default"

        import hashlib
        import json

        key_context = {"task_type": context.get("task_type"), "action": context.get("action")}
        return hashlib.md5(json.dumps(key_context, sort_keys=True).encode()).hexdigest()

    def _find_source_param(
        self, param_value: Any, available_params: Dict[str, Any]
    ) -> Optional[str]:
        """找到参数值对应的源参数名"""
        for param_name, value in available_params.items():
            if value == param_value:
                return param_name
        return None

    def _record_mapping_attempt(
        self, target_param: str, source_param: str, context_hash: str, task_type: str
    ):
        """记录映射尝试（使用Peewee ORM）"""
        mapping_id = f"{source_param}_{target_param}_{context_hash}"

        with self.lock:
            try:
                # 尝试获取现有记录
                mapping_record, created = self.ParameterMappingStats.get_or_create(
                    mapping_id=mapping_id,
                    defaults={
                        "source_param": source_param,
                        "target_param": target_param,
                        "context_hash": context_hash,
                        "task_type": task_type,
                        "success_count": 0,
                        "failure_count": 0,
                        "confidence_score": 0.0,
                    },
                )

                if not created:
                    # 更新最后使用时间
                    mapping_record.last_used = time.time()
                    mapping_record.save()

            except Exception:
                pass

    def update_mapping_success(
        self, target_param: str, source_param: str, context: Optional[Dict[str, Any]], success: bool
    ):
        """更新映射成功率统计（使用Peewee ORM）"""
        context_hash = self._generate_context_hash(context)
        mapping_id = f"{source_param}_{target_param}_{context_hash}"

        with self.lock:
            try:
                mapping_record = self.ParameterMappingStats.get(
                    self.ParameterMappingStats.mapping_id == mapping_id
                )

                if success:
                    mapping_record.success_count += 1
                else:
                    mapping_record.failure_count += 1

                # 更新最后使用时间和置信度分数
                mapping_record.last_used = time.time()

                # 根据成功率动态调整置信度分数
                total_attempts = mapping_record.total_attempts
                if total_attempts > 0:
                    mapping_record.confidence_score = mapping_record.success_rate

                mapping_record.save()

            except self.ParameterMappingStats.DoesNotExist:
                pass
            except Exception:
                pass

    def cleanup_low_performance_mappings(self, failure_threshold: float = 0.8):
        """清理低性能映射记录（使用Peewee ORM）"""
        with self.lock:
            try:
                # 删除失败率过高的映射记录
                low_performance_mappings = self.ParameterMappingStats.select().where(
                    (
                        self.ParameterMappingStats.success_count
                        + self.ParameterMappingStats.failure_count
                    )
                    >= 5,
                    (
                        self.ParameterMappingStats.failure_count
                        * 1.0
                        / (
                            self.ParameterMappingStats.success_count
                            + self.ParameterMappingStats.failure_count
                        )
                    )
                    > failure_threshold,
                )

                deleted_count = 0
                for mapping in low_performance_mappings:
                    mapping.delete_instance()
                    deleted_count += 1
            except Exception:
                pass

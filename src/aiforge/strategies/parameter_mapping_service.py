from typing import Dict, Any, Optional
import inspect
from abc import ABC, abstractmethod


class ParameterMappingService:
    """统一参数映射服务"""

    def __init__(self):
        self.strategies = []
        self._register_default_strategies()

    def _extract_with_strategy(self, param_name: str, available_params: Dict[str, Any]) -> Any:
        """使用策略提取参数值"""
        for strategy in self.strategies:
            if strategy.can_handle(param_name):
                result = strategy.map_parameter(param_name, available_params)
                if result is not None:
                    return result
        return None

    def _register_default_strategies(self):
        """注册默认映射策略"""
        self.register_strategy(SearchParameterMappingStrategy())
        self.register_strategy(FileOperationMappingStrategy())
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

        # 1. 使用策略进行智能映射（优先级提高）
        for param_name in func_params:
            for strategy in self.strategies:
                if strategy.can_handle(param_name, context):
                    mapped_value = strategy.map_parameter(param_name, available_params, context)
                    if mapped_value is not None:
                        mapped_params[param_name] = mapped_value
                        break

        # 2. 精确匹配（仅对未映射的参数）
        for param_name in func_params:
            if param_name not in mapped_params and param_name in available_params:
                mapped_params[param_name] = available_params[param_name]

        # 3. 应用默认值
        for param_name in func_params:
            if param_name not in mapped_params:
                default_value = self._get_default_value(param_name, sig.parameters[param_name])
                if default_value is not None:
                    mapped_params[param_name] = default_value

        return mapped_params

    def _get_default_value(self, param_name: str, param_obj) -> Any:
        """获取参数默认值"""
        # 1. 从函数签名获取默认值
        if param_obj.default != inspect.Parameter.empty:
            return param_obj.default

        # 2. 系统级默认值
        system_defaults = {"max_results": 10, "min_items": 1, "timeout": 30, "limit": 10}

        return system_defaults.get(param_name)

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

        # 只有AI明确分析出 max_results 相关参数时才提取，否则使用默认值
        max_results = 10  # 默认值
        max_results_candidates = [
            "max_results",
            "max_limit",
            "max_count",
            "max_size",
        ]
        for candidate in max_results_candidates:
            if candidate in parameters:
                param_value = parameters[candidate]
                if isinstance(param_value, dict) and "value" in param_value:
                    max_results = param_value["value"]
                else:
                    max_results = param_value
                break

        # min_items 从 num_results, count 等参数或 validation_rules 获取
        min_items = self._extract_with_strategy("min_items", parameters) or 1

        # 如果没有从参数中提取到 min_items，从 validation_rules 获取
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
            "min_abstract_len": self._extract_with_strategy("min_abstract_len", parameters) or 300,
            "max_abstract_len": self._extract_with_strategy("max_abstract_len", parameters) or 500,
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
        search_params = ["search_query", "query", "max_results", "min_items"]
        if context:
            task_type = context.get("task_type", "")
            return param_name in search_params and task_type == "data_fetch"
        return param_name in search_params

    def map_parameter(
        self,
        param_name: str,
        available_params: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> Any:
        mappings = {
            "search_query": ["query", "keyword", "q"],
            "query": ["search_query", "keyword"],
            "max_results": ["max_results", "max_limit", "max_count", "max_size"],
            "min_items": [
                "quantity",
                "count",
                "min_count",
                "num_results",
            ],
        }

        candidates = mappings.get(param_name, [])

        for candidate in candidates:
            if candidate in available_params:
                result = available_params[candidate]
                return result

        return None

    def get_priority(self) -> int:
        return 100


class FileOperationMappingStrategy(ParameterMappingStrategy):
    """文件操作参数映射策略"""

    def can_handle(self, param_name: str, context: Optional[Dict[str, Any]] = None) -> bool:
        file_params = ["file_path", "path", "filename", "output_path"]
        if context:
            task_type = context.get("task_type", "")
            return param_name in file_params and task_type == "file_operation"
        return param_name in file_params

    def map_parameter(
        self,
        param_name: str,
        available_params: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> Any:
        mappings = {
            "file_path": ["path", "filename", "file"],
            "path": ["file_path", "filename"],
            "output_path": ["output", "target_path", "destination"],
        }

        candidates = mappings.get(param_name, [])
        for candidate in candidates:
            if candidate in available_params:
                return available_params[candidate]

        return None

    def get_priority(self) -> int:
        return 90


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

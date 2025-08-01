from typing import Dict, Any, Optional
import inspect
from abc import ABC, abstractmethod


class ParameterMappingService:
    """统一参数映射服务"""

    def __init__(self):
        self.strategies = []
        self._register_default_strategies()

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

        # 1. 精确匹配
        for param_name in func_params:
            if param_name in available_params:
                mapped_params[param_name] = available_params[param_name]

        # 2. 使用策略进行智能映射
        for param_name in func_params:
            if param_name not in mapped_params:
                for strategy in self.strategies:
                    if strategy.can_handle(param_name, context):
                        mapped_value = strategy.map_parameter(param_name, available_params, context)
                        if mapped_value is not None:
                            mapped_params[param_name] = mapped_value
                            break

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
            "max_results": ["limit", "max_count", "size"],  # 注意：不包含 quantity/count
            "min_items": ["quantity", "count", "min_count"],  # quantity/count 映射到 min_items
        }

        candidates = mappings.get(param_name, [])
        for candidate in candidates:
            if candidate in available_params:
                return available_params[candidate]

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

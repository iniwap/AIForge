from typing import Dict, Any, List
import inspect
import hashlib

from .network_controller import NetworkSecurityController
from .file_controller import FileSecurityController
from .code_controller import CodeSecurityController


class SecurityMiddleware:
    """安全中间件 - 统一安全验证入口"""

    def __init__(self, components: Dict[str, Any] = None):
        self.components = components
        self.network_controller = NetworkSecurityController(components)
        self.file_controller = FileSecurityController(components)
        self.code_controller = CodeSecurityController(components)
        self._validation_cache = {}

    def validate_execution(
        self, module: Any, context: Dict[str, Any], strategy_type: str = None
    ) -> Dict[str, Any]:
        """统一的安全验证入口"""
        code = self._extract_code_from_module(module)
        cache_key = self._generate_cache_key(code, context, strategy_type or "default")

        if cache_key in self._validation_cache:
            return self._validation_cache[cache_key]

        validation_config = self._get_validation_config_for_strategy(strategy_type or "default")
        results = {"overall_allowed": True, "blocked_reasons": []}

        # 标准的分离验证
        if validation_config["need_network_validation"]:
            network_result = self.network_controller.validate_network_access(code, context)
            results["network"] = network_result
            if not network_result["allowed"]:
                results["overall_allowed"] = False
                results["blocked_reasons"].append("network_access_denied")

        if validation_config["need_file_validation"]:
            file_result = self.file_controller.validate_file_access(code, context)
            results["file"] = file_result
            if not file_result["allowed"]:
                results["overall_allowed"] = False
                results["blocked_reasons"].append("file_access_denied")

        if validation_config["need_code_validation"]:
            code_result = self.code_controller.validate_code_access(code, context)
            results["code"] = code_result
            if not code_result["allowed"]:
                results["overall_allowed"] = False
                results["blocked_reasons"].append("code_access_denied")

        if results["overall_allowed"]:
            self._validation_cache[cache_key] = results

        return results

    def _get_validation_config_for_strategy(self, strategy_type: str) -> Dict[str, bool]:
        """获取策略特定的验证配置"""
        configs = {
            "AIForgeExecutionEngine": {
                "need_network_validation": True,
                "need_file_validation": False,
                "need_code_validation": True,
            },
            "ParameterizedFunctionStrategy": {
                "need_network_validation": True,
                "need_file_validation": False,
                "need_code_validation": False,
            },
            "FileOperationStrategy": {
                "need_network_validation": False,
                "need_file_validation": True,
                "need_code_validation": False,
            },
            "ClassInstantiationStrategy": {
                "need_network_validation": True,
                "need_file_validation": False,
                "need_code_validation": False,
            },
            "DirectResultStrategy": {
                "need_network_validation": True,
                "need_file_validation": False,
                "need_code_validation": False,
            },
        }
        return configs.get(
            strategy_type,
            {
                "need_network_validation": True,
                "need_file_validation": True,
                "need_code_validation": True,
            },
        )

    def _extract_code_from_module(self, module) -> str:
        """从模块中提取代码"""
        try:
            if hasattr(module, "__code__"):
                return inspect.getsource(module)
            elif hasattr(module, "__result__") and callable(module.__result__):
                return inspect.getsource(module.__result__)
            return ""
        except Exception:
            return ""

    def _generate_cache_key(self, code: str, context: Dict[str, Any], strategy_type: str) -> str:
        """生成验证缓存键"""
        key_data = {
            "code_hash": hashlib.md5(code.encode()).hexdigest(),
            "task_type": context.get("task_type"),
            "strategy_type": strategy_type,
            "parameters_hash": hashlib.md5(
                str(sorted(context.get("parameters", {}).items())).encode()
            ).hexdigest(),
        }
        return hashlib.md5(str(key_data).encode()).hexdigest()

    def set_user_allowed_paths(self, paths: List[str]):
        """设置用户允许的路径"""
        self.file_controller.set_user_allowed_paths(paths)

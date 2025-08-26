import re
import ast
from typing import Dict, Any, List
from ..execution.analyzer import DataFlowAnalyzer
from .security_constants import SecurityConstants


class CodeSecurityController:
    """代码安全控制器"""

    def __init__(self, components: Dict[str, Any] = None):
        self.components = components
        self.config_manager = self.components.get("config_manager")
        self.security_config = self.config_manager.get_security_config()
        self._i18n_manager = components.get("i18n_manager")

    def validate_code_access(self, code: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """代码安全验证入口"""
        function_params = context.get("function_params", [])
        analyzer = DataFlowAnalyzer(function_params, self.components)

        # 只进行代码相关的危险函数检测
        security_issues = []
        for pattern in SecurityConstants.DANGEROUS_PATTERNS:
            if re.search(pattern, code):
                dangerous_function_message = self._i18n_manager.t(
                    "security.dangerous_function_detected", pattern=pattern
                )
                security_issues.append(dangerous_function_message)

        try:
            tree = ast.parse(code)
            analyzer.visit(tree)

            result = {
                "allowed": len(security_issues) == 0,
                "has_conflicts": len(analyzer.parameter_conflicts) > 0 or len(security_issues) > 0,
                "conflicts": analyzer.parameter_conflicts,
                "meaningful_uses": list(analyzer.meaningful_uses),
                "assignments": analyzer.assignments,
                "api_calls": analyzer.api_calls,
                "dangerous_functions": security_issues,
            }

            # 如果检测到危险函数，将其添加到冲突列表中
            if security_issues:
                for issue in security_issues:
                    result["conflicts"].append(
                        {"type": "security_violation", "description": issue, "severity": "high"}
                    )

            return result

        except Exception as e:
            analysis_failed_message = self._i18n_manager.t("security.analysis_failed", error=str(e))
            return {
                "allowed": len(security_issues) == 0,
                "has_conflicts": len(security_issues) > 0,
                "error": analysis_failed_message,
                "dangerous_functions": security_issues,
                "conflicts": [],
                "meaningful_uses": [],
                "assignments": {},
                "api_calls": [],
            }

    def detect_dangerous_patterns(self, code: str) -> List[str]:
        """检测危险模式"""
        detected_issues = []
        for pattern in SecurityConstants.DANGEROUS_PATTERNS:
            if re.search(pattern, code):
                dangerous_function_message = self._i18n_manager.t(
                    "security.dangerous_function_detected", pattern=pattern
                )
                detected_issues.append(dangerous_function_message)
        return detected_issues

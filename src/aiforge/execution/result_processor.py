import json
import hashlib
from datetime import datetime
from typing import Dict, Any, Tuple
from rich.console import Console

from ..validation.result_validator import ResultValidator
from ..instruction.analyzer import AIForgeInstructionAnalyzer
from .result_formatter import AIForgeResultFormatter


class AIForgeResultProcessor:
    """AIForge 执行结果处理器"""

    def __init__(self, console: Console = None, components: Dict[str, Any] = None):
        self.components = components or {}
        self.formatter = AIForgeResultFormatter(console, components) if console else None
        self.result_validator = ResultValidator(self.components)
        self.expected_output = None
        self._i18n_manager = components.get("i18n_manager")

    def set_expected_output(self, expected_output: Dict[str, Any]):
        """设置预期输出规则"""
        self.expected_output = expected_output

    def basic_execution_check(self, result: Dict[str, Any]) -> bool:
        """基础执行检查"""
        if not result.get("success", False):
            return False

        result_content = result.get("result")
        if result_content is None:
            return False

        if isinstance(result_content, dict):
            status = result_content.get("status")
            if status == "error":
                return False
            elif status == "success":
                return True
            if "error" in result_content or "exception" in result_content:
                return False

        return True

    def validate_execution_result(
        self, result: Dict[str, Any], instruction: str, task_type: str = None, llm_client=None
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """使用智能验证器验证执行结果"""
        # 如果没有预期输出，构建默认的验证规则
        if not self.expected_output:
            default_expected_output = AIForgeInstructionAnalyzer.get_default_expected_output(
                task_type
            )
        else:
            default_expected_output = self.expected_output

        # 统一使用智能验证器进行完整验证
        return self.result_validator.validate_execution_result(
            result, default_expected_output, instruction, task_type or "general", llm_client
        )

    def get_validation_feedback(self, failure_reason: str, validation_details: Dict[str, Any]):
        """获取验证反馈信息"""
        validation_type = validation_details.get("validation_type", "unknown")

        # 构建简化的反馈结构
        if validation_type == "execution_error":
            feedback = {
                "type": "execution_error",
                "message": failure_reason,
                "suggestion": self._i18n_manager.t(
                    "result_processor.suggestions.check_syntax_logic"
                ),
            }
        elif validation_type == "ai_deep":
            feedback = {
                "type": "ai_validation_failed",
                "message": failure_reason,
                "suggestion": self._i18n_manager.t("result_processor.suggestions.regenerate_code"),
            }
        elif validation_type in ["empty_data", "missing_data", "missing_field"]:
            feedback = {
                "type": "data_validation_failed",
                "message": failure_reason,
                "suggestion": self._i18n_manager.t("result_processor.suggestions.check_data_logic"),
            }
        elif validation_type == "local_basic":
            feedback = {
                "type": "basic_validation_failed",
                "message": failure_reason,
                "suggestion": self._i18n_manager.t(
                    "result_processor.suggestions.check_execution_structure"
                ),
            }
        elif validation_type == "local_business":
            feedback = {
                "type": "business_validation_failed",
                "message": failure_reason,
                "suggestion": self._i18n_manager.t(
                    "result_processor.suggestions.check_business_logic"
                ),
            }
        else:
            feedback = {
                "type": "validation_failed",
                "message": failure_reason,
                "suggestion": self._i18n_manager.t(
                    "result_processor.suggestions.check_code_format"
                ),
            }

        return json.dumps(feedback, ensure_ascii=False)

    def get_intelligent_feedback(self, result: Dict[str, Any]):
        """返回代码执行错误的JSON反馈"""
        error_info = result.get("error", "")

        # 检查是否为系统级错误
        system_errors = [
            self._i18n_manager.t("result_processor.system_errors.execution_timeout"),
            "Permission denied",
            "Access denied",
        ]

        if any(sys_err in error_info for sys_err in system_errors):
            # 系统级错误不发送给 AI，直接记录日志
            return None

        # 构建简化的错误反馈
        feedback = {
            "type": "execution_error",
            "message": self._i18n_manager.t(
                "result_processor.messages.execution_failed", error=error_info
            ),
            "suggestion": self._i18n_manager.t(
                "result_processor.suggestions.check_syntax_variables"
            ),
        }

        return json.dumps(feedback, ensure_ascii=False)

    def process_execution_result(self, result_content, instruction: str, task_type: str = None):
        """后处理执行结果，强制标准化格式"""
        task_type = task_type or "general"

        if not isinstance(result_content, dict):
            # 区分执行失败和空数据
            is_empty_data = isinstance(result_content, list) and len(result_content) == 0

            result_content = {
                "data": result_content,
                "status": "success",  # 代码执行成功，即使数据为空
                "summary": (
                    self._i18n_manager.t("result_processor.summaries.no_data")
                    if is_empty_data
                    else self._i18n_manager.t("result_processor.summaries.execution_complete")
                ),
                "metadata": {
                    "timestamp": datetime.now().isoformat(),
                    "task_type": task_type,
                    "auto_wrapped": True,
                },
            }
        else:
            result_content.setdefault("status", "success")
            result_content.setdefault(
                "summary", self._i18n_manager.t("result_processor.summaries.operation_complete")
            )
            result_content.setdefault("metadata", {})
            result_content["metadata"].update(
                {
                    "timestamp": datetime.now().isoformat(),
                    "task_type": task_type,
                    "instruction_hash": hashlib.md5(instruction.encode()).hexdigest(),
                }
            )

        if self.formatter:
            processed_result = self.formatter.format_task_type_result(result_content, task_type)
            return processed_result
        return result_content

    def validate_cached_result(
        self, result: Dict[str, Any], standardized_instruction: Dict[str, Any]
    ) -> bool:
        """严格的缓存结果验证"""
        # 严格的格式验证
        if not AIForgeResultProcessor.validate_result_format(result):
            return False

        # 严格的状态检查
        if isinstance(result, dict):
            status = result.get("status")
            if status != "success":
                return False

            result_data = result.get("result", {})
            if isinstance(result_data, dict):
                if (
                    "error" in result_data
                    or "exception" in result_data
                    or "failed" in str(result_data).lower()
                    or "traceback" in str(result_data).lower()
                ):
                    return False

        # 严格的预期输出验证
        expected_output = standardized_instruction.get("expected_output")
        if expected_output:
            return AIForgeResultProcessor.strict_expected_output_validation(result, expected_output)

        # 严格的数据完整性检查
        if not AIForgeResultProcessor.strict_data_integrity_check(result):
            return False

        return True

    @staticmethod
    def validate_result_format(result: Any) -> bool:
        """验证结果是否符合标准格式"""
        if not isinstance(result, dict):
            return False

        required_fields = ["data", "status", "summary", "metadata"]
        if not all(field in result for field in required_fields):
            return False

        metadata = result.get("metadata", {})
        if not isinstance(metadata, dict):
            return False

        required_metadata = ["timestamp", "task_type"]
        if not all(field in metadata for field in required_metadata):
            return False

        return True

    @staticmethod
    def strict_expected_output_validation(
        result: Dict[str, Any], expected_output: Dict[str, Any]
    ) -> bool:
        """严格的预期输出验证"""
        from ..strategies.semantic_field_strategy import SemanticFieldStrategy

        data = result.get("data", [])
        if not isinstance(data, list) or len(data) == 0:
            return False

        required_fields = expected_output.get("required_fields", [])
        if required_fields and len(data) > 0:
            first_item = data[0]
            if not isinstance(first_item, dict):
                return False

            # 使用语义字段策略进行字段映射验证
            field_processor = SemanticFieldStrategy()
            for field in required_fields:
                # 查找语义匹配的字段
                matched_field = field_processor._find_best_source_field(first_item, field)
                if matched_field not in first_item:
                    return False

        # 验证非空字段
        validation_rules = expected_output.get("validation_rules", {})
        non_empty_fields = validation_rules.get("non_empty_fields", [])
        field_processor = SemanticFieldStrategy()

        for item in data:
            if isinstance(item, dict):
                for field in non_empty_fields:
                    matched_field = field_processor._find_best_source_field(item, field)
                    if matched_field in item:
                        value = item[matched_field]
                        if (
                            value is None
                            or value == ""
                            or (isinstance(value, (list, dict)) and len(value) == 0)
                        ):
                            return False

        return True

    @staticmethod
    def strict_data_integrity_check(result: Dict[str, Any]) -> bool:
        """严格的数据完整性检查"""
        # 统一从标准位置获取数据
        data = result.get("data")
        if data is None:
            return False

        if not isinstance(data, list):
            return False

        if len(data) == 0:
            return False

        # 检查数据项的完整性
        for i, item in enumerate(data):
            if not isinstance(item, dict):
                return False

            # 检查是否包含错误指示符
            item_str = str(item).lower()
            error_indicators = ["error", "failed", "exception", "traceback"]
            if any(indicator in item_str for indicator in error_indicators):
                return False

        return True

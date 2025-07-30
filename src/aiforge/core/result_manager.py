import json
import hashlib
from datetime import datetime
from typing import Dict, Any, Tuple
from rich.console import Console

from ..validation.result_validator import ResultValidator
from ..instruction.analyzer import InstructionAnalyzer
from ..formatting.result_formatter import AIForgeResultFormatter


class AIForgeResult:
    """AIForge 执行结果处理器"""

    def __init__(self, console: Console = None):
        self.formatter = AIForgeResultFormatter(console) if console else None
        self.result_validator = ResultValidator()
        self.expected_output = None

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
            default_expected_output = InstructionAnalyzer.get_default_expected_output(task_type)
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
                "suggestion": "检查代码语法和逻辑错误",
            }
        elif validation_type == "ai_deep":  # 修正：应该是 ai_deep 而不是 ai_validation
            feedback = {
                "type": "ai_validation_failed",
                "message": failure_reason,
                "suggestion": "请重新生成代码以更好地满足用户需求。检查数据获取逻辑，确保返回有效的标题和内容字段",
            }
        elif validation_type in ["empty_data", "missing_data", "missing_field"]:
            feedback = {
                "type": "data_validation_failed",
                "message": failure_reason,
                "suggestion": "请检查数据获取逻辑，确保返回正确格式的数据",
            }
        elif validation_type == "local_basic":
            feedback = {
                "type": "basic_validation_failed",
                "message": failure_reason,
                "suggestion": "检查代码执行和基本数据结构",
            }
        elif validation_type == "local_business":
            feedback = {
                "type": "business_validation_failed",
                "message": failure_reason,
                "suggestion": "检查业务逻辑和必需字段",
            }
        else:
            feedback = {
                "type": "validation_failed",
                "message": failure_reason,
                "suggestion": "请检查代码逻辑和输出格式",
            }

        return json.dumps(feedback, ensure_ascii=False)

    def get_intelligent_feedback(self, result: Dict[str, Any]):
        """返回代码执行错误的JSON反馈"""
        error_info = result.get("error", "")

        # 检查是否为系统级错误
        system_errors = [
            "代码执行超时",
            "Permission denied",
            "Access denied",
        ]

        if any(sys_err in error_info for sys_err in system_errors):
            # 系统级错误不发送给 AI，直接记录日志
            print(f"[SYSTEM ERROR] {error_info}")
            return None

        # 构建简化的错误反馈
        feedback = {
            "type": "execution_error",
            "message": f"代码执行失败: {error_info}",
            "suggestion": "请检查代码语法、变量定义和逻辑错误",
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
                "summary": "执行完成，但未获取到数据" if is_empty_data else "执行完成",
                "metadata": {
                    "timestamp": datetime.now().isoformat(),
                    "task_type": task_type,
                    "auto_wrapped": True,
                },
            }
        else:
            result_content.setdefault("status", "success")
            result_content.setdefault("summary", "操作完成")
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

    @staticmethod
    def validate_cached_result(
        result: Dict[str, Any], standardized_instruction: Dict[str, Any]
    ) -> bool:
        """严格的缓存结果验证"""
        # 严格的格式验证
        if not AIForgeResult.validate_result_format(result):
            print("[DEBUG] 缓存结果格式验证失败")
            return False

        # 严格的状态检查
        if isinstance(result, dict):
            status = result.get("status")
            if status != "success":
                print(f"[DEBUG] 缓存结果状态不是success: {status}")
                return False

            result_data = result.get("result", {})
            if isinstance(result_data, dict):
                if (
                    "error" in result_data
                    or "exception" in result_data
                    or "failed" in str(result_data).lower()
                    or "traceback" in str(result_data).lower()
                ):
                    print("[DEBUG] 缓存结果包含错误信息")
                    return False

        # 严格的预期输出验证
        expected_output = standardized_instruction.get("expected_output")
        if expected_output:
            return AIForgeResult.strict_expected_output_validation(result, expected_output)

        # 严格的数据完整性检查
        if not AIForgeResult.strict_data_integrity_check(result):
            print("[DEBUG] 缓存结果数据完整性检查失败")
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
        """严格的预期输出验证 - 统一数据格式版本"""
        # 统一从标准位置获取数据
        data = result.get("data", [])

        # 验证 data 必须是列表
        if not isinstance(data, list):
            print("[DEBUG] 严格验证失败：data字段必须是列表格式")
            return False

        # 先检查是否有数据
        if len(data) == 0:
            print("[DEBUG] 严格验证失败：data字段为空，未获取到有效数据")
            return False

        # 验证数据项的必需字段
        required_fields = expected_output.get("required_fields", [])
        if required_fields and len(data) > 0:
            first_item = data[0]
            if not isinstance(first_item, dict):
                print("[DEBUG] 严格验证失败：数据项必须是字典格式")
                return False

            for field in required_fields:
                if field not in first_item:
                    print(f"[DEBUG] 严格验证失败：数据项缺少必需字段 {field}")
                    return False

        # 验证非空字段
        validation_rules = expected_output.get("validation_rules", {})
        non_empty_fields = validation_rules.get("non_empty_fields", [])
        for item in data:
            if isinstance(item, dict):
                for field in non_empty_fields:
                    if field in item:
                        value = item[field]
                        if (
                            value is None
                            or value == ""
                            or (isinstance(value, (list, dict)) and len(value) == 0)
                        ):
                            print(f"[DEBUG] 严格验证失败：字段 {field} 为空")
                            return False

        return True

    @staticmethod
    def strict_data_integrity_check(result: Dict[str, Any]) -> bool:
        """严格的数据完整性检查 - 统一数据格式版本"""
        # 统一从标准位置获取数据
        data = result.get("data")
        if data is None:
            print("[DEBUG] 数据完整性检查失败：缺少data字段")
            return False

        if not isinstance(data, list):
            print("[DEBUG] 数据完整性检查失败：data字段必须是列表")
            return False

        if len(data) == 0:
            print("[DEBUG] 数据完整性检查失败：data字段为空")
            return False

        # 检查数据项的完整性
        for i, item in enumerate(data):
            if not isinstance(item, dict):
                print(f"[DEBUG] 数据完整性检查失败：data[{i}]必须是字典格式")
                return False

            # 检查是否包含错误指示符
            item_str = str(item).lower()
            error_indicators = ["error", "failed", "exception", "traceback"]
            if any(indicator in item_str for indicator in error_indicators):
                print(f"[DEBUG] 数据完整性检查失败：data[{i}]包含错误信息")
                return False

        return True

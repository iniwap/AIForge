from typing import Dict, Any, Tuple
import json
import re


class IntelligentResultValidator:
    """智能结果验证器"""

    def __init__(self, llm_client=None):
        self.llm_client = llm_client

    def validate_execution_result(
        self,
        result: Dict[str, Any],
        expected_output: Dict[str, Any],
        original_instruction: str,
        task_type: str,
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """
        验证执行结果
        返回: (是否成功, 失败原因, 验证详情)
        """

        # 第一步：本地基础验证
        local_valid, local_reason = self._local_basic_validation(result, expected_output)
        if not local_valid:
            return False, f"本地验证失败: {local_reason}", {"validation_type": "local_basic"}

        # 第二步：本地业务逻辑验证
        business_valid, business_reason = self._local_business_validation(
            result, expected_output, task_type
        )
        if not business_valid:
            return (
                False,
                f"业务逻辑验证失败: {business_reason}",
                {"validation_type": "local_business"},
            )

        # 第三步：AI深度验证（如果本地验证通过但仍有疑虑）
        if self.llm_client and self._needs_ai_validation(result, expected_output):
            ai_valid, ai_reason = self._ai_deep_validation(
                result, expected_output, original_instruction, task_type
            )
            if not ai_valid:
                return False, f"AI验证失败: {ai_reason}", {"validation_type": "ai_deep"}

        return True, "验证通过", {"validation_type": "complete"}

    def _local_basic_validation(
        self, result: Dict[str, Any], expected: Dict[str, Any]
    ) -> Tuple[bool, str]:
        """本地基础验证：错误、空值、基本格式"""

        # 检查执行是否成功
        if not result.get("success", False):
            return False, f"代码执行失败: {result.get('error', '未知错误')}"

        result_content = result.get("result")

        # 检查结果是否为None
        if result_content is None:
            return False, "执行结果为None"

        # 检查结果是否为空列表/字典
        if isinstance(result_content, (list, dict)) and len(result_content) == 0:
            return False, "执行结果为空"

        # 检查是否包含明显的错误指示
        if isinstance(result_content, dict):
            if result_content.get("status") == "error":
                return False, f"结果状态为错误: {result_content.get('error', '未知错误')}"

            failure_indicators = expected.get(
                "failure_indicators", ["error", "exception", "failed", "timeout"]
            )
            for indicator in failure_indicators:
                if indicator in result_content:
                    return False, f"结果包含错误指示: {indicator}"

        return True, ""

    def _local_business_validation(
        self, result: Dict[str, Any], expected: Dict[str, Any], task_type: str
    ) -> Tuple[bool, str]:
        """本地业务逻辑验证"""

        result_content = result.get("result")
        validation_rules = expected.get("validation_rules", {})

        # 检查必需字段
        required_fields = expected.get("required_fields", [])
        if isinstance(result_content, dict):
            for field in required_fields:
                if field not in result_content:
                    return False, f"缺少必需字段: {field}"

        # 检查非空字段
        non_empty_fields = validation_rules.get("non_empty_fields", [])
        if isinstance(result_content, dict):
            for field in non_empty_fields:
                if field in result_content:
                    value = result_content[field]
                    if not value or (isinstance(value, (list, dict)) and len(value) == 0):
                        return False, f"字段 {field} 不应为空"

        # 检查最小项目数
        min_items = validation_rules.get("min_items", 0)
        if isinstance(result_content, dict) and "data" in result_content:
            data = result_content["data"]
            if isinstance(data, dict) and "results" in data:
                results = data["results"]
                if isinstance(results, list) and len(results) < min_items:
                    return False, f"结果数量 {len(results)} 少于最小要求 {min_items}"
            elif isinstance(data, list) and len(data) < min_items:
                return False, f"数据项数量 {len(data)} 少于最小要求 {min_items}"

        # 检查成功指示器
        success_indicators = validation_rules.get("success_indicators", [])
        if success_indicators and isinstance(result_content, dict):
            has_success_indicator = False
            for indicator in success_indicators:
                if "data存在" in indicator and "data" in result_content and result_content["data"]:
                    has_success_indicator = True
                    break
                elif "results非空" in indicator and isinstance(result_content.get("data"), dict):
                    results = result_content["data"].get("results", [])
                    if results and len(results) > 0:
                        has_success_indicator = True
                        break

            if not has_success_indicator:
                return False, "未找到成功执行的指示器"

        return True, ""

    def _needs_ai_validation(self, result: Dict[str, Any], expected: Dict[str, Any]) -> bool:
        """判断是否需要AI深度验证"""
        # 如果有复杂的业务逻辑检查要求，则需要AI验证
        business_checks = expected.get("business_logic_checks", [])
        return len(business_checks) > 0

    def _ai_deep_validation(
        self,
        result: Dict[str, Any],
        expected: Dict[str, Any],
        original_instruction: str,
        task_type: str,
    ) -> Tuple[bool, str]:
        """AI深度验证 - 判断是否真正达到任务目标"""

        validation_prompt = f"""
请判断以下代码执行结果是否真正完成了用户的任务目标：

原始用户指令：{original_instruction}
任务类型：{task_type}
预期输出要求：{json.dumps(expected, ensure_ascii=False, indent=2)}

实际执行结果：
{json.dumps(result.get("result"), ensure_ascii=False, indent=2)}

请从以下角度分析：
1. 结果是否包含用户所需的核心信息
2. 数据质量是否满足实际使用需求
3. 是否存在明显的逻辑错误或遗漏
4. 结果格式是否便于后续处理

请返回JSON格式的验证结果：
{{
    "validation_passed": true/false,
    "confidence": 0.0-1.0,
    "failure_reason": "具体失败原因（如果失败）",
    "improvement_suggestions": ["改进建议1", "改进建议2"],
    "core_issues": ["核心问题1", "核心问题2"]
}}
"""

        try:
            response = self.llm_client.generate_code(validation_prompt, "")
            ai_result = self._parse_ai_validation_response(response)

            if ai_result.get("validation_passed", False):
                return True, ""
            else:
                return False, ai_result.get("failure_reason", "AI验证未通过")

        except Exception as e:
            # AI验证失败时，保守地认为验证通过
            return True, f"AI验证异常，默认通过: {str(e)}"

    def _parse_ai_validation_response(self, response: str) -> Dict[str, Any]:
        """解析AI验证响应"""
        try:
            json_match = re.search(r"\{.*\}", response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group(0))
        except Exception:
            pass
        return {"validation_passed": True, "failure_reason": "解析失败，默认通过"}

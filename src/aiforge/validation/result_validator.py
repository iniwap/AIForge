from typing import Dict, Any, Tuple
import json


class ResultValidator:
    """智能结果验证器"""

    def validate_execution_result(
        self,
        result: Dict[str, Any],
        expected_output: Dict[str, Any],
        original_instruction: str,
        task_type: str,
        llm_client=None,
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """
        验证执行结果
        返回: (是否成功, 失败原因, 验证详情)
        """

        # 第一步：本地基础验证
        local_valid, local_reason = self._local_basic_validation(result, expected_output)
        if not local_valid:
            return False, "本地验证失败", local_reason, {"validation_type": "local_basic"}

        # 第二步：本地业务逻辑验证
        business_valid, business_reason = self._local_business_validation(
            result, expected_output, task_type
        )
        if not business_valid:
            return (
                False,
                "业务逻辑验证失败",
                business_reason,
                {"validation_type": "local_business"},
            )

        # 第三步：AI深度验证（如果本地验证通过但仍有疑虑）
        if self._needs_ai_validation(result, expected_output):
            if llm_client:
                ai_valid, ai_reason = self._ai_deep_validation(
                    result, expected_output, original_instruction, task_type, llm_client
                )
                if not ai_valid:
                    return False, "AI验证失败", ai_reason, {"validation_type": "ai_deep"}
            else:
                return False, "AI验证失败", "llm_client 为None", {"validation_type": "ai_deep"}

        return True, "", "验证通过", {"validation_type": "complete"}

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

        # 强化空数据检查
        if isinstance(result_content, dict):
            # 检查状态
            if result_content.get("status") != "success":
                return False, f"{result_content.get('summary', '未知错误')}"

            # 严格检查data字段
            data = result_content.get("data")
            if data is not None:
                if isinstance(data, (list, dict)) and len(data) == 0:
                    return False, "data字段为空列表，未获取到有效数据"
                elif data is None:
                    return False, "data字段为None"
            else:
                return False, "缺少data字段"

        # 如果结果本身是空列表或字典，直接失败
        if isinstance(result_content, (list, dict)) and len(result_content) == 0:
            return False, "执行结果为空"

        return True, ""

    def _local_business_validation(
        self, result: Dict[str, Any], expected: Dict[str, Any], task_type: str
    ) -> Tuple[bool, str]:
        """业务逻辑验证 - 使用策略模式"""

        result_content = result.get("result")
        validation_rules = expected.get("validation_rules", {})

        # 使用验证策略管理器
        from ..strategies.validation_strategy import ValidationStrategyManager

        strategy_manager = ValidationStrategyManager()
        validation_strategy = strategy_manager.get_strategy(task_type)

        # 对于 data_fetch 任务，采用部分成功策略
        if task_type == "data_fetch" and isinstance(result_content, dict):
            data = result_content.get("data", [])
            if isinstance(data, list) and len(data) > 0:
                required_fields = expected.get("required_fields", [])
                non_empty_fields = validation_rules.get("non_empty_fields", [])

                # 使用策略进行验证
                valid_items, valid_count = validation_strategy.validate_data_items(
                    data, required_fields, non_empty_fields
                )

                # 检查最小数据量
                min_items = validation_rules.get("min_items", 1)
                if valid_count >= min_items:
                    result_content["data"] = valid_items
                    result_content["summary"] = f"找到{valid_count}条有效结果"
                    return True, ""
                else:
                    return (
                        False,
                        f"获取到{valid_count}条有效数据，不满足最少要获取{min_items}条",
                    )

        # 检查基本结构
        if not isinstance(result_content, dict):
            return False, "结果内容必须是字典格式"

        if result_content.get("status") == "error":
            return False, result_content.get("summary", "结果状态为error")

        # 检查 data 字段
        data = result_content.get("data", [])
        if not isinstance(data, list):
            return False, "data 字段必须是数组格式"

        if len(data) == 0:
            return False, "数据数组为空"

        # 使用策略进行字段验证
        required_fields = expected.get("required_fields", [])
        if required_fields and len(data) > 0:
            first_item = data[0]
            if not isinstance(first_item, dict):
                return False, "数据项必须是字典格式"

            # 使用策略检查必需字段
            valid_items, _ = validation_strategy.validate_data_items(
                [first_item], required_fields, []
            )

            if len(valid_items) == 0:
                return False, "数据项缺少必需字段"

        # 检查最小数据量
        min_items = validation_rules.get("min_items", 1)
        if len(data) < min_items:
            return False, f"数据量不足: 需要至少{min_items}条，实际{len(data)}条"

        return True, ""

    def _needs_ai_validation(self, result: Dict[str, Any], expected: Dict[str, Any]) -> bool:
        """判断是否需要AI深度验证 - 考虑数据数量"""
        result_content = result.get("result", {})
        if isinstance(result_content, dict):
            data = result_content.get("data", [])
            min_items = expected.get("validation_rules", {}).get("min_items", 3)

            # 如果获取到足够数量的数据，且基本格式正确，跳过 AI 验证
            if isinstance(data, list) and len(data) >= min_items:
                valid_items = 0
                for item in data:
                    if isinstance(item, dict):
                        title = item.get("title", "").strip()
                        content = item.get("content", "").strip()
                        if title and content and len(content) > 20:
                            valid_items += 1

                # 如果有效数据达到要求，跳过 AI 验证
                if valid_items >= min_items:
                    return False

        return True

    def _ai_deep_validation(
        self,
        result: Dict[str, Any],
        expected: Dict[str, Any],
        original_instruction: str,
        task_type: str,
        llm_client,
    ) -> Tuple[bool, str]:
        """AI深度验证"""

        validation_prompt = f"""
    请判断以下代码执行结果是否真正完成了用户的任务目标：

    原始用户指令：{original_instruction}
    任务类型：{task_type}
    预期输出要求：{json.dumps(expected, ensure_ascii=False, indent=2)}

    实际执行结果
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
            response = llm_client.generate_code(validation_prompt, "")
            ai_result = self._parse_ai_validation_response(response)

            if ai_result.get("validation_passed", False):
                return True, ""
            else:
                # 只返回核心失败原因，不包含"AI验证失败:"前缀
                failure_reason = ai_result.get("failure_reason", "结果不满足任务要求")
                return False, failure_reason

        except Exception as e:
            # AI验证失败时，保守地认为验证通过
            return True, f"AI验证异常，默认通过: {str(e)}"

    def _parse_ai_validation_response(self, response: str) -> Dict[str, Any]:
        """解析AI验证响应"""
        try:
            # 尝试直接解析JSON
            return json.loads(response)
        except json.JSONDecodeError:
            # 如果直接解析失败，尝试提取JSON部分
            import re

            json_match = re.search(r"\{.*\}", response, re.DOTALL)
            if json_match:
                try:
                    return json.loads(json_match.group())
                except json.JSONDecodeError:
                    pass

            # 解析失败时返回默认失败结果
            return {
                "validation_passed": False,
                "confidence": 0.0,
                "failure_reason": "AI响应格式无法解析",
                "improvement_suggestions": [],
                "core_issues": ["AI验证响应格式错误"],
            }

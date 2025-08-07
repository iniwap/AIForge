from typing import Dict, Any, Tuple
import json


class ResultValidator:
    """智能结果验证器"""

    def __init__(self, components: Dict[str, Any] = None):
        self.components = components or {}
        self._i18n_manager = self.components.get("i18n_manager")

    def validate_execution_result(
        self,
        result: Dict[str, Any],
        expected_output: Dict[str, Any],
        original_instruction: str,
        task_type: str,
        llm_client=None,
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """验证执行结果"""

        # 第一步：本地基础验证
        local_valid, local_reason = self._local_basic_validation(result, expected_output)
        if not local_valid:
            failure_reason = self._i18n_manager.t("validation.local_basic_failed")
            return False, failure_reason, local_reason, {"validation_type": "local_basic"}

        # 第二步：本地业务逻辑验证
        business_valid, business_reason = self._local_business_validation(
            result, expected_output, task_type
        )
        if not business_valid:
            failure_reason = self._i18n_manager.t("validation.business_logic_failed")
            return (
                False,
                failure_reason,
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
                    failure_reason = self._i18n_manager.t("validation.ai_validation_failed")
                    return False, failure_reason, ai_reason, {"validation_type": "ai_deep"}
            else:
                failure_reason = self._i18n_manager.t("validation.ai_validation_failed")
                llm_client_none_reason = self._i18n_manager.t("validation.llm_client_none")
                return False, failure_reason, llm_client_none_reason, {"validation_type": "ai_deep"}

        success_message = self._i18n_manager.t("validation.validation_passed")
        return True, "", success_message, {"validation_type": "complete"}

    def _local_basic_validation(
        self, result: Dict[str, Any], expected: Dict[str, Any]
    ) -> Tuple[bool, str]:
        """本地基础验证：错误、空值、基本格式"""

        # 检查执行是否成功
        if not result.get("success", False):
            error_message = self._i18n_manager.t(
                "validation.code_execution_failed",
                error=result.get("error", self._i18n_manager.t("validation.unknown_error")),
            )
            return False, error_message

        result_content = result.get("result")

        # 检查结果是否为None
        if result_content is None:
            return False, self._i18n_manager.t("validation.execution_result_none")

        # 强化空数据检查
        if isinstance(result_content, dict):
            # 检查状态
            if result_content.get("status") != "success":
                return False, result_content.get(
                    "summary", self._i18n_manager.t("validation.unknown_error")
                )

            # 严格检查data字段
            data = result_content.get("data")
            if data is not None:
                if isinstance(data, (list, dict)) and len(data) == 0:
                    return False, self._i18n_manager.t("validation.data_field_empty")
                elif data is None:
                    return False, self._i18n_manager.t("validation.data_field_none")
            else:
                return False, self._i18n_manager.t("validation.missing_data_field")

        # 如果结果本身是空列表或字典，直接失败
        if isinstance(result_content, (list, dict)) and len(result_content) == 0:
            return False, self._i18n_manager.t("validation.execution_result_empty")

        return True, ""

    def _local_business_validation(
        self, result: Dict[str, Any], expected: Dict[str, Any], task_type: str
    ) -> Tuple[bool, str]:
        """业务逻辑验证"""

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
                    summary_message = self._i18n_manager.t(
                        "validation.found_valid_results", count=valid_count
                    )
                    result_content["summary"] = summary_message
                    return True, ""
                else:
                    insufficient_data_message = self._i18n_manager.t(
                        "validation.insufficient_valid_data",
                        valid_count=valid_count,
                        min_items=min_items,
                    )
                    return False, insufficient_data_message

        # 检查基本结构
        if not isinstance(result_content, dict):
            return False, self._i18n_manager.t("validation.result_must_be_dict")

        if result_content.get("status") == "error":
            return False, result_content.get(
                "summary", self._i18n_manager.t("validation.result_status_error")
            )

        # 检查 data 字段
        data = result_content.get("data", [])
        if not isinstance(data, list):
            return False, self._i18n_manager.t("validation.data_must_be_array")

        if len(data) == 0:
            return False, self._i18n_manager.t("validation.data_array_empty")

        # 使用策略进行字段验证
        required_fields = expected.get("required_fields", [])
        if required_fields and len(data) > 0:
            first_item = data[0]
            if not isinstance(first_item, dict):
                return False, self._i18n_manager.t("validation.data_item_must_be_dict")

            # 使用策略检查必需字段
            valid_items, _ = validation_strategy.validate_data_items(
                [first_item], required_fields, []
            )

            if len(valid_items) == 0:
                return False, self._i18n_manager.t("validation.data_item_missing_required_fields")

        # 检查最小数据量
        min_items = validation_rules.get("min_items", 1)
        if len(data) < min_items:
            insufficient_quantity_message = self._i18n_manager.t(
                "validation.insufficient_data_quantity", min_items=min_items, actual=len(data)
            )
            return False, insufficient_quantity_message

        return True, ""

    def _needs_ai_validation(
        self,
        result: Dict[str, Any],
        expected: Dict[str, Any],
        original_instruction: str = None,
        llm_client=None,
    ) -> bool:
        """判断是否需要AI深度验证"""
        result_content = result.get("result", {})
        if isinstance(result_content, dict):
            data = result_content.get("data", [])
            min_items = expected.get("validation_rules", {}).get("min_items", 1)

            # 现有的数据质量检查
            if isinstance(data, list) and len(data) >= min_items:
                valid_items = 0
                for item in data:
                    if isinstance(item, dict):
                        title = item.get("title", "").strip()
                        content = item.get("content", "").strip()
                        if title and content and len(content) > 20:
                            valid_items += 1

                # 语义相关性初步检查
                if valid_items >= min_items and original_instruction and llm_client:
                    semantic_relevance = self._check_semantic_relevance(
                        original_instruction, data[:2], llm_client  # 为了节省时间，只检查前2条
                    )
                    if semantic_relevance < 0.3:  # 相关性阈值
                        return True  # 需要AI深度验证

                # 如果有效数据达到要求且语义相关，跳过 AI 验证
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

        # 构建本地化的验证提示词
        validation_prompt_template = self._i18n_manager.t(
            "validation.ai_validation_prompt_template"
        )
        analysis_dimensions = self._i18n_manager.t("validation.analysis_dimensions")
        json_format_instruction = self._i18n_manager.t("validation.json_format_instruction")

        validation_prompt = validation_prompt_template.format(
            original_instruction=original_instruction,
            task_type=task_type,
            expected_output=json.dumps(expected, ensure_ascii=False, indent=2),
            actual_result=json.dumps(result.get("result"), ensure_ascii=False, indent=2),
            analysis_dimensions=analysis_dimensions,
            json_format_instruction=json_format_instruction,
        )

        try:
            response = llm_client.generate_code(validation_prompt, "")
            ai_result = self._parse_ai_validation_response(response)

            if ai_result.get("validation_passed", False):
                return True, ""
            else:
                # 只返回核心失败原因，不包含"AI验证失败:"前缀
                failure_reason = ai_result.get(
                    "failure_reason",
                    self._i18n_manager.t("validation.result_not_meet_requirements"),
                )
                return False, failure_reason

        except Exception as e:
            # AI验证失败时，保守地认为验证通过
            ai_exception_message = self._i18n_manager.t(
                "validation.ai_validation_exception", error=str(e)
            )
            return True, ai_exception_message

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
                "failure_reason": self._i18n_manager.t("validation.ai_response_parse_failed"),
                "improvement_suggestions": [],
                "core_issues": [self._i18n_manager.t("validation.ai_response_format_error")],
            }

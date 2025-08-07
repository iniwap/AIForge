from typing import Optional, Dict, Any


class AIForgePrompt:
    """AIForge 提示词生成器"""

    def __init__(self, components: Dict[str, Any]):
        """初始化提示词生成器"""
        self.components = components
        self._i18n_manager = components.get("i18n_manager")

    def _get_task_specific_format(
        self, task_type: str, expected_output: Dict[str, Any] = None
    ) -> str:
        """获取任务特定格式，支持国际化"""

        if not expected_output:
            # 使用i18n提取的原始内容
            format_template = self._i18n_manager.t("output_format.default")
            important_note = self._i18n_manager.t("output_format.status_note")
            return f"{format_template}\n\n{important_note}"

        # 基于AI分析的预期输出规则生成格式
        required_fields = expected_output.get("required_fields", [])
        validation_rules = expected_output.get("validation_rules", {})
        non_empty_fields = validation_rules.get("non_empty_fields", [])

        # 构建data字段示例
        data_example = {}
        for field in required_fields:
            data_example[field] = f"{field}_value"

        format_header = self._i18n_manager.t("output_format.ai_analysis_header")
        required_fields_label = self._i18n_manager.t("output_format.required_fields_label")
        non_empty_fields_label = self._i18n_manager.t("output_format.non_empty_fields_label")
        important_note = self._i18n_manager.t("output_format.status_note")

        # 使用i18n的状态和摘要占位符
        status_placeholder = self._i18n_manager.t("format_templates.status_success_error")
        summary_placeholder = self._i18n_manager.t("format_templates.summary_placeholder")

        format_str = f"""
    {format_header}
    __result__ = {{
        "data": [{data_example},...],
        "status": "{status_placeholder}",
        "summary": "{summary_placeholder}",
        "metadata": {{"timestamp": "...", "task_type": "{task_type}"}}
    }}

    {required_fields_label} {', '.join(required_fields)}
    {non_empty_fields_label} {', '.join(non_empty_fields)}
    {important_note}
    """
        return format_str

    def get_base_aiforge_prompt(self, optimize_tokens: bool = True) -> str:
        """生成基础的AIForge系统提示"""

        # 使用i18n提取的原始内容
        base_header = self._i18n_manager.t("base.header")
        code_generation_header = self._i18n_manager.t("base.code_generation_header")
        execution_header = self._i18n_manager.t("base.execution_header")
        execution_guidance = self._i18n_manager.t("base.execution_guidance")

        code_rules = [
            self._i18n_manager.t("code_rules.executable"),
            self._i18n_manager.t("code_rules.format"),
            self._i18n_manager.t("code_rules.error_handling"),
        ]

        if optimize_tokens:
            code_rules.extend(
                [
                    self._i18n_manager.t("code_rules.minimal"),
                    self._i18n_manager.t("code_rules.variables"),
                ]
            )

        code_rule_text = "\n".join(code_rules)

        # 保持原有的格式结构
        base_prompt = f"""
{base_header}

{code_generation_header}
{code_rule_text}

{execution_header}
{execution_guidance}
"""
        return base_prompt

    def _get_enhanced_aiforge_prompt_with_validation(
        self,
        optimize_tokens: bool = True,
        task_type: Optional[str] = None,
        parameters: Optional[Dict[str, Any]] = None,
        expected_output: Optional[Dict[str, Any]] = None,
    ) -> str:
        """生成带通用参数验证约束的增强系统提示"""

        base_prompt = self.get_base_aiforge_prompt(optimize_tokens)

        execution_guidance = ""
        if parameters:
            param_analysis = self._analyze_parameters_for_execution(parameters)

            param_header = self._i18n_manager.t("parameterized.header")
            analysis_header = self._i18n_manager.t("parameterized.analysis_function")
            param_desc_header = self._i18n_manager.t("parameterized.param_description")
            call_instruction = self._i18n_manager.t("parameterized.call_instruction")
            usage_rules_header = self._i18n_manager.t("parameterized.usage_rules_header")
            usage_rules = self._i18n_manager.t("parameterized.usage_rules")
            avoid_patterns_header = self._i18n_manager.t("parameterized.avoid_patterns_header")
            avoid_patterns = self._i18n_manager.t("parameterized.avoid_patterns")

            execution_guidance = f"""
{param_header}

{analysis_header}

def execute_task({param_analysis['signature']}):
    '''
    {param_analysis['docstring']}
    '''
    return result_data

{param_desc_header}
{param_analysis['param_docs']}

{call_instruction}
__result__ = execute_task({param_analysis['call_args']})

{usage_rules_header}
{chr(10).join(usage_rules)}

{avoid_patterns_header}
{chr(10).join(avoid_patterns)}
    """

        enhanced_prompt = f"""
{base_prompt}

{execution_guidance}
"""

        # 使用AI分析结果生成格式要求
        enhanced_prompt += f"\n\n{self._get_task_specific_format(task_type, expected_output)}"

        return enhanced_prompt

    def _analyze_parameters_for_execution(self, parameters: Dict[str, Any]) -> Dict[str, str]:
        """分析参数结构，生成执行指导"""
        param_names = []
        param_docs = []
        call_args = []

        for param_name, param_info in parameters.items():
            if isinstance(param_info, dict):
                value = param_info.get("value")
                param_type = param_info.get("type", "str")
                required = param_info.get("required", True)

                # 构建函数签名
                if required and value is not None:
                    param_names.append(param_name)
                    call_args.append(f'"{value}"' if param_type == "str" else str(value))

                # 构建参数文档
                param_docs.append(f"- {param_name} ({param_type})")
            else:
                # 简单参数处理
                param_names.append(param_name)
                call_args.append(
                    f'"{param_info}"' if isinstance(param_info, str) else str(param_info)
                )
                param_docs.append(f"- {param_name}")

        signature = ", ".join(param_names)
        call_signature = ", ".join(call_args)

        docstring = self._i18n_manager.t(
            "parameterized.docstring_template", params=", ".join(param_names)
        )

        return {
            "signature": signature,
            "call_args": call_signature,
            "param_docs": "\n".join(param_docs),
            "docstring": docstring,
        }

    def get_direct_response_prompt(
        self, action: str, standardized_instruction: Dict[str, Any]
    ) -> str:
        """构建直接响应专用提示词"""

        # 使用i18n提取的原始提示词
        base_prompt = self._i18n_manager.t(
            f"direct_response.{action}", default=self._i18n_manager.t("direct_response.default")
        )

        # 保持原有的增强逻辑
        target = standardized_instruction.get("target", "")
        parameters = standardized_instruction.get("parameters", {})
        task_type = standardized_instruction.get("task_type", "")

        # 根据 action 类型选择合适的输出格式（保持原逻辑）
        action_format_mapping = {
            "create": "markdown",
            "translate": "text",
            "summarize": "structured_text",
            "answer": "text",
            "respond": "text",
            "suggest": "structured_text",
            "chat_ai": "text",
        }

        output_format = action_format_mapping.get(action, "text")
        enhanced_sections = []

        # 1. 任务上下文增强
        if target:
            task_target_label = self._i18n_manager.t("direct_response.task_target_label")
            enhanced_sections.append(f"{task_target_label}: {target}")

        # 2. 输出格式指导
        if output_format in ["text", "markdown", "structured_text"]:
            output_req = self._i18n_manager.t(
                f"direct_response.output_requirements.{output_format}"
            )
            task_requirements_label = self._i18n_manager.t(
                "format_templates.task_requirements_label"
            )
            enhanced_sections.append(f"{task_requirements_label} {output_req}")

        # 3. 参数上下文增强
        if parameters:
            param_context = []
            for param_name, param_value in parameters.items():
                if param_value:
                    param_context.append(f"- {param_name}: {param_value}")

            if param_context:
                related_params_label = self._i18n_manager.t("format_templates.related_params_label")
                enhanced_sections.append(f"{related_params_label}\n" + "\n".join(param_context))

        # 4. 任务类型特定指导
        if task_type in ["direct_response", "content_generation", "data_process"]:
            guidance = self._i18n_manager.t(f"direct_response.task_specific_guidance.{task_type}")
            special_requirements_label = self._i18n_manager.t(
                "format_templates.special_requirements_label"
            )
            enhanced_sections.append(f"{special_requirements_label} {guidance}")

        # 组装最终提示词
        enhanced_prompt = base_prompt

        if enhanced_sections:
            task_details_header = self._i18n_manager.t("format_templates.task_details_header")
            enhanced_prompt += f"\n\n{task_details_header}\n" + "\n\n".join(enhanced_sections)

        # 添加限制说明
        limitations = self._i18n_manager.t("direct_response.limitations")
        enhanced_prompt += limitations

        return enhanced_prompt

    def get_enhanced_system_prompt(
        self,
        standardized_instruction: Dict[str, Any],
        optimize_tokens=True,
        original_prompt: str = None,
    ) -> str:
        """基于标准化指令构建通用增强系统提示词"""
        task_type = standardized_instruction.get("task_type", "general")

        # 获取参数信息
        parameters = standardized_instruction.get("required_parameters", {})
        if not parameters:
            parameters = standardized_instruction.get("parameters", {})

        # 直接从标准化指令中获取预期输出规则
        expected_output = standardized_instruction.get("expected_output")

        # 最后的回退：确保有基本的指令参数
        if not parameters:
            parameters = {
                "instruction": {
                    "value": standardized_instruction.get("target", ""),
                    "type": "str",
                    "required": True,
                }
            }

        # 使用通用增强版提示词生成，传递预期输出规则
        enhanced_prompt = self._get_enhanced_aiforge_prompt_with_validation(
            optimize_tokens=optimize_tokens,
            task_type=task_type,
            parameters=parameters,
            expected_output=expected_output,
        )

        if original_prompt:
            original_instruction_label = self._i18n_manager.t(
                "format_templates.original_instruction_supplement"
            )
            enhanced_prompt += f"\n\n{original_instruction_label}\n{original_prompt}"

        return enhanced_prompt

    def get_base_prompt_sections(self) -> Dict[str, str]:
        """构建基础提示词各个部分"""

        # 使用i18n构建动态的output_format模板
        task_type = self._i18n_manager.t("analyzer_output_format.task_type")
        action = self._i18n_manager.t("analyzer_output_format.action")
        target = self._i18n_manager.t("analyzer_output_format.target")
        execution_mode = self._i18n_manager.t("analyzer_output_format.execution_mode")
        confidence = self._i18n_manager.t("analyzer_output_format.confidence")
        param_value_placeholder = self._i18n_manager.t(
            "analyzer_output_format.param_value_placeholder"
        )
        param_type = self._i18n_manager.t("analyzer_output_format.param_type")
        required_true_false = self._i18n_manager.t("analyzer_output_format.required_true_false")
        # min_items = self._i18n_manager.t("analyzer_output_format.min_items")
        # non_empty_fields = self._i18n_manager.t("analyzer_output_format.non_empty_fields")

        output_format_template = f"""{{
            "task_type": "{task_type}",
            "action": "{action}",
            "target": "{target}",
            "execution_mode": "{execution_mode}",
            "confidence": "{confidence}",
            "required_parameters": {{
                "param_name": {{
                    "value": "{param_value_placeholder}",
                    "type": "{param_type}",
                    "required": {required_true_false},
                }}
            }},
            "expected_output": {{
                "required_fields": [],
                "validation_rules": {{
                    "min_items": 1,
                    "non_empty_fields": ["title", "content"],
                }},
            }}
        }}"""

        return {
            "role": self._i18n_manager.t("analyzer.role"),
            "execution_mode": self._i18n_manager.t("analyzer.execution_modes"),
            "analysis_steps": self._i18n_manager.t("analyzer.analysis_steps"),
            "action_vocabulary": self._i18n_manager.t("analyzer.action_vocabulary"),
            "output_format": output_format_template,
        }

import time
from typing import Dict, Any, Optional
from ...strategies.semantic_field_strategy import SemanticFieldStrategy


class AIForgeContentGenerationManager:
    """内容生成管理器 - 专门处理内容生成任务"""

    def __init__(self, components: Dict[str, Any]):
        self.components = components
        self.field_processor = SemanticFieldStrategy()
        self.parameter_mapping_service = components.get("parameter_mapping_service")
        self._i18n_manager = self.components.get("i18n_manager")
        self._initialize_semantic_fields()

    def _initialize_semantic_fields(self):
        """动态初始化语义字段定义"""
        if hasattr(self.field_processor, "field_semantics"):
            # 从 i18n 配置获取语义字段
            semantic_fields = self._get_semantic_fields_from_i18n()
            self.field_processor.field_semantics.update(semantic_fields)

    def _get_semantic_fields_from_i18n(self):
        """从 i18n 配置获取语义字段"""
        semantic_config = self._i18n_manager.t("semantic_fields", default={})

        semantic_fields = {}
        for field_type, keywords in semantic_config.items():
            if isinstance(keywords, dict):
                semantic_fields[field_type] = list(keywords.values())
            elif isinstance(keywords, list):
                semantic_fields[field_type] = keywords

        return semantic_fields

    def can_handle_content_generation(self, standardized_instruction: Dict[str, Any]) -> bool:
        """判断是否为内容生成任务"""
        task_type = standardized_instruction.get("task_type", "")
        return task_type == "content_generation"

    def execute_content_generation(
        self, standardized_instruction: Dict[str, Any], instruction: str
    ) -> Optional[Dict[str, Any]]:
        """执行内容生成任务"""
        if standardized_instruction.get("execution_mode", "") == "code_generation":
            return self._execute_search_enhanced_generation(standardized_instruction, instruction)
        else:
            return self._execute_direct_generation(standardized_instruction, instruction)

    def _execute_search_enhanced_generation(
        self, standardized_instruction: Dict[str, Any], instruction: str
    ) -> Optional[Dict[str, Any]]:
        """执行搜索增强的内容生成"""
        search_manager = self.components.get("search_manager")
        if not search_manager:
            return self._execute_direct_generation(standardized_instruction, instruction)

        ai_min_items = (
            standardized_instruction.get("expected_output", {})
            .get("validation_rules", {})
            .get("min_items", 1)
        )
        # 确保内容生成任务至少有足够的搜索结果，但不低于 AI 分析的要求
        content_min_items = max(ai_min_items, 2)  # 可以设置一个合理的最小值如 2

        # 为内容生成任务优化搜索参数，确保足够的结果数量
        content_search_instruction = standardized_instruction.copy()

        content_search_instruction.update(
            {
                "task_type": "data_fetch",
                "required_parameters": {
                    # 保留原有参数
                    **standardized_instruction.get("required_parameters", {}),
                    "search_query": {
                        "value": search_manager.extract_search_query(
                            standardized_instruction, instruction
                        ),
                        "type": "string",
                        "required": True,
                    },
                    "max_results": {
                        "value": 10,
                        "type": "int",
                        "required": False,
                    },
                    "min_items": {
                        "value": content_min_items,
                        "type": "int",
                        "required": True,
                    },
                    "min_abstract_len": {
                        "value": 500,
                        "type": "int",
                        "required": False,
                    },
                    "max_abstract_len": {
                        "value": 1000,
                        "type": "int",
                        "required": False,
                    },
                },
                "expected_output": {
                    "required_fields": ["title", "content", "url", "pub_time"],
                    "validation_rules": {
                        "min_items": content_min_items,
                        "non_empty_fields": ["title", "content", "url"],
                        "enable_deduplication": True,
                    },
                },
            }
        )

        # 使用完整的多层级搜索
        search_result = search_manager.execute_multi_level_search(
            content_search_instruction, instruction
        )

        if search_result and search_result.get("status") == "success":
            return self._generate_content_with_search_result(
                standardized_instruction, instruction, search_result
            )
        else:
            return self._execute_direct_generation(standardized_instruction, instruction)

    def _execute_direct_generation(
        self, standardized_instruction: Dict[str, Any], instruction: str
    ) -> Optional[Dict[str, Any]]:
        """执行直接内容生成"""
        output_format = self._extract_output_format_with_mapping(standardized_instruction)
        style_params = self._extract_style_parameters(standardized_instruction)

        # 使用 i18n 的提示词模板
        base_template = self._i18n_manager.t("content_generation.direct_generation_template")
        format_requirement = self._i18n_manager.t("content_generation.format_requirement")
        style_requirement = self._i18n_manager.t("content_generation.style_requirement")
        tone_requirement = self._i18n_manager.t("content_generation.tone_requirement")
        language_requirement = self._i18n_manager.t("content_generation.language_requirement")

        special_notes_header = self._i18n_manager.t("content_generation.special_notes_header")
        format_strict_note = self._i18n_manager.t("content_generation.format_strict_note")
        structure_note = self._i18n_manager.t("content_generation.structure_note")
        logic_note = self._i18n_manager.t("content_generation.logic_note")
        tone_maintain_note = self._i18n_manager.t("content_generation.tone_maintain_note")

        enhanced_instruction = f"""
        {base_template.format(instruction=instruction)}

        {format_requirement}：{output_format}
        {style_requirement}：{style_params.get('style', '专业')}
        {tone_requirement}：{style_params.get('tone', '客观')}
        {language_requirement}：{style_params.get('language', '中文')}

        {special_notes_header}：
        1. {format_strict_note.format(format=output_format)}
        2. {structure_note}
        3. {logic_note}
        4. {tone_maintain_note.format(tone=style_params.get('tone', '客观'))}
        """

        return self._call_llm_for_content(
            enhanced_instruction, output_format, standardized_instruction
        )

    def _get_format_and_style_requirements(
        self, output_format: str, style_params: Dict[str, str]
    ) -> str:
        """获取格式和样式要求"""
        format_requirement = self._i18n_manager.t("content_generation.format_requirement")
        style_requirement = self._i18n_manager.t("content_generation.style_requirement")
        tone_requirement = self._i18n_manager.t("content_generation.tone_requirement")
        language_requirement = self._i18n_manager.t("content_generation.language_requirement")

        return f"""
        {format_requirement}：{output_format}
        {style_requirement}：{style_params.get('style', '专业')}
        {tone_requirement}：{style_params.get('tone', '客观')}
        {language_requirement}：{style_params.get('language', '中文')}
        """

    def _get_search_enhanced_special_notes(
        self, output_format: str, style_params: Dict[str, str]
    ) -> str:
        """获取搜索增强的特殊注意事项"""
        special_notes_header = self._i18n_manager.t("content_generation.special_notes_header")
        date_note = self._i18n_manager.t("content_generation.date_note")
        format_strict_note = self._i18n_manager.t("content_generation.format_strict_note")
        structure_note = self._i18n_manager.t("content_generation.structure_note")
        data_based_note = self._i18n_manager.t("content_generation.data_based_note")
        tone_maintain_note = self._i18n_manager.t("content_generation.tone_maintain_note")
        content_only_note = self._i18n_manager.t("content_generation.content_only_note")
        return f"""
{special_notes_header}：
1. {date_note}
2. {format_strict_note.format(format=output_format)}
3. {structure_note}
4. {data_based_note}
5. {content_only_note}
6. {tone_maintain_note.format(tone=style_params.get('tone', '客观'))}
"""

    def _generate_content_with_search_result(
        self,
        standardized_instruction: Dict[str, Any],
        instruction: str,
        search_result: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """基于搜索结果生成内容"""
        search_data = search_result.get("data", [])
        output_format = self._extract_output_format_with_mapping(standardized_instruction)
        style_params = self._extract_style_parameters(standardized_instruction)

        # 使用 i18n 格式化搜索结果
        if len(search_data) > 0:
            search_results_header = self._i18n_manager.t("content_generation.search_results_header")
            result_label = self._i18n_manager.t("content_generation.result_label")
            title_label = self._i18n_manager.t("content_generation.title_label")
            publish_time_label = self._i18n_manager.t("content_generation.publish_time_label")
            abstract_label = self._i18n_manager.t("content_generation.abstract_label")
            content_label = self._i18n_manager.t("content_generation.content_label")
            no_title = self._i18n_manager.t("content_generation.no_title")
            unknown_time = self._i18n_manager.t("content_generation.unknown_time")
            no_abstract = self._i18n_manager.t("content_generation.no_abstract")

            formatted = f"{search_results_header.format(instruction=instruction)}：\n\n"
            for i, result in enumerate(search_data, 1):
                formatted += f"## {result_label} {i}\n"
                formatted += f"**{title_label}**: {result.get('title', no_title)}\n"
                formatted += f"**{publish_time_label}**: {result.get('pub_time', unknown_time)}\n"
                formatted += f"**{abstract_label}**: {result.get('abstract', no_abstract)}\n"
                formatted += f"**{content_label}**: {result.get('content', '')}...\n"
                formatted += "\n"
        else:
            formatted = self._i18n_manager.t("content_generation.no_search_results_fallback")

        # 使用 i18n 的搜索增强模板
        search_enhanced_template = self._i18n_manager.t(
            "content_generation.search_enhanced_template"
        )
        task_requirement = self._i18n_manager.t("content_generation.task_requirement")

        enhanced_instruction = f"""
        {search_enhanced_template}
        {formatted}

        {task_requirement.format(instruction=instruction)}

        {self._get_format_and_style_requirements(output_format, style_params)}

        {self._get_search_enhanced_special_notes(output_format, style_params)}
        """

        return self._call_llm_for_content(
            enhanced_instruction, output_format, standardized_instruction, len(search_data)
        )

    def _extract_output_format_with_mapping(self, standardized_instruction: Dict[str, Any]) -> str:
        """使用参数映射服务提取输出格式"""
        parameters = standardized_instruction.get("required_parameters", {})

        # 使用参数映射服务进行格式参数映射
        if self.parameter_mapping_service:
            # 创建虚拟函数来获取格式参数
            def dummy_format_function(
                output_format="markdown", format="markdown", type="markdown", extension="md"
            ):
                # 优先级：output_format > format > type > extension
                for param in [output_format, format, type, extension]:
                    if param and param != "markdown" and param != "md":
                        return param
                return "markdown"

            context = {
                "task_type": standardized_instruction.get("task_type"),
                "action": standardized_instruction.get("action"),
                "function_name": "extract_format",
            }

            try:
                mapped_params = self.parameter_mapping_service.map_parameters(
                    dummy_format_function, parameters, context
                )
                result = dummy_format_function(**mapped_params)
                if result and result != "markdown":
                    return result.lower()
            except Exception:
                pass

        # 回退到原有逻辑
        return self._fallback_format_extraction(standardized_instruction)

    def _extract_style_parameters(self, standardized_instruction: Dict[str, Any]) -> Dict[str, str]:
        """使用参数映射服务提取样式参数"""
        parameters = standardized_instruction.get("required_parameters", {})
        style_params = {"style": "专业", "tone": "客观", "language": "中文"}

        if self.parameter_mapping_service:
            # 创建虚拟函数来获取样式参数
            def dummy_style_function(
                style="专业", tone="客观", language="中文", theme="专业", mood="客观", lang="中文"
            ):
                return {
                    "style": style or theme or "专业",
                    "tone": tone or mood or "客观",
                    "language": language or lang or "中文",
                }

            context = {
                "task_type": standardized_instruction.get("task_type"),
                "action": standardized_instruction.get("action"),
                "function_name": "extract_style",
            }

            try:
                mapped_params = self.parameter_mapping_service.map_parameters(
                    dummy_style_function, parameters, context
                )
                result = dummy_style_function(**mapped_params)
                style_params.update(result)
            except Exception:
                pass

        return style_params

    def _fallback_format_extraction(self, standardized_instruction: Dict[str, Any]) -> str:
        """回退的格式提取逻辑"""
        # 直接检查参数
        parameters = standardized_instruction.get("required_parameters", {})
        format_params = ["output_format", "format", "type", "extension"]

        for param_name in format_params:
            if param_name in parameters:
                param_info = parameters[param_name]
                if isinstance(param_info, dict) and "value" in param_info:
                    return param_info["value"].lower()
                elif isinstance(param_info, str):
                    return param_info.lower()

        # 从 i18n 配置获取格式关键词
        format_keywords = self._i18n_manager.t("format_keywords", default={})

        instruction_lower = standardized_instruction.get("target", "").lower()
        for format_type, keywords in format_keywords.items():
            if any(keyword in instruction_lower for keyword in keywords):
                return format_type

        return "markdown"

    def _call_llm_for_content(
        self,
        enhanced_instruction: str,
        output_format: str,
        standardized_instruction: Dict[str, Any],
        search_results_count: int = 0,
    ) -> Dict[str, Any]:
        """调用LLM生成内容"""
        llm_manager = self.components.get("llm_manager")
        if not llm_manager:
            error_content = self._i18n_manager.t("content_generation.llm_manager_unavailable")
            error_summary = self._i18n_manager.t("content_generation.llm_manager_error_summary")
            return {
                "data": {"content": error_content},
                "status": "error",
                "summary": error_summary,
            }

        client = llm_manager.get_client()
        if not client:
            error_content = self._i18n_manager.t("content_generation.llm_client_unavailable")
            error_summary = self._i18n_manager.t("content_generation.llm_client_error_summary")
            return {
                "data": {"content": error_content},
                "status": "error",
                "summary": error_summary,
            }
        try:
            content = client.generate_code(enhanced_instruction, None, use_history=False)

            success_summary = self._i18n_manager.t(
                "content_generation.generation_success", format=output_format
            )
            if search_results_count > 0:
                search_based_suffix = self._i18n_manager.t(
                    "content_generation.search_based_suffix", count=search_results_count
                )
                success_summary += search_based_suffix

            return {
                "data": {
                    "content": content,
                    "format": output_format,
                    "content_type": self._get_content_type(output_format),
                },
                "status": "success",
                "summary": success_summary,
                "metadata": {
                    "timestamp": time.time(),
                    "task_type": "content_generation",
                    "execution_type": (
                        "search_enhanced_content" if search_results_count > 0 else "direct_content"
                    ),
                    "output_format": output_format,
                    "search_results_count": search_results_count,
                },
            }
        except Exception as e:
            error_content = self._i18n_manager.t(
                "content_generation.generation_error", error=str(e)
            )
            error_summary = self._i18n_manager.t(
                "content_generation.generation_failed", error=str(e)
            )
            return {
                "data": {"content": error_content},
                "status": "error",
                "summary": error_summary,
            }

    def get_supported_formats(self) -> list:
        """获取支持的输出格式列表"""
        return ["markdown", "html", "json", "xml", "pdf", "docx", "txt"]

    def validate_format(self, format_name: str) -> bool:
        """验证格式是否支持"""
        return format_name.lower() in self.get_supported_formats()

    def _get_content_type(self, output_format: str) -> str:
        """根据输出格式获取内容类型"""
        content_type_mapping = {
            "markdown": "text/markdown",
            "html": "text/html",
            "json": "application/json",
            "xml": "application/xml",
            "pdf": "application/pdf",
            "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "txt": "text/plain",
        }
        return content_type_mapping.get(output_format.lower(), "text/plain")

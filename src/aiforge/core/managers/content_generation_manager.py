import time
from typing import Dict, Any, Optional
from ...strategies.semantic_field_strategy import SemanticFieldStrategy


class AIForgeContentGenerationManager:
    """内容生成管理器 - 专门处理内容生成任务"""

    def __init__(self, components: Dict[str, Any]):
        self.components = components
        self.field_processor = SemanticFieldStrategy()
        self.parameter_mapping_service = components.get("parameter_mapping_service")

        # 扩展语义字段定义，支持格式相关参数
        if hasattr(self.field_processor, "field_semantics"):
            self.field_processor.field_semantics.update(
                {
                    "format": [
                        "format",
                        "output_format",
                        "格式",
                        "输出格式",
                        "type",
                        "extension",
                        "文件格式",
                    ],
                    "style": ["style", "样式", "风格", "theme", "template", "模板"],
                    "language": ["language", "lang", "语言", "locale", "国际化"],
                    "tone": ["tone", "语调", "风格", "mood", "情感"],
                }
            )

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
                        "value": 5,
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
                        "min_items": 5,
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

        enhanced_instruction = f"""
        请根据用户要求：{instruction}，生成文章内容。

        输出格式要求：{output_format}
        样式要求：{style_params.get('style', '专业')}
        语调：{style_params.get('tone', '客观')}
        语言：{style_params.get('language', '中文')}

        特别注意：
        1. 严格按照{output_format}格式输出
        2. 确保内容结构清晰，格式规范
        3. 内容要有逻辑性和可读性
        4. 保持{style_params.get('tone', '客观')}的语调
        """

        return self._call_llm_for_content(
            enhanced_instruction, output_format, standardized_instruction
        )

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

        # 格式化搜索结果
        if len(search_data) > 0:
            formatted = f"关于'{instruction}'的搜索结果：\n\n"
            for i, result in enumerate(search_data, 1):
                formatted += f"## 结果 {i}\n"
                formatted += f"**标题**: {result.get('title', '无标题')}\n"
                formatted += f"**发布时间**: {result.get('pub_time', '未知时间')}\n"
                formatted += f"**摘要**: {result.get('abstract', '无摘要')}\n"
                formatted += f"**内容**: {result.get('content', '')}...\n"
                formatted += "\n"
        else:
            formatted = "未找到相关搜索结果，请基于已有知识生成内容。"

        enhanced_instruction = f"""
        请基于以下搜索到的最新数据内容：
        {formatted}

        和用户任务要求：{instruction}，生成文章内容。

        输出格式要求：{output_format}
        样式要求：{style_params.get('style', '专业')}
        语调：{style_params.get('tone', '客观')}
        语言：{style_params.get('language', '中文')}

        特别注意：
        1. 文章中的日期必须采用搜索结果的日期
        2. 严格按照{output_format}格式输出
        3. 确保内容结构清晰，格式规范
        4. 基于搜索结果的真实数据进行分析和创作
        5. 保持{style_params.get('tone', '客观')}的语调
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

        # 检查指令中是否包含格式要求
        instruction_lower = standardized_instruction.get("target", "").lower()
        format_keywords = {
            "markdown": ["markdown", "md", "标记语言"],
            "html": ["html", "网页", "web"],
            "json": ["json", "数据格式"],
            "xml": ["xml"],
            "pdf": ["pdf"],
            "docx": ["word", "docx", "文档"],
            "txt": ["txt", "文本", "纯文本"],
        }

        for format_type, keywords in format_keywords.items():
            if any(keyword in instruction_lower for keyword in keywords):
                return format_type

        # 默认返回markdown
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
            return {
                "data": {"content": "LLM管理器不可用"},
                "status": "error",
                "summary": "内容生成失败：LLM管理器不可用",
            }

        client = llm_manager.get_client()
        if not client:
            return {
                "data": {"content": "LLM客户端不可用"},
                "status": "error",
                "summary": "内容生成失败：LLM客户端不可用",
            }
        try:
            content = client.generate_code(enhanced_instruction, None, use_history=False)

            return {
                "data": {
                    "content": content,
                    "format": output_format,
                    "content_type": self._get_content_type(output_format),
                },
                "status": "success",
                "summary": f"成功生成{output_format}格式内容"
                + (f"（基于{search_results_count}条搜索结果）" if search_results_count > 0 else ""),
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
            return {
                "data": {"content": f"内容生成出错：{str(e)}"},
                "status": "error",
                "summary": f"内容生成失败：{str(e)}",
            }

    def _get_content_type(self, output_format: str) -> str:
        """根据格式返回内容类型"""
        format_mapping = {
            "markdown": "text/markdown",
            "html": "text/html",
            "json": "application/json",
            "xml": "application/xml",
            "pdf": "application/pdf",
            "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "txt": "text/plain",
        }
        return format_mapping.get(output_format, "text/plain")

    def get_supported_formats(self) -> list:
        """获取支持的输出格式列表"""
        return ["markdown", "html", "json", "xml", "pdf", "docx", "txt"]

    def validate_format(self, format_name: str) -> bool:
        """验证格式是否支持"""
        return format_name.lower() in self.get_supported_formats()

from typing import Optional, Dict, Any


class AIForgePrompt:
    """AIForge 提示词生成器"""

    @staticmethod
    def _get_task_specific_format(task_type: str, expected_output: Dict[str, Any] = None) -> str:
        """获取任务特定格式，只在 data_fetch 且包含搜索字段时应用搜索增强"""

        if not expected_output:
            # 回退到基础格式
            return """
# 输出格式要求：
__result__ = {
    "data": [{"字段1": "值1", ...},...],
    "status": "success或error",
    "summary": "结果摘要",
    "metadata": {"timestamp": "...", "task_type": "..."}
}

# 重要提示：status 应该反映代码执行状态，而不是数据获取结果（即使data=[],status=success）
"""

        # 基于AI分析的预期输出规则生成格式
        required_fields = expected_output.get("required_fields", [])

        # 构建data字段示例
        data_example = {}
        for field in required_fields:
            data_example[field] = f"{field}_value"

        # 添加验证规则中的非空字段说明
        validation_rules = expected_output.get("validation_rules", {})
        non_empty_fields = validation_rules.get("non_empty_fields", [])

        format_str = f"""
# 基于AI分析的输出格式要求：
__result__ = {{
    "data": [{data_example},...],
    "status": "success或error",
    "summary": "任务完成描述",
    "metadata": {{"timestamp": "...", "task_type": "{task_type}"}}
}}

# 必需字段：{', '.join(required_fields)}
# 非空字段：{', '.join(non_empty_fields)}
# 重要提示：status 应该反映代码执行状态，而不是数据获取结果（即使data=[],status=success）
"""
        return format_str

    @staticmethod
    def get_base_aiforge_prompt(optimize_tokens: bool = True) -> str:
        """生成基础的AIForge系统提示"""
        # 基础代码生成规则
        code_rule = """
- 生成的代码必须能在标准 Python 环境中直接执行
- 使用标准 Markdown 代码块格式：```python ... ```，不要输出任何解释性文字
- 实现完整的错误处理和异常捕获
"""

        if optimize_tokens:
            code_rule += "\n- 生成极简代码，无注释，无空行\n- 使用最短变量名(a,b,c,d等)，函数的参数名不得压缩"

        # 构建基础 prompt
        base_prompt = f"""
# AIForge：Python 代码生成和执行助手

# 代码生成规范
{code_rule}

# 执行规范
执行代码，并将执行结果赋值给 __result__ ，结果禁止使用模拟或占位符数据
"""
        return base_prompt

    @staticmethod
    def _get_enhanced_aiforge_prompt_with_validation(
        optimize_tokens: bool = True,
        task_type: Optional[str] = None,
        parameters: Optional[Dict[str, Any]] = None,
        expected_output: Optional[Dict[str, Any]] = None,  # 新增参数
    ) -> str:
        """生成带通用参数验证约束的增强系统提示"""

        base_prompt = AIForgePrompt.get_base_aiforge_prompt(optimize_tokens)

        execution_guidance = ""
        if parameters:
            param_analysis = AIForgePrompt._analyze_parameters_for_execution(parameters)

            execution_guidance = f"""
## 🔧 参数化执行指导

根据任务分析生成函数：

def execute_task({param_analysis['signature']}):
    '''
    {param_analysis['docstring']}
    '''
    # 实现功能逻辑
    return result_data

# 参数说明：
{param_analysis['param_docs']}

# 必须立即调用：
__result__ = execute_task({param_analysis['call_args']})

## 📋 参数使用规范：
1. 每个参数必须在函数体内被实际使用，影响执行路径或结果
2. 禁止硬编码可通过参数获取的值
3. 参数应用于：控制行为、作为数据源、影响输出、配置执行

## ❌ 避免模式：
- 定义但不使用的参数
- 参数仅用于显示而不影响核心逻辑
- 忽略参数而使用硬编码值
    """

        enhanced_prompt = f"""
{base_prompt}

{execution_guidance}
"""

        # 使用AI分析结果生成格式要求，而不是内置格式
        enhanced_prompt += (
            f"\n\n{AIForgePrompt._get_task_specific_format(task_type, expected_output)}"
        )

        return enhanced_prompt

    @staticmethod
    def _analyze_parameters_for_execution(parameters: Dict[str, Any]) -> Dict[str, str]:
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
        docstring = f"执行任务，使用提供的参数: {', '.join(param_names)}"

        return {
            "signature": signature,
            "call_args": call_signature,
            "param_docs": "\n".join(param_docs),
            "docstring": docstring,
        }

    @staticmethod
    def get_direct_response_prompt(action: str, standardized_instruction: Dict[str, Any]) -> str:
        """构建直接响应专用提示词"""
        # 基础提示词映射
        prompts = {
            "answer": "你是一个知识助手，请直接回答用户的问题。要求准确、简洁、有用。",
            "respond": "你是一个知识助手，请直接回答用户的问题。要求准确、简洁、有用。",
            "create": "你是一个内容创作助手，请根据用户要求创作内容。注意风格和格式要求。",
            "translate": "你是一个翻译助手，请准确翻译用户提供的内容。保持原意和语言风格。",
            "summarize": "你是一个文本分析助手，请总结和分析用户提供的文本内容。",
            "suggest": "你是一个咨询顾问，请根据用户需求提供建议和意见。",
            "chat_ai": "你是一个友好、专业且体贴的AI助手，请根据对话情境提供合适的回应。",
        }

        base_prompt = prompts.get(action, "你是一个AI助手，请直接响应用户的需求。")

        # 从 standardized_instruction 中提取增强信息
        target = standardized_instruction.get("target", "")

        # 根据 action 类型选择合适的输出格式
        action_format_mapping = {
            "create": "markdown",  # 内容创作通常需要格式化
            "translate": "text",  # 翻译保持纯文本
            "summarize": "structured_text",  # 总结需要结构化
            "answer": "text",  # 问答保持简洁
            "respond": "text",  # 响应保持简洁
            "suggest": "structured_text",  # 建议需要结构化
            "chat_ai": "text",
        }

        output_format = action_format_mapping.get(action, "text")

        parameters = standardized_instruction.get("parameters", {})
        task_type = standardized_instruction.get("task_type", "")

        # 构建增强的提示词
        enhanced_sections = []

        # 1. 任务上下文增强
        if target:
            enhanced_sections.append(f"任务目标: {target}")

        # 2. 输出格式指导
        format_guidance = {
            "text": "以纯文本形式回答",
            "markdown": "使用Markdown格式，包含适当的标题、列表和强调",
            "structured_text": "使用结构化的文本格式，包含清晰的段落和要点",
        }

        if output_format in format_guidance:
            enhanced_sections.append(f"输出要求: {format_guidance[output_format]}")

        # 3. 参数上下文增强
        if parameters:
            param_context = []
            for param_name, param_value in parameters.items():
                if param_value:
                    param_context.append(f"- {param_name}: {param_value}")

            if param_context:
                enhanced_sections.append("相关参数:\n" + "\n".join(param_context))

        # 4. 任务类型特定指导
        task_specific_guidance = {
            "direct_response": "专注于直接回答，避免冗余信息",
            "content_generation": "注重创意和原创性",
            "data_process": "提供清晰的分析思路",
        }

        if task_type in task_specific_guidance:
            enhanced_sections.append(f"特殊要求: {task_specific_guidance[task_type]}")

        # 组装最终提示词
        enhanced_prompt = base_prompt

        if enhanced_sections:
            enhanced_prompt += "\n\n## 任务详情\n" + "\n\n".join(enhanced_sections)

        enhanced_prompt += """

## 重要限制
- 直接提供最终答案，不要生成代码
- 如果任务需要实时数据或文件操作，请说明无法完成
- 保持回答的专业性和准确性
"""

        return enhanced_prompt

    @staticmethod
    def get_enhanced_system_prompt(
        standardized_instruction: Dict[str, Any], optimize_tokens=True, original_prompt: str = None
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
        enhanced_prompt = AIForgePrompt._get_enhanced_aiforge_prompt_with_validation(
            optimize_tokens=optimize_tokens,
            task_type=task_type,
            parameters=parameters,
            expected_output=expected_output,  # 直接使用标准化指令中的输出规则
        )

        if original_prompt:
            enhanced_prompt += f"\n\n# 原始指令补充\n{original_prompt}"

        return enhanced_prompt

    @staticmethod
    def get_base_prompt_sections() -> Dict[str, str]:
        """构建基础提示词各个部分"""
        return {
            "role": "你是 AIForge 智能任务分析器，负责理解用户指令并分析完成任务所需的必要信息以及预期结果",
            "execution_mode": """
    - 直接响应：AI知识可直接完成，无需最新数据，包括对话延续和情感支持
    - 代码生成：需要外部数据源、实时信息或系统交互
    """,
            "analysis_steps": """
    - 识别执行模式和任务类型
    - 提取关键参数和数量要求，设置合适的 min_items
    - 定义必需字段和验证规则
    - "获取/查找/搜索"某类信息的非任务型指令，仅提取一个required_parameters参数search_query=原始指令
    - 智能识别对话延续和情感支持类指令，自动设置为直接响应模式
    """,
            "action_vocabulary": """
    - 数据获取 → fetch_{task_type_suffix}
    - 数据处理 → process_{task_type_suffix}
    - 内容生成 → generate_{task_type_suffix}
    - 文件操作 → transform_{task_type_suffix}
    - 直接响应 → respond_{task_type_suffix}
    - 对话延续和情感支持 → chat_ai

    """,
            "output_format": """{
        "task_type": "任务类型",
        "action": "具体动作",
        "target": "任务描述",
        "execution_mode": "direct_ai_response或code_generation",
        "confidence": "置信度",
        "required_parameters": {
            "param_name": {
                "value": "提取的值或None",
                "type": "参数类型",
                "required": true/false,
            }
        },
        "expected_output": {
            "required_fields": [],
            "validation_rules": {
                "min_items": 1,
                "non_empty_fields": ["title", "content"],
            },
        }
    }""",
        }

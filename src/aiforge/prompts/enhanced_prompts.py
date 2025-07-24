from typing import Optional, Dict, Any


def get_task_specific_format(task_type: str) -> str:
    """获取任务特定的输出格式要求"""
    formats = {
        "web_search": """
# 搜索任务输出格式
__result__ = {
    "data": {
        "results": [{"title": "...", "url": "...", "content": "..."}],
        "total_count": int,
        "query": "原始查询"
    },
    "status": "success",
    "summary": "搜索完成描述",
    "metadata": {"timestamp": "...", "source": "搜索引擎名称"}
}""",
        "data_analysis": """
# 数据分析任务输出格式
__result__ = {
    "data": {
        "analysis": {"key_findings": "...", "trends": "..."},
        "processed_data": processed_data,
        "summary": {"total_records": int, "key_metrics": {}}
    },
    "status": "success",
    "summary": "分析完成描述",
    "metadata": {"timestamp": "...", "data_source": "..."}
}""",
        "file_processing": """
# 文件处理任务输出格式
__result__ = {
    "data": {
        "processed_files": [{"file": "...", "status": "success", "size": int}],
        "summary": {"total_files": int, "success_count": int, "error_count": int},
        "errors": [{"file": "...", "error": "..."}]
    },
    "status": "success",
    "summary": "文件处理完成描述",
    "metadata": {"timestamp": "...", "operation": "..."}
}""",
        "api_call": """
# API调用任务输出格式
__result__ = {
    "data": {
        "response_data": api_response,
        "status_code": int,
        "headers": response_headers,
        "summary": {"success": bool, "response_time": float}
    },
    "status": "success",
    "summary": "API调用完成描述",
    "metadata": {"endpoint": "...", "timestamp": "..."}
}""",
        "data_fetch": """
# 数据获取任务输出格式
__result__ = {
    "data": {
        "content": "获取的数据内容",
        "source": "数据来源",
        "additional_info": {}
    },
    "status": "success",
    "summary": "数据获取完成描述",
    "metadata": {"timestamp": "...", "task_type": "data_fetch"}
}""",
        "web_request": """
# 网页请求任务输出格式
__result__ = {
    "data": {
        "content": "网页内容",
        "url": "请求的URL",
        "status_code": int,
        "headers": {}
    },
    "status": "success",
    "summary": "网页请求完成描述",
    "metadata": {"timestamp": "...", "method": "GET/POST"}
}""",
        "automation": """
# 自动化任务输出格式
__result__ = {
    "data": {
        "executed_steps": ["步骤1", "步骤2"],
        "results": {},
        "summary": {"total_steps": int, "success_steps": int}
    },
    "status": "success",
    "summary": "自动化任务完成描述",
    "metadata": {"timestamp": "...", "workflow": "..."}
}""",
        "content_generation": """
# 内容生成任务输出格式
__result__ = {
    "data": {
        "generated_content": "生成的内容",
        "content_type": "text/html/markdown",
        "word_count": int
    },
    "status": "success",
    "summary": "内容生成完成描述",
    "metadata": {"timestamp": "...", "template": "..."}
}""",
    }

    return formats.get(
        task_type,
        """
# 输出格式要求：
__result__ = {
    "data": main_result,
    "status": "success/error",
    "summary": "结果摘要",
    "metadata": {"timestamp": "...", "task_type": "..."}
}""",
    )


def get_base_aiforge_prompt(optimize_tokens: bool = True) -> str:
    """生成基础的AIForge系统提示"""
    # 基础代码生成规则
    code_rule = """
- 生成的代码必须能在标准 Python 环境中直接执行
- 使用标准 Markdown 代码块格式：```python ... ```，不要输出任何解释性文字
- 使用预装库：requests, BeautifulSoup, pandas, numpy 等
- 实现完整的错误处理和异常捕获
"""

    if optimize_tokens:
        code_rule += "\n- 生成极简代码，无注释，无空行\n- 使用最短变量名(a,b,c,d等)"

    # 构建基础 prompt
    base_prompt = f"""
# AIForge：Python 代码生成和执行助手

# 代码生成规范
{code_rule}

# 执行规范
执行代码，并将执行结果赋值给 __result__

"""
    return base_prompt


def get_enhanced_aiforge_prompt(
    optimize_tokens: bool = True,
    task_type: Optional[str] = None,
    parameters: Optional[Dict[str, Any]] = None,
) -> str:
    """生成增强的系统提示"""

    base_prompt = get_base_aiforge_prompt(optimize_tokens)

    # 智能参数化执行指导
    execution_guidance = ""
    if parameters:
        # 分析参数结构，生成智能的函数定义
        param_analysis = _analyze_parameters_for_execution(parameters)

        execution_guidance = f"""
## 🔧 智能参数化执行指导

基于任务分析，生成以下参数化函数：

def execute_task({param_analysis['signature']}):
    '''
    {param_analysis['docstring']}
    '''
    # 使用传入的参数完成任务
    # 实现逻辑应该基于参数的实际含义和任务需求
    return result_data

# 参数说明：
{param_analysis['param_docs']}

🚨 必须在函数定义后立即调用：
__result__ = execute_task({param_analysis['call_args']})

重要：函数实现应该真正使用这些参数来完成任务，而不是忽略参数。
"""

    enhanced_prompt = f"""
{base_prompt}

{execution_guidance}
"""

    enhanced_prompt += f"\n\n{get_task_specific_format(task_type)}"

    return enhanced_prompt


def get_enhanced_aiforge_prompt_with_universal_validation(
    optimize_tokens: bool = True,
    task_type: Optional[str] = None,
    parameters: Optional[Dict[str, Any]] = None,
) -> str:
    """生成带通用参数验证约束的增强系统提示"""

    base_prompt = get_base_aiforge_prompt(optimize_tokens)

    execution_guidance = ""
    if parameters:
        param_analysis = _analyze_parameters_for_execution(parameters)

        execution_guidance = f"""
## 🔧 智能参数化执行指导

基于任务分析，生成以下参数化函数：

def execute_task({param_analysis['signature']}):
    '''
    {param_analysis['docstring']}
    '''
    # 🚨 通用参数使用要求：
    # 1. 每个参数都必须在函数逻辑中被实际使用
    # 2. 参数值必须影响函数的执行结果或返回值
    # 3. 不得硬编码任何可以从参数获取的值
    # 4. 参数应该用于控制函数的行为、数据源或输出格式

    # 实现逻辑应该基于参数的实际含义和任务需求
    return result_data

# 参数说明：
{param_analysis['param_docs']}

🚨 必须在函数定义后立即调用：
__result__ = execute_task({param_analysis['call_args']})

## 📋 通用参数使用验证标准：
1. 参数必须在函数体内被引用和使用
2. 参数的值必须影响函数的执行路径或结果
3. 避免硬编码任何可以通过参数传递的值
4. 参数应该用于：
   - 控制函数行为（条件判断、循环控制）
   - 作为数据源（API调用、文件路径、查询条件）
   - 影响输出格式（格式化、过滤、排序）
   - 配置执行参数（超时、重试次数、精度）

## ❌ 通用禁止模式：
- 定义参数但不在函数体中使用
- 参数仅用于字符串拼接显示，不影响核心逻辑
- 硬编码值而忽略相应参数
- 参数仅用于注释或日志，不参与业务逻辑
"""

    enhanced_prompt = f"""
{base_prompt}

{execution_guidance}
"""

    enhanced_prompt += f"\n\n{get_task_specific_format(task_type)}"

    return enhanced_prompt


def _analyze_parameters_for_execution(parameters: Dict[str, Any]) -> Dict[str, str]:
    """分析参数结构，生成执行指导"""
    param_names = []
    param_docs = []
    call_args = []

    for param_name, param_info in parameters.items():
        if isinstance(param_info, dict):
            value = param_info.get("value")
            param_type = param_info.get("type", "str")
            description = param_info.get("description", "")
            required = param_info.get("required", True)

            # 构建函数签名
            if required and value is not None:
                param_names.append(param_name)
                call_args.append(f'"{value}"' if param_type == "str" else str(value))
            elif not required:
                default_val = param_info.get("default", "None")
                param_names.append(f"{param_name}={default_val}")
                if value is not None:
                    call_args.append(f'"{value}"' if param_type == "str" else str(value))
                else:
                    if default_val is None:
                        call_args.append("None")
                    else:
                        call_args.append(str(default_val))

            # 构建参数文档
            param_docs.append(f"- {param_name} ({param_type}): {description}")
        else:
            # 简单参数处理
            param_names.append(param_name)
            call_args.append(f'"{param_info}"' if isinstance(param_info, str) else str(param_info))
            param_docs.append(f"- {param_name}: {param_info}")

    signature = ", ".join(param_names)
    call_signature = ", ".join(call_args)
    docstring = f"执行任务，使用提供的参数: {', '.join(param_names)}"

    return {
        "signature": signature,
        "call_args": call_signature,
        "param_docs": "\n".join(param_docs),
        "docstring": docstring,
    }


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
    }

    base_prompt = prompts.get(action, "你是一个AI助手，请直接响应用户的需求。")

    # 从 standardized_instruction 中提取增强信息
    target = standardized_instruction.get("target", "")
    output_format = standardized_instruction.get("output_format", "text")
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


def get_enhanced_system_prompt_universal(
    standardized_instruction: Dict[str, Any], optimize_tokens=True, original_prompt: str = None
) -> str:
    """基于标准化指令构建通用增强系统提示词"""
    task_type = standardized_instruction.get("task_type", "general")

    # 获取参数信息
    parameters = standardized_instruction.get("required_parameters", {})
    if not parameters:
        parameters = standardized_instruction.get("parameters", {})

    # 最后的回退：确保有基本的指令参数
    if not parameters:
        parameters = {
            "instruction": {
                "value": standardized_instruction.get("target", ""),
                "type": "str",
                "description": "用户输入的指令内容",
                "required": True,
            }
        }

    # 使用通用增强版提示词生成
    enhanced_prompt = get_enhanced_aiforge_prompt_with_universal_validation(
        optimize_tokens=optimize_tokens,
        task_type=task_type,
        parameters=parameters,
    )

    if original_prompt:
        enhanced_prompt += f"\n\n# 原始指令补充\n{original_prompt}"

    return enhanced_prompt

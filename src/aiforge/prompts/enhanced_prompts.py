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
                    call_args.append(default_val)

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

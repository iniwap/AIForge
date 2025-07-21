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
# 通用任务输出格式
__result__ = {
    "data": main_result,
    "status": "success/error",
    "summary": "结果摘要",
    "metadata": {"timestamp": "...", "task_type": "..."}
}""",
    )


def should_use_detailed_prompt(instruction: str) -> bool:
    """判断是否使用详细的用户指令模式"""
    if not instruction:
        return False

    instruction_lower = instruction.lower()

    # 1. 长度判断 - 超过200字符通常是详细指令
    if len(instruction) > 200:
        return True

    # 2. 技术实现关键词 - 包含具体技术实现细节
    technical_keywords = [
        # 代码结构相关
        "函数",
        "function",
        "def ",
        "class ",
        "方法",
        "method",
        "返回格式",
        "return format",
        "数据格式",
        "data format",
        "严格遵守",
        "strictly follow",
        "必须",
        "must",
        # Web抓取相关
        "css选择器",
        "css selector",
        "xpath",
        "beautifulsoup",
        "requests",
        "urllib",
        "html",
        "dom",
        "meta标签",
        "meta tag",
        "time标签",
        "time tag",
        # 数据处理相关
        "json",
        "xml",
        "csv",
        "pandas",
        "numpy",
        "并行",
        "parallel",
        "concurrent",
        "threadpool",
        "异步",
        "async",
        "await",
        # 搜索引擎相关
        "百度",
        "baidu",
        "bing",
        "360",
        "搜狗",
        "sogou",
        "搜索引擎",
        "search engine",
        "爬虫",
        "crawler",
        # 配置和格式相关
        "配置",
        "config",
        "参数",
        "parameter",
        "param",
        "模板",
        "template",
        "格式化",
        "format",
    ]

    # 3. 代码块标识 - 包含代码块或代码示例
    code_indicators = [
        "```",
        "`",
        "import ",
        "from ",
        "def ",
        "class ",
        "if __name__",
        "__result__",
        "print(",
        "return ",
    ]

    # 4. 详细规范关键词 - 包含详细的规范说明
    specification_keywords = [
        "按优先级",
        "priority",
        "依次尝试",
        "try in order",
        "遵从以下策略",
        "follow strategy",
        "处理逻辑",
        "processing logic",
        "停止条件",
        "stop condition",
        "终止条件",
        "termination condition",
        "至少",
        "at least",
        "不少于",
        "no less than",
        "过滤掉",
        "filter out",
        "排序",
        "sort",
        "优先",
        "priority",
    ]

    # 5. 多步骤指令 - 包含多个步骤的复杂任务
    multi_step_keywords = [
        "第一步",
        "step 1",
        "首先",
        "first",
        "然后",
        "then",
        "接下来",
        "next",
        "最后",
        "finally",
        "步骤",
        "step",
        "流程",
        "process",
        "顺序",
        "sequence",
        "依次",
        "in order",
    ]

    # 检查各类关键词
    keyword_groups = [
        technical_keywords,
        code_indicators,
        specification_keywords,
        multi_step_keywords,
    ]

    # 如果在多个关键词组中都找到匹配，说明是详细指令
    matched_groups = 0
    for keywords in keyword_groups:
        if any(keyword in instruction_lower for keyword in keywords):
            matched_groups += 1

    # 匹配2个或以上关键词组，认为是详细指令
    if matched_groups >= 2:
        return True

    # 6. 特殊模式检测 - 包含特定的详细指令模式
    detailed_patterns = [
        # 包含具体的URL模式
        r"https?://[^\s]+",
        # 包含CSS选择器模式
        r'["\'][.#][^"\']+["\']',
        # 包含代码变量模式
        r"\{[^}]+\}",
        # 包含函数调用模式
        r"\w+\([^)]*\)",
    ]

    import re

    for pattern in detailed_patterns:
        if re.search(pattern, instruction):
            return True

    return False


def get_enhanced_aiforge_prompt(
    user_prompt: Optional[str] = None,
    optimize_tokens: bool = True,
    task_type: Optional[str] = None,
    parameters: Optional[Dict[str, Any]] = None,
    original_prompt: str | None = None,
) -> str:
    """生成增强的系统提示"""

    # 基础代码生成规则
    code_rule = """
## 代码生成规则
- 生成的代码必须能在标准 Python 环境中直接执行
- 使用预装库：requests, BeautifulSoup, pandas, numpy 等
- 实现完整的错误处理和异常捕获"""

    if optimize_tokens:
        code_rule += "\n- 生成极简代码，无注释，无空行\n- 使用最短变量名(a,b,c,d等)"

    # 输出格式要求
    format_rules = """
## 🚨 CRITICAL: 输出格式要求 🚨
__result__ 必须是字典格式，包含：
- "data": 实际数据（成功时）或 null（失败时）
- "status": "success" 或 "error"
- "summary": 简短描述
- "metadata": 包含timestamp等信息"""

    # 参数化和执行模式指导
    execution_guidance = ""
    if parameters:
        param_names = list(parameters.keys())
        param_descriptions = []
        for k, v in parameters.items():
            if isinstance(v, dict) and "description" in v:
                param_descriptions.append(
                    f"- {k}: {v['description']} (类型: {v.get('type', 'str')})"
                )
            else:
                param_descriptions.append(f"- {k}: {v}")

        execution_guidance = f"""
## 🔧 参数化执行指导
请生成以下参数化函数形式的代码：

def execute_task({', '.join(param_names)}):
    # 执行具体逻辑
    # 从kwargs提取参数
    # 例如: location = kwargs.get('location', '杭州')
    return result_data

参数说明：
{chr(10).join(param_descriptions)}

🚨 必须定义函数后立即调用并赋值：__result__ = execute_task(参数...)"""

    # 构建基础 prompt
    base_prompt = f"""
# AIForge：Python 代码生成和执行助手

# 代码生成规范
{code_rule}

{format_rules}

{execution_guidance}
"""

    # 任务特定格式（仅在需要时添加）
    if task_type and task_type != "general":
        base_prompt += f"\n\n{get_task_specific_format(task_type)}"

    # 用户指令处理
    if user_prompt:
        prompt_header = "# 详细指令" if should_use_detailed_prompt(user_prompt) else "# 任务要求"
        enhanced_prompt = f"{base_prompt}\n\n{prompt_header}\n{user_prompt}"
    else:
        enhanced_prompt = f"{base_prompt}\n\n# 任务要求\n请根据用户指令生成相应的 Python 代码"

    if original_prompt:
        enhanced_prompt = f"{enhanced_prompt}\n\n额外要求：{original_prompt}"

from typing import Optional


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
) -> str:
    """生成增强的系统提示，包含输出格式规范"""

    if optimize_tokens:
        code_rule = """
# 代码生成规则
- 生成的代码必须能在标准 Python 环境中直接执行
- 生成极简代码，无注释，无空行
- 使用最短变量名(a,b,c,d等)
- 使用预装库：requests, BeautifulSoup, pandas, numpy 等
- 实现完整的错误处理和异常捕获
"""
    else:
        code_rule = """
# 代码生成规则
- 生成的代码必须能在标准 Python 环境中直接执行
- 使用预装库：requests, BeautifulSoup, pandas, numpy 等
- 实现完整的错误处理和异常捕获
"""

    # 将格式要求提前并加强
    critical_format_rules = """
🚨 CRITICAL: 必须严格遵守的格式要求 🚨

1. __result__ 变量必须是字典格式，绝不能是字符串
2. 字典必须包含以下字段：
   - "data": 实际数据（成功时）或 null（失败时）
   - "status": "success" 或 "error"
   - "summary": 简短描述
   - "metadata": 包含timestamp等信息

3. 示例格式：
   成功时：__result__ = {"data": 实际数据, "status": "success", "summary": "操作成功", "metadata": {...}}
   失败时：__result__ = {"data": null, "status": "error", "summary": "错误描述", "metadata": {...}}

4. 严禁使用：__result__ = "字符串内容"
"""

    base_prompt = f"""
# 角色定义
你是 AIForge，一个专业的 Python 代码生成和执行助手。

# 输出格式规范
你的回答必须严格遵循以下格式：

## 代码块格式
- 使用标准 Markdown 代码块格式：```python ... ```
- 将最终结果赋值给 __result__ 变量

{critical_format_rules}

{code_rule}

"""

    # 强化的质量要求
    enhanced_quality_rules = """
# 🔥 强制执行的结果质量要求 🔥

- 如果数据获取成功：status="success", data=实际数据
- 如果数据获取失败：status="error", data=null, summary包含错误原因
- data字段在成功时不能为空、null或错误信息
- 错误信息只能放在summary字段中
- 绝对禁止返回字符串格式的__result__

违反格式要求的代码将被拒绝执行！
"""

    # 只有在提供了task_type时才添加任务特定格式
    if task_type:
        task_format = get_task_specific_format(task_type)
        enhanced_prompt = f"{base_prompt}\n{task_format}\n{enhanced_quality_rules}"
    else:
        enhanced_prompt = f"{base_prompt}\n{enhanced_quality_rules}"

    if user_prompt and should_use_detailed_prompt(user_prompt):
        return f"{enhanced_prompt}\n\n# 用户详细指令\n请严格按照以上格式要求执行：\n{user_prompt}"
    else:
        return f"{enhanced_prompt}\n\n# 任务要求\n{user_prompt or '请根据用户指令生成相应的 Python 代码'}"

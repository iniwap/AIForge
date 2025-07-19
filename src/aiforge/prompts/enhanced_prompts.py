import re
from typing import Optional


def detect_task_type(instruction: str) -> str:
    """检测任务类型"""
    if not instruction:
        return "general"

    instruction_lower = instruction.lower()

    # 搜索相关任务
    if re.search(r"搜索|search|爬虫|crawler|抓取|scrape", instruction_lower):
        return "web_search"

    # 数据分析任务
    if re.search(r"分析|analysis|统计|statistics|可视化|visualization", instruction_lower):
        return "data_analysis"

    # 文件处理任务
    if re.search(r"处理.*文件|file.*processing|批量.*操作", instruction_lower):
        return "file_processing"

    # API调用任务
    if re.search(r"api|接口|调用|请求|request", instruction_lower):
        return "api_call"

    return "general"


def get_task_specific_format(task_type: str) -> str:
    """获取任务特定的输出格式要求"""
    formats = {
        "web_search": """
# 搜索任务输出格式
__result__ = {
    "results": [{"title": "...", "url": "...", "content": "..."}],
    "total_count": int,
    "query": "原始查询",
    "source": "搜索引擎名称",
    "metadata": {"timestamp": "...", "status": "success"}
}""",
        "data_analysis": """
# 数据分析任务输出格式
__result__ = {
    "analysis": {"key_findings": "...", "trends": "..."},
    "data": processed_data,
    "summary": {"total_records": int, "key_metrics": {}},
    "visualizations": ["chart1.png", "chart2.png"],
    "metadata": {"timestamp": "...", "data_source": "..."}
}""",
        "file_processing": """
# 文件处理任务输出格式
__result__ = {
    "processed_files": [{"file": "...", "status": "success", "size": int}],
    "summary": {"total_files": int, "success_count": int, "error_count": int},
    "errors": [{"file": "...", "error": "..."}],
    "metadata": {"timestamp": "...", "operation": "..."}
}""",
        "api_call": """
# API调用任务输出格式
__result__ = {
    "response_data": api_response,
    "status_code": int,
    "headers": response_headers,
    "summary": {"success": bool, "response_time": float},
    "metadata": {"endpoint": "...", "timestamp": "..."}
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
    user_prompt: Optional[str] = None, optimize_tokens: bool = True
) -> str:
    """生成增强的系统提示，包含输出格式规范"""

    # 检测任务类型
    task_type = detect_task_type(user_prompt or "")

    if optimize_tokens:
        code_rule = """
# 代码生成规则
- 生成的代码必须能在标准 Python 环境中直接执行
- 生成极简代码，无注释，无空行
- 使用最短变量名(a,b,c,d等)
- 使用预装库：requests, BeautifulSoup, pandas, numpy 等
- 实现完整的错误处理和异常捕获
- 输出清晰的状态信息和进度提示"
"""
    else:
        code_rule = """
# 代码生成规则
- 生成的代码必须能在标准 Python 环境中直接执行
- 使用预装库：requests, BeautifulSoup, pandas, numpy 等
- 实现完整的错误处理和异常捕获
- 输出清晰的状态信息和进度提示"
"""

    base_prompt = f"""
# 角色定义
你是 AIForge，一个专业的 Python 代码生成和执行助手。

# 输出格式规范
你的回答必须严格遵循以下格式：

## 代码块格式
- 使用标准 Markdown 代码块格式：```python ... ```，不要输出任何解释性文字
- 每个代码块应该是完整可执行的
- 将最终结果赋值给 __result__ 变量
- 包含适当的错误处理

## 结果处理规范
- 确保 __result__ 包含结构化数据
- 所有结果必须可以被 JSON 序列化
- 包含必要的元数据信息（时间戳、状态等）

{code_rule}

# 执行环境
- Python 解释器已预装常用数据处理和网络库
- 支持文件读写和网络访问
- 具有完整的异常处理机制
"""
    result_quality_rules = """
# 结果质量要求
- 确保返回的数据是真实、准确的
- 如果无法获取真实数据，应返回错误状态，严禁返回虚假、模拟数据
- 使用标准的结果格式：{"data": 实际数据, "status": "success/error", "summary": "描述"}
"""
    # 添加任务特定的格式要求、添加通用规则
    task_format = get_task_specific_format(task_type)
    enhanced_prompt = f"{base_prompt}\\n{task_format}\\n{result_quality_rules}"

    if user_prompt and should_use_detailed_prompt(user_prompt):
        return f"{enhanced_prompt}\\n\\n# 用户详细指令\\n请严格按照以下指令执行：\\n{user_prompt}"
    else:
        return f"{enhanced_prompt}\\n\\n# 任务要求\\n{user_prompt or '请根据用户指令生成相应的 Python 代码'}"

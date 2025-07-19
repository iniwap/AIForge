import json
import re
from typing import Dict, Any
from ..llm.llm_client import AIForgeLLMClient


class InstructionAnalyzer:
    """指令分析器 - 将自然语言转换为标准化指令"""

    def __init__(self, llm_client: AIForgeLLMClient):
        self.llm_client = llm_client

        # 任务类型映射
        self.task_type_patterns = {
            # 数据获取类
            "web_search": [
                "搜索",
                "search",
                "查找",
                "爬取",
                "crawl",
                "scrape",
                "抓取",
                "新闻",
                "news",
            ],
            "web_scraping": ["爬虫", "spider", "抓取网页", "提取数据", "网页内容"],
            "api_data_fetch": ["api", "接口", "获取数据", "fetch", "调用接口"],
            "database_query": ["数据库", "database", "查询", "query", "sql"],
            # 数据处理类
            "data_analysis": ["分析", "analyze", "统计", "statistics", "报告", "report"],
            "data_processing": ["处理", "process", "转换", "transform", "清洗", "clean"],
            "data_visualization": ["可视化", "visualization", "图表", "chart", "绘图", "plot"],
            # 文件操作类
            "file_operation": ["文件", "file", "读取", "read", "写入", "write", "保存", "save"],
            "file_batch_processing": ["批量", "batch", "批处理", "多个文件"],
            "document_parsing": ["解析", "parse", "提取", "extract", "文档", "document"],
            # 网络通信类
            "web_request": ["网页", "webpage", "url", "html", "http", "requests"],
            "webhook_handler": ["webhook", "回调", "callback", "事件", "event"],
            # 自动化任务类
            "automation": ["自动化", "automation", "定时", "schedule", "任务", "task"],
            "monitoring": ["监控", "monitor", "告警", "alert", "检查", "check"],
            # 内容生成类
            "content_generation": ["生成", "generate", "创建", "create", "写作", "writing"],
            "code_generation": ["代码生成", "code generation", "编程", "programming"],
            # 系统集成类
            "integration": ["集成", "integration", "同步", "sync", "连接", "connect"],
        }

    def analyze_instruction(self, user_input: str) -> Dict[str, Any]:
        """分析用户指令，返回标准化的指令结构"""
        # 首先尝试本地分析
        local_analysis = self._local_analyze(user_input)
        if local_analysis["confidence"] > 0.7:
            return local_analysis

        # 如果本地分析置信度不高，使用AI分析
        analysis_prompt = self._get_analysis_prompt()
        full_prompt = f"{analysis_prompt}\\n\\n用户指令: {user_input}"

        try:
            response = self.llm_client.generate_code(full_prompt, "")
            ai_analysis = self._parse_standardized_instruction(response)

            # 合并本地分析和AI分析结果
            return self._merge_analysis(local_analysis, ai_analysis)
        except Exception:
            # AI分析失败时回退到本地分析
            return local_analysis

    def _local_analyze(self, instruction: str) -> Dict[str, Any]:
        """本地指令分析"""
        instruction_lower = instruction.lower()

        # 计算每种任务类型的匹配分数
        type_scores = {}
        for task_type, keywords in self.task_type_patterns.items():
            score = sum(1 for keyword in keywords if keyword in instruction_lower)
            if score > 0:
                type_scores[task_type] = score

        if not type_scores:
            return self._get_default_analysis(instruction)

        # 获取最高分的任务类型
        best_task_type = max(type_scores.items(), key=lambda x: x[1])[0]
        confidence = min(type_scores[best_task_type] / 3.0, 1.0)  # 标准化置信度

        return {
            "task_type": best_task_type,
            "action": self._infer_action(instruction, best_task_type),
            "target": self._extract_target(instruction),
            "parameters": self._extract_parameters(instruction, best_task_type),
            "output_format": self._infer_output_format(instruction),
            "cache_key": f"{best_task_type}_{hash(instruction) % 10000}",
            "confidence": confidence,
        }

    def _infer_action(self, instruction: str, task_type: str) -> str:
        """推断具体动作"""
        action_patterns = {
            "web_search": "search",
            "web_scraping": "extract",
            "api_data_fetch": "fetch",
            "database_query": "query",
            "data_analysis": "analyze",
            "data_processing": "process",
            "data_visualization": "plot",
            "file_operation": "process",
            "file_batch_processing": "batch_process",
            "document_parsing": "parse",
            "web_request": "request",
            "webhook_handler": "handle",
            "automation": "automate",
            "monitoring": "monitor",
            "content_generation": "generate",
            "code_generation": "generate",
            "integration": "integrate",
        }
        return action_patterns.get(task_type, "process")

    def _extract_target(self, instruction: str) -> str:
        """提取操作目标"""
        # 简单的目标提取逻辑
        return instruction[:100]  # 取前100个字符作为目标描述

    def _extract_parameters(self, instruction: str, task_type: str) -> Dict[str, Any]:
        """提取参数"""
        params = {}

        # 根据任务类型提取特定参数
        if task_type in ["web_search", "web_scraping"]:
            # 提取查询关键词
            query_match = re.search(r'["""]([^"""]+)["""]', instruction)
            if query_match:
                params["query"] = query_match.group(1)

            # 提取数量限制
            num_match = re.search(r"(\\d+)", instruction)
            if num_match:
                params["max_results"] = int(num_match.group(1))

        elif task_type == "file_operation":
            # 提取文件路径
            file_match = re.search(r"([^\\s]+\\.[a-zA-Z]+)", instruction)
            if file_match:
                params["file_path"] = file_match.group(1)

        return params

    def _infer_output_format(self, instruction: str) -> str:
        """推断输出格式"""
        if any(word in instruction.lower() for word in ["json", "字典", "dict"]):
            return "json"
        elif any(word in instruction.lower() for word in ["列表", "list", "数组"]):
            return "list"
        elif any(word in instruction.lower() for word in ["表格", "table", "csv"]):
            return "table"
        else:
            return "general"

    def _get_default_analysis(self, instruction: str) -> Dict[str, Any]:
        """获取默认分析结果"""
        return {
            "task_type": "general",
            "action": "process",
            "target": instruction[:100],
            "parameters": {},
            "output_format": "general",
            "cache_key": f"general_{hash(instruction) % 10000}",
            "confidence": 0.3,
        }

    def _get_analysis_prompt(self) -> str:
        """获取指令分析的系统提示词"""
        return """
# 角色定义
你是 AIForge 指令分析器，负责将用户的自然语言指令转换为标准化的指令结构。

# 任务要求
分析用户指令，返回以下JSON格式的标准化指令：

{
    "task_type": "任务类型",
    "action": "具体动作",
    "target": "操作目标",
    "parameters": {
        "key1": "value1",
        "key2": "value2"
    },
    "output_format": "期望的输出格式",
    "cache_key": "用于缓存的标准化键"
}

# 任务类型包括
- web_search: 网络搜索
- web_scraping: 网页爬取
- api_data_fetch: API数据获取
- database_query: 数据库查询
- data_analysis: 数据分析
- data_processing: 数据处理
- data_visualization: 数据可视化
- file_operation: 文件操作
- web_request: 网页请求
- automation: 自动化任务
- content_generation: 内容生成
- integration: 系统集成

请严格按照JSON格式返回，不要包含其他解释文字。
"""

    def _parse_standardized_instruction(self, response: str) -> Dict[str, Any]:
        """解析AI返回的标准化指令"""
        # 提取JSON内容
        json_match = re.search(r"\\{.*\\}", response, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(0))
            except json.JSONDecodeError:
                pass

        # 解析失败时返回默认结构
        return self._get_default_analysis(response[:100])

    def _merge_analysis(self, local: Dict[str, Any], ai: Dict[str, Any]) -> Dict[str, Any]:
        """合并本地分析和AI分析结果"""
        # 如果AI分析结果更完整，优先使用AI结果
        if len(ai.get("parameters", {})) > len(local.get("parameters", {})):
            return ai
        return local

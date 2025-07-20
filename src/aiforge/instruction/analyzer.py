import json
import re
from typing import Dict, Any, List
from ..llm.llm_client import AIForgeLLMClient


class InstructionAnalyzer:
    """指令分析器 - 将自然语言转换为标准化指令"""

    def __init__(self, llm_client: AIForgeLLMClient):
        self.llm_client = llm_client

        # 标准化的任务类型定义 - 完整覆盖常见场景
        self.standardized_patterns = {
            "data_fetch": {
                "keywords": [
                    "搜索",
                    "search",
                    "获取",
                    "fetch",
                    "查找",
                    "天气",
                    "weather",
                    "新闻",
                    "news",
                    "api",
                    "接口",
                    "爬取",
                    "crawl",
                ],
                "actions": ["search", "fetch", "get", "crawl"],
                "output_formats": ["json", "list", "dict"],
                "common_params": ["query", "url", "max_results", "city", "topic"],
            },
            "data_process": {
                "keywords": [
                    "分析",
                    "analyze",
                    "处理",
                    "process",
                    "计算",
                    "统计",
                    "转换",
                    "transform",
                ],
                "actions": ["analyze", "process", "calculate", "transform"],
                "output_formats": ["json", "table", "report"],
                "common_params": ["data_source", "method", "format"],
            },
            "file_operation": {
                "keywords": [
                    "文件",
                    "file",
                    "读取",
                    "read",
                    "写入",
                    "write",
                    "保存",
                    "save",
                    "批量",
                    "batch",
                ],
                "actions": ["read", "write", "save", "process"],
                "output_formats": ["file", "json", "text"],
                "common_params": ["file_path", "format", "encoding"],
            },
            "automation": {
                "keywords": [
                    "自动化",
                    "automation",
                    "定时",
                    "schedule",
                    "监控",
                    "monitor",
                    "任务",
                    "task",
                ],
                "actions": ["automate", "schedule", "monitor", "execute"],
                "output_formats": ["status", "log", "report"],
                "common_params": ["interval", "condition", "action"],
            },
            "content_generation": {
                "keywords": [
                    "生成",
                    "generate",
                    "创建",
                    "create",
                    "写作",
                    "writing",
                    "报告",
                    "report",
                ],
                "actions": ["generate", "create", "write", "compose"],
                "output_formats": ["text", "document", "html"],
                "common_params": ["template", "content", "style"],
            },
        }

    def analyze_instruction(self, user_input: str) -> Dict[str, Any]:
        """分析用户指令，优先本地分析"""
        # 本地分析
        local_analysis = self._local_analyze(user_input)

        # 降低AI调用阈值 - 本地分析置信度 > 0.5 就直接使用
        if local_analysis["confidence"] > 0.5:
            return local_analysis

        # 置信度不够才使用AI分析
        try:
            analysis_prompt = self._get_analysis_prompt()
            response = self.llm_client.generate_code(
                f"{analysis_prompt}\n\n用户指令: {user_input}", ""
            )
            ai_analysis = self._parse_standardized_instruction(response)

            # 合并本地和AI分析结果
            return self._merge_analysis(local_analysis, ai_analysis)
        except Exception:
            return local_analysis

    def _local_analyze(self, instruction: str) -> Dict[str, Any]:
        """增强的本地指令分析 - 提供完整的标准化输出"""
        instruction_lower = instruction.lower()

        # 计算每种任务类型的匹配分数
        type_scores = {}
        best_match_details = {}

        for task_type, pattern_data in self.standardized_patterns.items():
            score = sum(1 for keyword in pattern_data["keywords"] if keyword in instruction_lower)
            if score > 0:
                type_scores[task_type] = score
                best_match_details[task_type] = pattern_data

        if not type_scores:
            return self._get_default_analysis(instruction)

        # 获取最高分的任务类型
        best_task_type = max(type_scores.items(), key=lambda x: x[1])[0]
        best_pattern = best_match_details[best_task_type]

        # 提高置信度计算的准确性
        max_possible_score = len(best_pattern["keywords"])
        confidence = min(type_scores[best_task_type] / max_possible_score * 2, 1.0)

        # 生成完整的标准化指令
        standardized = {
            "task_type": best_task_type,
            "action": self._smart_infer_action(instruction, best_pattern["actions"]),
            "target": self._extract_target(instruction),
            "parameters": self._smart_extract_parameters(
                instruction, best_pattern["common_params"]
            ),
            "output_format": self._smart_infer_output_format(
                instruction, best_pattern["output_formats"]
            ),
            "cache_key": self._generate_semantic_cache_key(best_task_type, instruction),
            "confidence": confidence,
            "source": "local_analysis",
        }

        return standardized

    def _smart_infer_action(self, instruction: str, possible_actions: List[str]) -> str:
        """智能推断动作"""
        instruction_lower = instruction.lower()

        # 动作关键词映射
        action_keywords = {
            "search": ["搜索", "查找", "search", "find"],
            "fetch": ["获取", "fetch", "get", "retrieve"],
            "analyze": ["分析", "analyze", "统计", "calculate"],
            "process": ["处理", "process", "转换", "transform"],
            "generate": ["生成", "generate", "创建", "create"],
            "save": ["保存", "save", "写入", "write"],
        }

        for action in possible_actions:
            if action in action_keywords:
                if any(keyword in instruction_lower for keyword in action_keywords[action]):
                    return action

        return possible_actions[0] if possible_actions else "process"

    def _extract_target(self, instruction: str) -> str:
        """提取操作目标"""
        return instruction[:100]  # 取前100个字符作为目标描述

    def _smart_extract_parameters(
        self, instruction: str, common_params: List[str]
    ) -> Dict[str, Any]:
        """智能提取参数"""
        params = {}

        # 通用参数提取规则
        param_patterns = {
            "query": [
                r'["""]([^"""]+)["""]',
                r"搜索(.+?)(?:的|，|。|$)",
                r"查找(.+?)(?:的|，|。|$)",
            ],
            "city": [r"(.+?)(?:天气|weather)", r"(.+?)市", r"(.+?)(?:的天气|weather)"],
            "max_results": [r"(\d+)(?:条|个|项)", r"最多(\d+)", r"前(\d+)"],
            "file_path": [r"([^\s]+\.[a-zA-Z]+)", r"文件(.+?)(?:的|，|。|$)"],
            "url": [r"(https?://[^\s]+)"],
        }

        for param in common_params:
            if param in param_patterns:
                for pattern in param_patterns[param]:
                    match = re.search(pattern, instruction)
                    if match:
                        value = match.group(1).strip()
                        if param == "max_results":
                            params[param] = int(value)
                        else:
                            params[param] = value
                        break

        return params

    def _smart_infer_output_format(self, instruction: str, possible_formats: List[str]) -> str:
        """智能推断输出格式"""
        instruction_lower = instruction.lower()

        format_keywords = {
            "json": ["json", "字典", "dict"],
            "list": ["列表", "list", "数组"],
            "table": ["表格", "table", "csv"],
            "text": ["文本", "text", "字符串"],
            "file": ["文件", "file"],
            "report": ["报告", "report"],
        }

        for fmt in possible_formats:
            if fmt in format_keywords:
                if any(keyword in instruction_lower for keyword in format_keywords[fmt]):
                    return fmt

        return "json"  # 默认返回json格式

    def _generate_semantic_cache_key(self, task_type: str, instruction: str) -> str:
        """生成语义化的缓存键"""
        # 提取关键词生成更稳定的缓存键
        key_words = []

        # 根据任务类型提取关键词
        if task_type == "data_fetch":
            # 提取查询主题
            for pattern in [
                r'["""]([^"""]+)["""]',
                r"搜索(.+?)(?:的|，|。|$)",
                r"获取(.+?)(?:的|，|。|$)",
            ]:
                match = re.search(pattern, instruction)
                if match:
                    key_words.append(match.group(1).strip())
                    break

        # 生成稳定的哈希
        content = f"{task_type}_{' '.join(key_words)}" if key_words else instruction[:50]
        return f"{task_type}_{hash(content) % 100000}"

    def _get_default_analysis(self, instruction: str) -> Dict[str, Any]:
        """获取默认分析结果"""
        return {
            "task_type": "general",
            "action": "process",
            "target": instruction[:100],
            "parameters": {},
            "output_format": "json",
            "cache_key": f"general_{hash(instruction) % 10000}",
            "confidence": 0.3,
            "source": "default",
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
- data_fetch: 数据获取（搜索、天气、新闻、API等）
- data_process: 数据处理（分析、转换、计算等）
- file_operation: 文件操作（读取、写入、批量处理等）
- automation: 自动化任务（定时、监控等）
- content_generation: 内容生成（写作、报告等）

请严格按照JSON格式返回，不要包含其他解释文字。
"""

    def _parse_standardized_instruction(self, response: str) -> Dict[str, Any]:
        """解析AI返回的标准化指令"""
        # 先尝试提取```json代码块
        code_block_match = re.search(r"```json\s*(\{.*?\})\s*```", response, re.DOTALL)
        if code_block_match:
            try:
                return json.loads(code_block_match.group(1))
            except json.JSONDecodeError:
                pass

        # 回退到直接提取JSON
        json_match = re.search(r"\{.*\}", response, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(0))
            except json.JSONDecodeError:
                pass

        # 解析失败时返回默认结构
        return self._get_default_analysis(response[:100])

    def _merge_analysis(self, local: Dict[str, Any], ai: Dict[str, Any]) -> Dict[str, Any]:
        """合并本地分析和AI分析结果"""

        # 检查AI分析是否有效
        if self._is_ai_analysis_valid(ai):
            ai["source"] = "ai_analysis"
            ai["confidence"] = 0.9
            return ai

        local["source"] = "local_analysis"
        return local

    def _is_ai_analysis_valid(self, ai_analysis: Dict[str, Any]) -> bool:
        """验证AI分析结果的有效性"""
        # 1. 检查必要字段是否存在
        required_fields = ["task_type", "action", "target"]
        if not all(field in ai_analysis for field in required_fields):
            return False

        # 2. 检查task_type是否在已知类型中
        known_task_types = set(self.standardized_patterns.keys()) | {"general"}  # 修复这里
        if ai_analysis.get("task_type") not in known_task_types:
            return False

        # 3. 检查参数是否合理（非空且有意义）
        parameters = ai_analysis.get("parameters", {})
        if parameters:
            # 检查参数值是否有意义（非空字符串等）
            for key, value in parameters.items():
                if isinstance(value, str) and not value.strip():
                    return False

        # 4. 检查是否比本地分析更准确（可选的额外验证）
        return True

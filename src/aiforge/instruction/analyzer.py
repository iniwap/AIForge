import json
import re
from typing import Dict, Any, List
from ..llm.llm_client import AIForgeLLMClient


class InstructionAnalyzer:
    """指令分析器"""

    def __init__(self, llm_client: AIForgeLLMClient):
        self.llm_client = llm_client

        # 标准化的任务类型定义
        self.standardized_patterns = {
            "data_fetch": {
                "keywords": [
                    "搜索",
                    "search",
                    "获取",
                    "fetch",
                    "查找",
                    "新闻",
                    "news",
                    "api",
                    "接口",
                    "爬取",
                    "crawl",
                ],
                "actions": ["search", "fetch", "get", "crawl"],
                "output_formats": ["json", "list", "dict"],
                "common_params": ["query", "url", "max_results", "topic"],
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

    def local_analyze_instruction(self, instruction: str) -> Dict[str, Any]:
        """本地指令分析"""
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
            "cache_key": self._generate_semantic_cache_key(
                best_task_type,
                instruction,
                self._smart_extract_parameters(instruction, best_pattern["common_params"]),
            ),
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
            "query": {
                "patterns": [
                    r'["""]([^"""]+)["""]',
                    r"搜索(.+?)(?:的|，|。|$)",
                    r"查找(.+?)(?:的|，|。|$)",
                ],
                "type": "str",
                "description": "搜索查询内容",
            },
            "max_results": {
                "patterns": [r"(\d+)(?:条|个|项)", r"最多(\d+)", r"前(\d+)"],
                "type": "int",
                "description": "最大结果数量",
            },
            "file_path": {
                "patterns": [r"([^\s]+\.[a-zA-Z]+)", r"文件(.+?)(?:的|，|。|$)"],
                "type": "str",
                "description": "文件路径",
            },
            "url": {"patterns": [r"(https?://[^\s]+)"], "type": "str", "description": "URL地址"},
        }

        for param in common_params:
            if param in param_patterns:
                param_config = param_patterns[param]
                for pattern in param_config["patterns"]:
                    match = re.search(pattern, instruction)
                    if match:
                        value = match.group(1).strip()
                        if param_config["type"] == "int":
                            value = int(value)

                        params[param] = {
                            "value": value,
                            "type": param_config["type"],
                            "description": param_config["description"],
                        }
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

    def _generate_semantic_cache_key(
        self, task_type: str, instruction: str, parameters: Dict = None
    ) -> str:
        """基于参数化指令生成语义化缓存键"""
        key_components = [task_type]

        # 优先使用 required_parameters 生成稳定的缓存键
        if parameters:
            # 提取参数值，按参数名排序确保一致性
            param_values = []
            sorted_params = sorted(parameters.items())

            for param_name, param_info in sorted_params:
                if isinstance(param_info, dict) and "value" in param_info:
                    value = param_info["value"]
                    # 标准化参数值
                    if isinstance(value, str):
                        value = value.lower().strip()
                    param_values.append(f"{param_name}:{value}")
                elif param_info is not None:
                    param_values.append(f"{param_name}:{str(param_info).lower()}")

            if param_values:
                key_components.extend(param_values)

        # 如果没有参数，使用指令内容
        if len(key_components) == 1:
            key_components.append(instruction[:50])

        # 生成稳定的哈希
        content = "_".join(key_components)
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

    def get_analysis_prompt(self) -> str:
        return """
# 角色定义
你是 AIForge 智能任务分析器，负责理解用户指令并分析完成任务所需的必要信息。

# 核心任务
分析用户指令，思考：要完成这个任务，我需要哪些具体信息作为输入参数？

# 分析步骤
1. 理解用户想要完成什么任务
2. 思考完成这个任务的必要条件和输入信息
3. 从用户指令中提取这些信息的具体值
4. 将缺失但必要的信息标记为需要默认值或推断

# 输出格式
{
    "task_type": "任务类型",
    "action": "具体动作",
    "target": "任务描述",
    "required_parameters": {
        "param_name": {
            "value": "从指令中提取的值或null",
            "type": "参数类型",
            "description": "参数用途说明",
            "required": true/false,
            "default": "默认值或null"
        }
    },
    "execution_logic": "完成任务的基本逻辑描述",
    "output_format": "期望输出格式"
}

# 分析原则
- 专注于任务完成的必要性，而非指令的字面内容
- 参数应该是执行任务的最小必要集合
- 优先从指令中提取具体值，无法提取时考虑合理默认值
- 参数命名应该清晰反映其在任务中的作用

# 示例思考过程
用户指令："北京今天的天气如何"
思考：要获取天气信息，我需要知道：
1. 地点（必需）- 从指令提取："北京"
2. 时间（必需）- 从指令提取："今天"
3. 信息类型（必需）- 从指令推断："天气"

请严格按照JSON格式返回分析结果。
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
        # 1. 检查必要字段
        required_fields = ["task_type", "action", "target"]
        if not all(field in ai_analysis for field in required_fields):
            return False

        # 2. 检查task_type是否有效（支持动态类型）
        task_type = ai_analysis.get("task_type")
        if not task_type or not isinstance(task_type, str) or not task_type.strip():
            return False

        # 注册新的任务类型
        if hasattr(self, "task_type_manager"):
            self.task_type_manager.register_task_type(task_type, ai_analysis)

        # 其余验证逻辑保持不变...
        return True

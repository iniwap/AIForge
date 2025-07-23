import json
import re
from typing import Dict, Any, List
from ..llm.llm_client import AIForgeLLMClient


class InstructionAnalyzer:
    """指令分析器"""

    def __init__(self, llm_client: AIForgeLLMClient):
        self.llm_client = llm_client
        self.task_type_manager = None
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
            "direct_response": {
                "keywords": [
                    # 问答类
                    "什么是",
                    "如何",
                    "为什么",
                    "解释",
                    "介绍",
                    "定义",
                    "概念",
                    "原理",
                    "区别",
                    "比较",
                    "what",
                    "how",
                    "why",
                    "explain",
                    "describe",
                    "define",
                    "concept",
                    # 创作类
                    "写一篇",
                    "写一个",
                    "创作",
                    "编写",
                    "起草",
                    "写作",
                    "撰写",
                    "write",
                    "compose",
                    "draft",
                    "create content",
                    # 翻译类
                    "翻译",
                    "translate",
                    "转换为",
                    "改写为",
                    "用...语言",
                    # 总结分析类（纯文本）
                    "总结",
                    "概括",
                    "归纳",
                    "分析这段",
                    "解读",
                    "summarize",
                    "analyze this text",
                    "interpret",
                    # 建议咨询类
                    "建议",
                    "推荐",
                    "意见",
                    "看法",
                    "评价",
                    "怎么看",
                    "suggest",
                    "recommend",
                    "opinion",
                    "advice",
                ],
                "exclude_keywords": [
                    # 时效性关键词
                    "今天",
                    "现在",
                    "最新",
                    "当前",
                    "实时",
                    "目前",
                    "天气",
                    "股价",
                    "新闻",
                    "汇率",
                    "价格",
                    "状态",
                ],
                "actions": ["respond", "answer", "create", "translate", "summarize", "suggest"],
                "output_formats": ["text", "markdown"],
                "common_params": ["content", "style"],
            },
        }

    def local_analyze_instruction(self, instruction: str) -> Dict[str, Any]:
        """本地指令分析"""
        instruction_lower = instruction.lower()

        # 计算每种任务类型的匹配分数
        type_scores = {}
        best_match_details = {}

        for task_type, pattern_data in self.standardized_patterns.items():
            # 检查排除关键词
            exclude_keywords = pattern_data.get("exclude_keywords", [])
            if any(exclude_keyword in instruction_lower for exclude_keyword in exclude_keywords):
                continue  # 跳过包含排除关键词的任务类型

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
            "respond": ["回答", "respond", "解释", "explain"],
            "answer": ["回答", "answer", "解答", "回复"],
            "translate": ["翻译", "translate", "转换", "convert"],
            "summarize": ["总结", "summarize", "概括", "归纳"],
            "suggest": ["建议", "suggest", "推荐", "recommend"],
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
            "content": {
                "patterns": [r"内容[：:](.+?)(?:的|，|。|$)", r"文本[：:](.+?)(?:的|，|。|$)"],
                "type": "str",
                "description": "处理内容",
            },
            "style": {
                "patterns": [r"风格[：:](.+?)(?:的|，|。|$)", r"样式[：:](.+?)(?:的|，|。|$)"],
                "type": "str",
                "description": "输出风格",
            },
        }

        for param in common_params:
            if param in param_patterns:
                param_config = param_patterns[param]
                for pattern in param_config["patterns"]:
                    match = re.search(pattern, instruction)
                    if match:
                        value = match.group(1).strip()
                        if param_config["type"] == "int":
                            try:
                                value = int(value)
                            except ValueError:
                                continue

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
            "markdown": ["markdown", "md", "格式化"],
            "file": ["文件", "file"],
            "report": ["报告", "report"],
        }

        for fmt in possible_formats:
            if fmt in format_keywords:
                if any(keyword in instruction_lower for keyword in format_keywords[fmt]):
                    return fmt

        # 根据任务类型返回默认格式
        if "direct_response" in possible_formats:
            return "text"
        return "json"

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

    def get_analysis_prompt(self, include_guidance: bool = True) -> str:
        """获取AI分析提示词"""
        # 构建基础提示词内容
        base_sections = self._build_base_prompt_sections()

        # 如果需要引导信息，添加任务类型引导
        if include_guidance:
            builtin_types = list(self.standardized_patterns.keys())
            guidance_info = self._build_task_type_guidance(builtin_types)
            return self._assemble_prompt_with_guidance(base_sections, guidance_info)
        else:
            return self._assemble_basic_prompt(base_sections)

    def _build_base_prompt_sections(self) -> Dict[str, str]:
        """构建基础提示词各个部分"""
        return {
            "role": "你是 AIForge 智能任务分析器，负责理解用户指令并分析完成任务所需的必要信息。",
            "execution_mode": """
## 直接响应类型特征：
- 纯知识问答、概念解释、定义说明（非时效性）
- 文本创作、写作、翻译、改写
- 历史信息查询、理论分析
- 建议咨询、意见评价（基于已有知识）
- 可以通过AI的知识和语言能力直接完成且不需要最新数据

## 代码执行类型特征：
- 需要访问外部数据源（API、网页、文件系统）
- 需要实时信息获取（天气、股价、新闻、汇率等）
- 需要最新数据的查询和分析
- 需要数据计算、统计、处理、转换
- 需要文件操作、系统交互、自动化任务
""",
            "analysis_steps": """
## 对于直接响应类型：
1. 理解用户想要获得什么信息或内容
2. 确认信息不涉及时效性要求
3. 确认可以通过AI知识直接提供

## 对于代码执行类型：
1. 理解用户想要完成什么任务
2. 识别是否需要最新数据或实时信息
3. 思考完成这个任务的必要条件和输入信息
4. 从用户指令中提取这些信息的具体值
""",
            "output_format": """{
    "task_type": "任务类型",
    "action": "具体动作",
    "target": "任务描述",
    "execution_mode": "direct_ai_response 或 code_generation",
    "confidence": "置信度",
    "reasoning": "判断理由",
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
}""",
            "principles": """
- 专注于任务完成的必要性，而非指令的字面内容
- 参数应该是执行任务的最小必要集合
- 优先从指令中提取具体值，无法提取时考虑合理默认值
- 参数命名应该清晰反映其在任务中的作用
""",
            "examples": """
用户指令："北京今天的天气如何"
思考：要获取天气信息，我需要知道：
1. 地点：北京
2. 时间：今天
3. 信息类型：天气
执行模式：code_generation

用户指令："解释什么是机器学习"
思考：这是纯知识问答，不需要外部数据
执行模式：direct_ai_response
""",
        }

    def _build_task_type_guidance(self, builtin_types: List[str]) -> str:
        """构建任务类型引导信息"""
        # 获取动态类型统计（如果有任务类型管理器）
        guidance_strength = "优先考虑"
        additional_info = ""

        if hasattr(self, "task_type_manager") and self.task_type_manager:
            try:
                # 获取动态类型数量
                dynamic_types = getattr(self.task_type_manager, "dynamic_types", {})
                dynamic_count = len(dynamic_types) if dynamic_types else 0

                # 如果动态类型过多，增强内置类型引导
                if dynamic_count > 10:
                    guidance_strength = "强烈推荐"
                    additional_info = f"\n注意：系统已有{dynamic_count}个动态类型，建议优先使用内置类型以提高性能。"

                # 获取高优先级类型
                high_priority_types = []
                for task_type in builtin_types:
                    priority = self.task_type_manager.get_task_type_priority(task_type)
                    if priority > 80:  # 高优先级阈值
                        high_priority_types.append(f"{task_type}(优先级:{priority})")

                if high_priority_types:
                    additional_info += f"\n高优先级类型：{', '.join(high_priority_types)}"

            except Exception:
                # 如果获取统计信息失败，使用默认设置
                pass

        return f"""
# 任务类型指导
{guidance_strength}使用以下经过验证的内置任务类型：
{builtin_types}

这些内置类型具有以下优势：
- 更高的缓存命中率和执行效率
- 经过充分测试和优化的执行路径
- 更稳定的性能表现和错误处理

仅当用户任务确实属于全新领域且无法归类到现有类型时，才创建新的task_type。{additional_info}
"""

    def _assemble_prompt_with_guidance(
        self, base_sections: Dict[str, str], guidance_info: str
    ) -> str:
        """组装包含引导信息的提示词"""
        return f"""
# 角色定义
{base_sections["role"]}

{guidance_info}

# 执行模式判断
首先判断任务是否可以通过AI直接响应完成：
{base_sections["execution_mode"]}

# 分析步骤
{base_sections["analysis_steps"]}

# 输出格式
{base_sections["output_format"]}

# 分析原则
{base_sections["principles"]}

# 示例思考过程
{base_sections["examples"]}

请严格按照JSON格式返回分析结果。
"""

    def _assemble_basic_prompt(self, base_sections: Dict[str, str]) -> str:
        """组装基础提示词（无引导信息）"""
        return f"""
# 角色定义
{base_sections["role"]}

# 核心任务
分析用户指令，思考：要完成这个任务，我需要哪些具体信息作为输入参数？

# 执行模式判断
首先判断任务是否可以通过AI直接响应完成：
{base_sections["execution_mode"]}

# 分析步骤
{base_sections["analysis_steps"]}

# 输出格式
{base_sections["output_format"]}

# 分析原则
{base_sections["principles"]}

# 示例思考过程
{base_sections["examples"]}

请严格按照JSON格式返回分析结果。
"""

    def parse_standardized_instruction(self, response: str) -> Dict[str, Any]:
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

    def is_ai_analysis_valid(self, ai_analysis: Dict[str, Any]) -> bool:
        """验证AI分析结果的有效性"""
        # 1. 检查必要字段
        required_fields = ["task_type", "action", "target"]
        if not all(field in ai_analysis for field in required_fields):
            return False

        # 2. 检查task_type是否有效
        task_type = ai_analysis.get("task_type")
        if not task_type or not isinstance(task_type, str) or not task_type.strip():
            return False

        # 3. 新增：检查是否使用了推荐的内置类型
        builtin_types = list(self.standardized_patterns.keys())
        is_builtin = task_type in builtin_types

        # 4. 如果不是内置类型，进行额外验证
        if not is_builtin:
            # 检查reasoning字段，确保有充分理由创建新类型
            reasoning = ai_analysis.get("reasoning", "")
            if not reasoning or len(reasoning) < 20:
                print(f"[DEBUG] 新任务类型 '{task_type}' 缺少充分的创建理由")
                return False

            # 检查是否与现有类型过于相似
            if self._is_too_similar_to_existing_types(task_type, builtin_types):
                print(f"[DEBUG] 新任务类型 '{task_type}' 与现有类型过于相似")
                return False

        # 5. 注册新的任务类型（如果有管理器）
        if hasattr(self, "task_type_manager") and self.task_type_manager:
            self.task_type_manager.register_task_type(task_type, ai_analysis)

            # 记录类型使用统计
            if is_builtin:
                print(f"[DEBUG] 使用内置任务类型: {task_type}")
            else:
                print(f"[DEBUG] 创建新任务类型: {task_type}")

        return True

    def _is_too_similar_to_existing_types(self, new_type: str, existing_types: List[str]) -> bool:
        """检查新类型是否与现有类型过于相似"""
        new_type_lower = new_type.lower()

        for existing_type in existing_types:
            existing_lower = existing_type.lower()

            # 检查是否包含相同的关键词
            if any(word in existing_lower for word in new_type_lower.split("_")):
                return True

            # 检查编辑距离（简单实现）
            if self._calculate_similarity(new_type_lower, existing_lower) > 0.7:
                return True

        return False

    def _calculate_similarity(self, str1: str, str2: str) -> float:
        """计算两个字符串的相似度"""
        # 简单的相似度计算（可以使用更复杂的算法）
        if str1 == str2:
            return 1.0

        # 计算公共子串长度
        common_chars = set(str1) & set(str2)
        total_chars = set(str1) | set(str2)

        if not total_chars:
            return 0.0

        return len(common_chars) / len(total_chars)

    def get_task_type_usage_stats(self) -> Dict[str, Any]:
        """获取任务类型使用统计"""
        stats = {
            "builtin_types_usage": {},
            "dynamic_types_usage": {},
            "total_analysis_count": 0,
            "builtin_usage_rate": 0.0,
        }

        if hasattr(self, "task_type_manager") and self.task_type_manager:
            try:
                builtin_types = set(self.standardized_patterns.keys())
                all_types = self.task_type_manager.get_all_task_types()

                builtin_count = 0
                total_count = 0

                for task_type in all_types:
                    priority = self.task_type_manager.get_task_type_priority(task_type)
                    usage_info = {
                        "priority": priority,
                        "estimated_usage": max(0, priority - 50),  # 简单的使用量估算
                    }

                    if task_type in builtin_types:
                        stats["builtin_types_usage"][task_type] = usage_info
                        builtin_count += usage_info["estimated_usage"]
                    else:
                        stats["dynamic_types_usage"][task_type] = usage_info

                    total_count += usage_info["estimated_usage"]

                stats["total_analysis_count"] = total_count
                stats["builtin_usage_rate"] = (
                    builtin_count / total_count if total_count > 0 else 0.0
                )

            except Exception as e:
                print(f"[DEBUG] 获取使用统计失败: {e}")

        return stats

    def recommend_task_type_optimizations(self) -> List[str]:
        """推荐任务类型优化建议"""
        recommendations = []

        try:
            stats = self.get_task_type_usage_stats()
            builtin_rate = stats["builtin_usage_rate"]

            if builtin_rate < 0.6:
                recommendations.append("建议增强内置类型引导，当前内置类型使用率较低")

            if builtin_rate > 0.9:
                recommendations.append("内置类型使用率很高，可以考虑适当放宽新类型创建条件")

            # 检查动态类型数量
            dynamic_count = len(stats["dynamic_types_usage"])
            if dynamic_count > 15:
                recommendations.append(f"动态类型过多({dynamic_count}个)，建议清理低优先级类型")

            # 检查低优先级类型
            low_priority_types = []
            for task_type, info in stats["dynamic_types_usage"].items():
                if info["priority"] < 60:
                    low_priority_types.append(task_type)

            if low_priority_types:
                recommendations.append(
                    f"发现{len(low_priority_types)}个低优先级动态类型，建议考虑移除"
                )

            # 检查内置类型使用分布
            builtin_usage = stats["builtin_types_usage"]
            if builtin_usage:
                unused_builtin = [
                    t for t, info in builtin_usage.items() if info["estimated_usage"] == 0
                ]
                if unused_builtin:
                    recommendations.append(
                        f"内置类型 {unused_builtin} 使用率为0，可能需要优化关键词匹配"
                    )

            if not recommendations:
                recommendations.append("任务类型使用情况良好，无需特殊优化")

        except Exception as e:
            recommendations.append(f"统计分析失败: {str(e)}")

        return recommendations

    def adjust_guidance_strength(self) -> str:
        """根据使用统计动态调整引导强度"""
        try:
            stats = self.get_task_type_usage_stats()
            builtin_rate = stats["builtin_usage_rate"]
            dynamic_count = len(stats["dynamic_types_usage"])

            # 根据统计数据调整引导强度
            if builtin_rate < 0.5 or dynamic_count > 20:
                return "强烈推荐"
            elif builtin_rate > 0.8 and dynamic_count < 5:
                return "可以考虑"
            else:
                return "优先考虑"

        except Exception:
            return "优先考虑"

    def get_adaptive_analysis_prompt(self) -> str:
        """获取自适应的分析提示词"""
        builtin_types = list(self.standardized_patterns.keys())
        guidance_strength = self.adjust_guidance_strength()

        # 构建自适应引导信息
        adaptive_guidance = f"""
# 任务类型指导（自适应模式）
{guidance_strength}使用以下经过验证的内置任务类型：
{builtin_types}

系统状态：
- 当前引导强度：{guidance_strength}
- 内置类型使用率：{self.get_task_type_usage_stats().get('builtin_usage_rate', 0):.1%}

这些内置类型具有更高的缓存命中率和执行效率。
"""

        # 其余提示词内容保持不变...
        return self._assemble_prompt_with_guidance(
            self._build_base_prompt_sections(), adaptive_guidance
        )

    def _get_task_type_recommendations(self) -> Dict[str, Any]:
        """获取任务类型推荐信息"""
        recommendations = {
            "builtin_types": list(self.standardized_patterns.keys()),
            "type_descriptions": {},
            "usage_stats": {},
        }

        # 添加类型描述
        for task_type, pattern_data in self.standardized_patterns.items():
            recommendations["type_descriptions"][task_type] = {
                "keywords": pattern_data["keywords"][:5],  # 只显示前5个关键词
                "actions": pattern_data["actions"],
                "common_use_cases": self._get_use_cases_for_type(task_type),
            }

        # 获取使用统计（如果有任务类型管理器）
        if hasattr(self, "task_type_manager") and self.task_type_manager:
            try:
                for task_type in recommendations["builtin_types"]:
                    priority = self.task_type_manager.get_task_type_priority(task_type)
                    recommendations["usage_stats"][task_type] = {
                        "priority": priority,
                        "is_high_priority": priority > 80,
                    }
            except Exception:
                pass

        return recommendations

    def _get_use_cases_for_type(self, task_type: str) -> List[str]:
        """获取任务类型的常见用例"""
        use_cases = {
            "data_fetch": ["搜索网页内容", "获取API数据", "爬取新闻信息"],
            "data_process": ["数据分析", "统计计算", "格式转换"],
            "file_operation": ["读写文件", "批量处理", "文档操作"],
            "automation": ["定时任务", "系统监控", "自动化流程"],
            "content_generation": ["文档生成", "报告创建", "内容创作"],
            "direct_response": ["知识问答", "文本创作", "翻译总结"],
        }
        return use_cases.get(task_type, [])

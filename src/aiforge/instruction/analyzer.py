import json
from pathlib import Path
import re
from typing import Dict, Any, List
from ..llm.llm_client import AIForgeLLMClient
from ..prompts.prompt_generator import AIForgePromptGenerator


class AIForgeInstructionAnalyzer:
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
                    "信息",
                    "资讯",
                    "内容",
                ],
                "actions": ["search", "fetch", "get", "crawl"],
                "common_params": ["query", "topic", "time_range", "date"],
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
                    "复制",
                    "copy",
                    "移动",
                    "move",
                    "删除",
                    "delete",
                    "重命名",
                    "rename",
                    "压缩",
                    "compress",
                    "解压",
                    "extract",
                    "创建",
                    "create",
                    "目录",
                    "directory",
                    "文件夹",
                    "folder",
                ],
                "actions": [
                    "read",
                    "write",
                    "save",
                    "copy",
                    "move",
                    "delete",
                    "rename",
                    "compress",
                    "extract",
                    "create",
                    "process",
                ],
                "common_params": [
                    "file_path",
                    "source_path",
                    "target_path",
                    "format",
                    "encoding",
                    "recursive",
                    "force",
                    "operation",
                ],
                "exclude_keywords": [
                    "分析",
                    "analyze",
                    "统计",
                    "statistics",
                    "计算",
                    "calculate",
                    "处理数据",
                    "process data",
                    "清洗",
                    "clean",
                ],
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
                continue

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

        # 提取参数
        parameters = self._smart_extract_parameters(instruction, best_pattern["common_params"])

        # 生成完整的标准化指令，包含预期输出
        standardized = {
            "task_type": best_task_type,
            "action": self._smart_infer_action(instruction, best_pattern["actions"]),
            "target": self._extract_target(instruction),
            "parameters": parameters,
            "cache_key": self._generate_semantic_cache_key(best_task_type, instruction, parameters),
            "confidence": confidence,
            "source": "local_analysis",
            "expected_output": self.get_default_expected_output(best_task_type, parameters),
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
            },
            "required_count": {
                "patterns": [
                    r"(\d+)(?:条|个|项|篇|份|次)",
                    r"最多(\d+)",
                    r"前(\d+)",
                    r"至少(\d+)",
                    r"处理(\d+)",
                    r"生成(\d+)",
                    r"获取(\d+)",
                ],
                "type": "int",
            },
            "file_path": {
                "patterns": [r"([^\s]+\.[a-zA-Z]+)", r"文件(.+?)(?:的|，|。|$)"],
                "type": "str",
            },
            "url": {"patterns": [r"(https?://[^\s]+)"], "type": "str"},
            "content": {
                "patterns": [r"内容[：:](.+?)(?:的|，|。|$)", r"文本[：:](.+?)(?:的|，|。|$)"],
                "type": "str",
            },
            "style": {
                "patterns": [r"风格[：:](.+?)(?:的|，|。|$)", r"样式[：:](.+?)(?:的|，|。|$)"],
                "type": "str",
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
                        }
                        break

        return params

    def _extract_file_pattern(self, parameters: Dict[str, Any]) -> str:
        """从参数中提取文件路径模式"""
        # 检查各种可能的文件路径参数
        file_path_keys = ["file_path", "source_path", "target_path", "path", "filename"]

        for key in file_path_keys:
            if key in parameters:
                param_info = parameters[key]
                if isinstance(param_info, dict) and "value" in param_info:
                    file_path = param_info["value"]
                else:
                    file_path = str(param_info)

                # 提取文件扩展名和基本模式
                path_obj = Path(file_path)
                if path_obj.suffix:
                    return f"{path_obj.suffix.lower()}_file"
                elif "*" in file_path or "?" in file_path:
                    return "pattern_match"
                else:
                    return "generic_file"

        return "unknown_pattern"

    def _generate_semantic_cache_key(
        self, task_type: str, instruction: str, parameters: Dict = None
    ) -> str:
        """基于参数化指令生成语义化缓存键"""
        key_components = [task_type]

        if task_type == "file_operation":
            # 文件操作的缓存键应该考虑操作类型和文件路径模式
            operation = parameters.get("operation", "unknown")
            file_pattern = self._extract_file_pattern(parameters)
            return f"file_op_{operation}_{file_pattern}_{hash(instruction) % 10000}"

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
            "cache_key": f"general_{hash(instruction) % 10000}",
            "confidence": 0.3,
            "source": "default",
            "expected_output": self.get_default_expected_output("general"),
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
{base_sections["execution_mode"]}

# 动作命名规范
{base_sections["action_vocabulary"]}

# 分析要求
{base_sections["analysis_steps"]}

# 输出格式
{base_sections["output_format"]}

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
            # 检查是否与现有类型过于相似
            if self._is_too_similar_to_existing_types(task_type, builtin_types):
                print(f"[DEBUG] 新任务类型 '{task_type}' 与现有类型过于相似")
                return False

        # 5. 注册新的任务类型和动作（如果有管理器）
        if hasattr(self, "task_type_manager") and self.task_type_manager:
            task_type = ai_analysis.get("task_type")
            action = ai_analysis.get("action", "")

            # 注册任务类型
            self.task_type_manager.register_task_type(task_type, ai_analysis)

            # 注册动态动作（新增）
            if action and task_type:
                self.task_type_manager.register_dynamic_action(action, task_type, ai_analysis)

            # 记录类型使用统计
            builtin_types = list(self.standardized_patterns.keys())
            is_builtin = task_type in builtin_types
            if is_builtin:
                print(f"[DEBUG] 使用内置任务类型: {task_type}")
            else:
                print(f"[DEBUG] 创建新任务类型: {task_type}")

        return True

    def _is_too_similar_to_existing_types(self, task_type: str, builtin_types: List[str]) -> bool:
        """检查是否与现有类型过于相似"""
        try:
            from difflib import SequenceMatcher

            for existing_type in builtin_types:
                similarity = SequenceMatcher(None, task_type.lower(), existing_type.lower()).ratio()
                if similarity > 0.8:  # 相似度阈值
                    return True
            return False
        except Exception:
            return False

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
# 任务类型指导
{guidance_strength}使用以下经过验证的内置任务类型：
{builtin_types}

# 系统状态：
- 当前引导强度：{guidance_strength}
- 内置类型使用率：{self.get_task_type_usage_stats().get('builtin_usage_rate', 0):.1%}

这些内置类型具有更高的缓存命中率和执行效率。
"""

        return self._assemble_prompt_with_guidance(
            AIForgePromptGenerator.get_base_prompt_sections(), adaptive_guidance
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

    @staticmethod
    def get_default_expected_output(
        task_type: str, extracted_params: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """获取默认的预期输出规则"""
        defaults = {
            "data_analysis": {
                "required_fields": ["data", "analysis"],
                "validation_rules": {
                    "min_items": 0,
                    "non_empty_fields": ["key_findings"],
                },
            },
            "data_fetch": {
                "required_fields": ["data", "status"],
                "validation_rules": {
                    "min_items": 1,
                    "non_empty_fields": ["data"],
                    "partial_success": True,
                    "min_valid_ratio": 0.3,
                },
            },
            "data_process": {
                "required_fields": ["data", "processed_data"],
                "validation_rules": {
                    "min_items": 0,
                    "non_empty_fields": ["processed_data"],
                },
            },
            "file_operation": {
                "required_fields": ["data", "status"],
                "validation_rules": {
                    "min_items": 0,
                },
            },
            "automation": {
                "required_fields": ["data", "status", "summary"],
                "validation_rules": {
                    "min_items": 0,
                    "non_empty_fields": ["summary"],
                },
            },
            "content_generation": {
                "required_fields": ["data", "generated_content"],
                "validation_rules": {
                    "min_items": 1,
                    "non_empty_fields": ["generated_content"],
                },
            },
            "default": {
                "required_fields": ["data", "status"],
                "validation_rules": {
                    "min_items": 0,
                },
            },
        }

        base_config = defaults.get(task_type, defaults.get("default"))

        # 通用的数量参数调整逻辑
        if extracted_params:
            quantity_params = [
                "required_count",
                "count",
                "limit",
                "num_items",
                "quantity",
                "amount",
            ]
            for param_name in quantity_params:
                if param_name in extracted_params:
                    param_info = extracted_params[param_name]
                    if isinstance(param_info, dict) and "value" in param_info:
                        try:
                            quantity = int(param_info["value"])
                            base_config["validation_rules"]["min_items"] = max(
                                1, min(quantity, 100)
                            )
                            break
                        except (ValueError, TypeError):
                            continue

        return base_config

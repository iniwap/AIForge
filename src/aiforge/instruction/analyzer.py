from typing import Dict, Any, List
from ..llm.llm_client import AIForgeLLMClient
from ..core.prompt import AIForgePrompt
from .parser import InstructionParser
from .classifier import TaskClassifier
from .extractor import ParameterExtractor
from functools import lru_cache


class AIForgeInstructionAnalyzer:
    """指令分析器"""

    def __init__(self, llm_client: AIForgeLLMClient, components: Dict[str, Any] = None):
        # 标准化的任务类型定义
        self.standardized_patterns = {
            "data_fetch": {
                "actions": ["search", "fetch", "get", "crawl"],
                "common_params": ["query", "topic", "time_range", "date"],
            },
            "data_process": {
                "actions": ["analyze", "process", "calculate", "transform"],
                "common_params": ["data_source", "method", "format"],
            },
            "file_operation": {
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
            },
            "automation": {
                "actions": ["automate", "schedule", "monitor", "execute"],
                "common_params": ["interval", "condition", "action"],
            },
            "content_generation": {
                "actions": ["generate", "create", "write", "compose"],
                "common_params": ["template", "content", "style"],
            },
            "direct_response": {
                "actions": ["respond", "answer", "create", "translate", "summarize", "suggest"],
                "common_params": ["content", "style"],
            },
        }

        self.llm_client = llm_client
        self.task_type_manager = None
        self.components = components or {}
        self._ai_forgePrompt = AIForgePrompt(self.components)
        self._i18n_manager = self.components.get("i18n_manager")
        # 初始化子组件
        self.parser = InstructionParser(llm_client)
        self.classifier = TaskClassifier(components)
        self.extractor = ParameterExtractor(components)
        self.initialize_with_locale_detection()

    @lru_cache(maxsize=256)
    def get_cached_localized_keywords(self, task_type):
        """缓存本地化关键词以提高性能"""
        return self.get_task_type_keywords(task_type)

    def initialize_with_locale_detection(self):
        """根据检测到的语言环境初始化关键词"""
        # 预加载当前语言环境的关键词
        for task_type in self.standardized_patterns.keys():
            self.get_cached_localized_keywords(task_type)

    def get_task_type_keywords(self, task_type):
        """动态获取任务类型的关键词"""
        # 从 i18n 配置中获取当前语言的关键词
        task_keywords = self._i18n_manager.t(f"keywords.{task_type}", default={})

        # 返回所有关键词（排除 exclude 部分）
        keywords = []
        for key, value in task_keywords.items():
            if key != "exclude":
                keywords.append(value)

        return keywords

    def get_exclude_keywords(self, task_type):
        """获取排除关键词"""
        task_keywords = self._i18n_manager.t("keywords", default={}).get(task_type, {})

        exclude_section = task_keywords.get("exclude", {})
        return list(exclude_section.values()) if exclude_section else []

    def local_analyze_instruction(self, instruction: str) -> Dict[str, Any]:
        """本地指令分析"""
        instruction_lower = instruction.lower()

        # 计算每种任务类型的匹配分数
        type_scores = {}
        best_match_details = {}

        for task_type, pattern_data in self.standardized_patterns.items():
            # 使用统一的关键词获取方法
            localized_keywords = self.get_task_type_keywords(task_type)

            # 检查排除关键词
            exclude_keywords = self.get_exclude_keywords(task_type)
            if any(exclude_keyword in instruction_lower for exclude_keyword in exclude_keywords):
                continue

            score = sum(1 for keyword in localized_keywords if keyword.lower() in instruction_lower)
            if score > 0:
                type_scores[task_type] = score
                pattern_copy = pattern_data.copy()
                pattern_copy["keywords"] = localized_keywords
                best_match_details[task_type] = pattern_copy

        if not type_scores:
            return self.parser.get_default_analysis(instruction)

        # 获取最高分的任务类型
        best_task_type = max(type_scores.items(), key=lambda x: x[1])[0]
        best_pattern = best_match_details[best_task_type]

        # 提高置信度计算的准确性
        max_possible_score = len(best_pattern["keywords"])
        confidence = min(type_scores[best_task_type] / max_possible_score * 2, 1.0)

        # 提取参数
        parameters = self.extractor.smart_extract_parameters(
            instruction, best_pattern["common_params"]
        )

        # 生成完整的标准化指令，包含预期输出
        standardized = {
            "task_type": best_task_type,
            "action": self.extractor.smart_infer_action(instruction, best_pattern["actions"]),
            "target": self.extractor.extract_target(instruction),
            "parameters": parameters,
            "cache_key": self.extractor.generate_semantic_cache_key(
                best_task_type, instruction, parameters
            ),
            "confidence": confidence,
            "source": "local_analysis",
            "expected_output": ParameterExtractor.get_default_expected_output(
                best_task_type, parameters
            ),
        }

        return standardized

    def _build_task_type_guidance(self, builtin_types: List[str]) -> str:
        """构建任务类型引导信息"""
        guidance_strength = self._i18n_manager.t("analyzer.guidance.default_strength")
        additional_info = ""

        if hasattr(self, "task_type_manager") and self.task_type_manager:
            try:
                dynamic_types = getattr(self.task_type_manager, "dynamic_types", {})
                dynamic_count = len(dynamic_types) if dynamic_types else 0

                if dynamic_count > 10:
                    guidance_strength = self._i18n_manager.t(
                        "analyzer.guidance.strong_recommendation"
                    )
                    additional_info = self._i18n_manager.t(
                        "analyzer.guidance.too_many_dynamic_types", count=dynamic_count
                    )

                # 获取高优先级类型
                high_priority_types = []
                for task_type in builtin_types:
                    priority = self.task_type_manager.get_task_type_priority(task_type)
                    if priority > 80:
                        high_priority_types.append(
                            f"{task_type}({self._i18n_manager.t('analyzer.priority_label')}:{priority})"  # noqa 501
                        )

                if high_priority_types:
                    additional_info += self._i18n_manager.t(
                        "analyzer.guidance.high_priority_types",
                        types=", ".join(high_priority_types),
                    )

            except Exception:
                pass

        guidance_template = self._i18n_manager.t("analyzer.guidance.task_type_template")
        advantages = self._i18n_manager.t("analyzer.guidance.builtin_advantages")
        creation_rule = self._i18n_manager.t("analyzer.guidance.creation_rule")

        return guidance_template.format(
            strength=guidance_strength,
            types=builtin_types,
            advantages=advantages,
            creation_rule=creation_rule,
            additional_info=additional_info,
        )

    def _assemble_prompt_with_guidance(
        self, base_sections: Dict[str, str], guidance_info: str
    ) -> str:
        """组装包含引导信息的提示词"""
        role_header = self._i18n_manager.t("analyzer.prompt.role_header")
        execution_mode_header = self._i18n_manager.t("analyzer.prompt.execution_mode_header")
        action_vocabulary_header = self._i18n_manager.t("analyzer.prompt.action_vocabulary_header")
        analysis_requirements_header = self._i18n_manager.t(
            "analyzer.prompt.analysis_requirements_header"
        )
        output_format_header = self._i18n_manager.t("analyzer.prompt.output_format_header")
        strict_json_note = self._i18n_manager.t("analyzer.prompt.strict_json_note")

        return f"""
{role_header}
{base_sections["role"]}

{guidance_info}

{execution_mode_header}
{base_sections["execution_mode"]}

{action_vocabulary_header}
{base_sections["action_vocabulary"]}

{analysis_requirements_header}
{base_sections["analysis_steps"]}

{output_format_header}
{base_sections["output_format"]}

{strict_json_note}
"""

    def parse_standardized_instruction(self, response: str) -> Dict[str, Any]:
        """解析AI返回的标准化指令"""
        return self.parser.parse_standardized_instruction(response)

    def is_ai_analysis_valid(self, ai_analysis: Dict[str, Any]) -> bool:
        """验证AI分析结果的有效性"""
        return self.classifier.is_ai_analysis_valid(ai_analysis)

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

            except Exception:
                pass

        return stats

    def recommend_task_type_optimizations(self) -> List[str]:
        """推荐任务类型优化建议"""
        recommendations = []

        try:
            stats = self.get_task_type_usage_stats()
            builtin_rate = stats["builtin_usage_rate"]

            if builtin_rate < 0.6:
                recommendations.append(
                    self._i18n_manager.t("analyzer.recommendations.enhance_builtin_guidance")
                )

            if builtin_rate > 0.9:
                recommendations.append(
                    self._i18n_manager.t("analyzer.recommendations.relax_creation_conditions")
                )

            dynamic_count = len(stats["dynamic_types_usage"])
            if dynamic_count > 15:
                recommendations.append(
                    self._i18n_manager.t(
                        "analyzer.recommendations.too_many_dynamic", count=dynamic_count
                    )
                )

            # 检查低优先级类型
            low_priority_types = []
            for task_type, info in stats["dynamic_types_usage"].items():
                if info["priority"] < 60:
                    low_priority_types.append(task_type)

            if low_priority_types:
                recommendations.append(
                    self._i18n_manager.t(
                        "analyzer.recommendations.low_priority_types", count=len(low_priority_types)
                    )
                )

            # 检查内置类型使用分布
            builtin_usage = stats["builtin_types_usage"]
            if builtin_usage:
                unused_builtin = [
                    t for t, info in builtin_usage.items() if info["estimated_usage"] == 0
                ]
                if unused_builtin:
                    recommendations.append(
                        self._i18n_manager.t(
                            "analyzer.recommendations.unused_builtin", types=unused_builtin
                        )
                    )

            if not recommendations:
                recommendations.append(self._i18n_manager.t("analyzer.recommendations.all_good"))

        except Exception as e:
            recommendations.append(
                self._i18n_manager.t("analyzer.recommendations.analysis_failed", error=str(e))
            )

        return recommendations

    def adjust_guidance_strength(self) -> str:
        """根据使用统计动态调整引导强度"""
        try:
            stats = self.get_task_type_usage_stats()
            builtin_rate = stats["builtin_usage_rate"]
            dynamic_count = len(stats["dynamic_types_usage"])

            if builtin_rate < 0.5 or dynamic_count > 20:
                return self._i18n_manager.t("analyzer.guidance.strong_recommendation")
            elif builtin_rate > 0.8 and dynamic_count < 5:
                return self._i18n_manager.t("analyzer.guidance.consider")
            else:
                return self._i18n_manager.t("analyzer.guidance.default_strength")

        except Exception:
            return self._i18n_manager.t("analyzer.guidance.default_strength")

    def get_adaptive_analysis_prompt(self) -> str:
        """获取自适应的分析提示词"""
        builtin_types = list(self.standardized_patterns.keys())
        guidance_strength = self.adjust_guidance_strength()

        # 构建自适应引导信息
        task_type_guidance_header = self._i18n_manager.t(
            "analyzer.adaptive.task_type_guidance_header"
        )
        system_status_header = self._i18n_manager.t("analyzer.adaptive.system_status_header")
        current_guidance_strength = self._i18n_manager.t(
            "analyzer.adaptive.current_guidance_strength"
        )
        builtin_usage_rate = self._i18n_manager.t("analyzer.adaptive.builtin_usage_rate")
        efficiency_note = self._i18n_manager.t("analyzer.adaptive.efficiency_note")

        adaptive_guidance = f"""
{task_type_guidance_header}
{guidance_strength}{self._i18n_manager.t("analyzer.adaptive.use_builtin_types")}:
{builtin_types}

{system_status_header}
- {current_guidance_strength}: {guidance_strength}
- {builtin_usage_rate}: {self.get_task_type_usage_stats().get('builtin_usage_rate', 0):.1%}

{efficiency_note}
    """

        # 获取提示词生成器
        prompt_generator = self.components.get("prompt_generator")
        if prompt_generator:
            return self._assemble_prompt_with_guidance(
                prompt_generator.get_base_prompt_sections(), adaptive_guidance
            )
        else:
            # 回退到硬编码
            return self._assemble_prompt_with_guidance(
                self._ai_forgePrompt.get_base_prompt_sections(), adaptive_guidance
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
            # 动态获取关键词
            keywords = self.get_task_type_keywords(task_type)
            recommendations["type_descriptions"][task_type] = {
                "keywords": keywords[:5],  # 只显示前5个关键词
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
        use_cases_key = f"analyzer.use_cases.{task_type}"
        use_cases = self._i18n_manager.t(use_cases_key, default=[])

        if not use_cases:
            # 回退到硬编码
            fallback_cases = {
                "data_fetch": ["搜索网页内容", "获取API数据", "爬取新闻信息"],
                "data_process": ["数据分析", "统计计算", "格式转换"],
                "file_operation": ["读写文件", "批量处理", "文档操作"],
                "automation": ["定时任务", "系统监控", "自动化流程"],
                "content_generation": ["文档生成", "报告创建", "内容创作"],
                "direct_response": ["知识问答", "文本创作", "翻译总结"],
            }
            use_cases = fallback_cases.get(task_type, [])

        return use_cases

    @staticmethod
    def get_default_expected_output(
        task_type: str, extracted_params: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """获取默认的预期输出规则"""
        return ParameterExtractor.get_default_expected_output(task_type, extracted_params)

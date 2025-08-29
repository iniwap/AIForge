from typing import Dict, Any, Optional
import time
from ..helpers.cache_helper import CacheHelper
from ...strategies.semantic_field_strategy import SemanticFieldStrategy, FieldProcessorManager


class AIForgeSearchManager:
    """搜索管理器 - 负责多层级搜索策略和search_template集成"""

    def __init__(self, components: Dict[str, Any]):
        self.components = components
        self._i18n_manager = components.get("i18n_manager")
        self.processor_manager = FieldProcessorManager()
        self.parameter_mapping_service = components.get("parameter_mapping_service")
        self._progress_indicator = components.get("progress_indicator")

    def is_search_task(self, standardized_instruction: Dict[str, Any]) -> bool:
        """判断是否为搜索类任务"""
        action = standardized_instruction.get("action", "")

        # 从 i18n 配置获取搜索关键词
        search_keywords = self._i18n_manager.t("search_keywords", default={})

        # 检查任务类型和动作
        search_indicators = [
            any(
                keyword in action.lower() for keyword in search_keywords.get("action_keywords", [])
            ),
            any(
                keyword in standardized_instruction.get("target", "").lower()
                for keyword in search_keywords.get("target_keywords", [])
            ),
        ]

        # 检查参数中是否包含搜索相关字段
        parameters = standardized_instruction.get("required_parameters", {})
        search_param_keywords = search_keywords.get("param_keywords", [])
        search_params = any(param_name in search_param_keywords for param_name in parameters.keys())

        return any(search_indicators) or search_params

    def _try_searxng_search(
        self,
        standardized_instruction: Dict[str, Any],
        original_instruction: str,
        search_params: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """尝试使用 SearXNG 搜索"""
        config_manager = self.components.get("config_manager")
        if not config_manager or not config_manager.is_searxng_available():
            return None

        try:
            if not search_params["search_query"]:
                search_params["search_query"] = original_instruction

            # 使用 SearXNG 搜索
            template_manager = self.components.get("template_manager")
            if template_manager:
                search_result = template_manager.get_template(
                    "search_direct",
                    search_query=search_params["search_query"],
                    max_results=search_params["max_results"],
                    min_items=search_params["min_items"],
                    min_abstract_len=search_params["min_abstract_len"],
                    max_abstract_len=search_params["max_abstract_len"],
                    engine_override=f"searxng#{config_manager.get_searxng_config()['url']}",
                    progress_indicator=self._progress_indicator,
                    i18n_manager=self._i18n_manager,
                )

                if search_result and search_result.get("success"):
                    self._progress_indicator.emit(
                        "search_complete", count=len(search_result.get("results", 0))
                    )
                    return self._convert_search_result_to_aiforge_format(
                        search_result, standardized_instruction, "searxng_search"
                    )

            return None
        except Exception:
            return None

    def _try_direct_search_web(
        self,
        standardized_instruction: Dict[str, Any],
        original_instruction: str,
        search_params: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """第一层：直接调用 search_web 函数"""
        try:
            if not search_params["search_query"]:
                search_params["search_query"] = original_instruction

            # 直接调用
            template_manager = self.components.get("template_manager")
            if template_manager:
                search_result = template_manager.get_template(
                    "search_direct",
                    search_query=search_params["search_query"],
                    max_results=search_params["max_results"],
                    min_items=search_params["min_items"],
                    min_abstract_len=search_params["min_abstract_len"],
                    max_abstract_len=search_params["max_abstract_len"],
                    i18n_manager=self._i18n_manager,
                    progress_indicator=self._progress_indicator,
                )
            else:
                return None

            if search_result:
                self._progress_indicator.emit(
                    "search_complete", count=len(search_result.get("results", 0))
                )
                # 转换为AIForge标准格式
                return self._convert_search_result_to_aiforge_format(
                    search_result, standardized_instruction, "direct_search_web"
                )

            return None

        except Exception:
            return None

    def _try_cached_search(
        self, standardized_instruction: Dict[str, Any], original_instruction: str
    ) -> Optional[Dict[str, Any]]:
        """第二层：使用缓存中的搜索函数"""
        try:
            code_cache = self.components.get("code_cache")
            if not code_cache:
                return None

            # 查找搜索相关的缓存模块
            search_instruction = standardized_instruction.copy()
            search_instruction.update({"task_type": "data_fetch", "action": "search"})
            cached_modules = code_cache.get_cached_modules_by_standardized_instruction(
                search_instruction
            )
            if cached_modules:

                execution_manager = self.components.get("execution_manager")
                if not execution_manager:
                    return None

                cache_result = execution_manager.try_execute_cached_modules(
                    cached_modules, standardized_instruction
                )
                if cache_result:
                    # 应用字段映射
                    expected_output = standardized_instruction.get("expected_output")
                    if expected_output and expected_output.get("required_fields"):
                        cache_result["data"] = self.processor_manager.process_field(
                            cache_result.get("data", []), expected_output["required_fields"]
                        )

                    cache_result["metadata"]["execution_type"] = "cached_search"
                    return cache_result

            return None

        except Exception:
            return None

    def _try_template_guided_search(
        self,
        standardized_instruction: Dict[str, Any],
        original_instruction: str,
        search_params: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """第三层：模板指导"""
        try:
            if not search_params["search_query"]:
                search_params["search_query"] = original_instruction

            # 生成搜索指令
            template_manager = self.components.get("template_manager")
            if template_manager:
                search_instruction = template_manager.get_template(
                    "search_guided",
                    search_query=search_params["search_query"],
                    expected_output=standardized_instruction.get("expected_output"),
                    i18n_manager=self._i18n_manager,
                    max_results=search_params["max_results"],
                    min_abstract_len=search_params["min_abstract_len"],
                )
            else:
                return None, False

            # 执行代码生成流程
            execution_manager = self.components.get("execution_manager")
            if not execution_manager:
                return None, False

            result, code, success = execution_manager.generate_and_execute_with_code(
                search_instruction,
                None,  # 不使用系统提示词
                "data_fetch",
                standardized_instruction.get("expected_output"),
            )
            if success and result and code:
                # 缓存生成的代码
                template_instruction = standardized_instruction.copy()
                template_instruction.update(
                    {"source": "template_guided_search", "dynamic_params": search_params}
                )

                CacheHelper.save_standardized_module(self.components, template_instruction, code)

                # 标记执行类型
                result["metadata"]["execution_type"] = "template_guided_search"
                return result, True

            return None, False

        except Exception:
            return None, False

    def _try_free_form_search(
        self,
        standardized_instruction: Dict[str, Any],
        original_instruction: str,
        search_params: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """第四层：使用 AI自由模板"""
        try:
            if not search_params["search_query"]:
                search_params["search_query"] = original_instruction

            # 生成搜索指令
            template_manager = self.components.get("template_manager")
            if template_manager:
                search_instruction = template_manager.get_template(
                    "search_free_form",
                    search_query=search_params["search_query"],
                    expected_output=standardized_instruction.get("expected_output"),
                    i18n_manager=self._i18n_manager,
                    max_results=search_params["max_results"],
                    min_abstract_len=search_params["min_abstract_len"],
                )
            else:
                return None, False

            # 执行代码生成流程
            execution_manager = self.components.get("execution_manager")
            if not execution_manager:
                return None, False

            result, code, success = execution_manager.generate_and_execute_with_code(
                search_instruction,
                None,  # 不使用系统提示词
                "data_fetch",
                standardized_instruction.get("expected_output"),
            )
            if success and result and code:
                # 缓存生成的代码
                freeform_instruction = standardized_instruction.copy()
                freeform_instruction.update(
                    {"source": "free_form_search", "dynamic_params": search_params}
                )

                CacheHelper.save_standardized_module(self.components, freeform_instruction, code)

                # 标记执行类型
                result["metadata"]["execution_type"] = "free_form_search"
                return result, True

            return None, False

        except Exception:
            return None, False

    def extract_search_query(
        self, standardized_instruction: Dict[str, Any], instruction: str
    ) -> str:
        """提取搜索查询"""
        if self.parameter_mapping_service:
            # 使用现有的搜索参数提取服务
            try:
                search_params = self.parameter_mapping_service.extract_search_parameters(
                    standardized_instruction, instruction
                )
                return search_params.get("search_query", instruction)
            except Exception:
                pass

        # 回退逻辑：直接从参数中提取
        parameters = standardized_instruction.get("required_parameters", {})

        # 尝试从参数中提取搜索查询
        for param_name in ["search_query", "query", "keyword"]:
            if param_name in parameters:
                param_info = parameters[param_name]
                if isinstance(param_info, dict) and "value" in param_info:
                    return param_info["value"]
                elif isinstance(param_info, str):
                    return param_info

        # 从target中提取
        target = standardized_instruction.get("target", "")
        if target:
            return target

        # 使用原始指令作为最后的回退
        return instruction

    def _convert_search_result_to_aiforge_format(
        self,
        search_result: Dict[str, Any],
        standardized_instruction: Dict[str, Any],
        execution_type: str,
    ) -> Dict[str, Any]:
        """将search_web结果转换为AIForge标准格式，并应用字段映射"""
        import time

        # 提取搜索结果数据
        results = search_result.get("results", [])
        success = search_result.get("success", False)
        error = search_result.get("error")

        expected_output = standardized_instruction.get("expected_output")
        if expected_output and expected_output.get("required_fields"):
            results = self.processor_manager.process_field(
                results, expected_output["required_fields"]
            )

        # 使用 i18n 的消息模板
        if success:
            summary = self._i18n_manager.t("search.search_complete_success", count=len(results))
        else:
            summary = self._i18n_manager.t("search.search_failed_error", error=error)

        # 转换为AIForge标准格式
        aiforge_result = {
            "data": results,
            "status": "success" if success and results else "error",
            "summary": summary,
            "metadata": {
                "timestamp": time.time(),
                "task_type": "data_fetch",
                "execution_type": execution_type,
                "search_query": search_result.get("search_query", ""),
                "original_result_format": "search_template",
            },
        }

        return aiforge_result

    def _validate_search_result_quality(
        self, search_result: Dict[str, Any], standardized_instruction: Dict[str, Any] = None
    ) -> bool:
        """验证搜索结果质量"""

        if not search_result:
            return False

        status = search_result.get("status", "")
        data = search_result.get("data", [])

        # 基本验证：状态为成功且有数据
        if status != "success" or not data:
            return False

        # 获取期望字段
        required_fields = []
        if standardized_instruction:
            expected_output = standardized_instruction.get("expected_output", {})
            required_fields = expected_output.get("required_fields", [])

        # 如果没有指定required_fields，使用默认验证
        if not required_fields:
            required_fields = ["title", "content"]  # 最基本的字段要求

        # 使用语义字段策略进行质量验证
        field_processor = SemanticFieldStrategy()
        valid_results = 0

        for item in data:
            if isinstance(item, dict):
                # 动态验证所有required_fields
                all_fields_valid = True

                for required_field in required_fields:
                    matched_field = field_processor._find_best_source_field(item, required_field)
                    value = item.get(matched_field, "")

                    # 根据字段类型设置不同的验证标准
                    if not value:
                        all_fields_valid = False
                        break

                    # 对内容类字段进行长度检查
                    if any(
                        kw in required_field.lower()
                        for kw in ["content", "abstract", "summary", "内容"]
                    ):
                        if isinstance(value, str) and len(value.strip()) < 50:
                            all_fields_valid = False
                            break

                if all_fields_valid:
                    valid_results += 1

        # 至少要有一个有效结果
        return valid_results > 0

    def execute_multi_level_search(
        self, standardized_instruction: Dict[str, Any], original_instruction: str
    ) -> Optional[Dict[str, Any]]:
        """执行多层级搜索策略"""
        # 提取搜索参数
        search_params = self.parameter_mapping_service.extract_search_parameters(
            standardized_instruction, original_instruction
        )
        self._progress_indicator.emit("search_start", query=search_params["search_query"])

        # 第0层：尝试 SearXNG（如果可用）
        searxng_result = self._try_searxng_search(
            standardized_instruction, original_instruction, search_params
        )
        if searxng_result:
            return searxng_result

        # 第一层：直接调用 search_web
        direct_result = self._try_direct_search_web(
            standardized_instruction, original_instruction, search_params
        )
        if direct_result:
            return direct_result

        # 第二层：使用缓存中的搜索函数
        self._progress_indicator.emit(
            "search_process", search_type=self._i18n_manager.t("search.process_system_cache")
        )

        cache_result = self._try_cached_search(standardized_instruction, original_instruction)
        if cache_result and self._validate_search_result_quality(
            cache_result, standardized_instruction
        ):
            return cache_result

        # 第三层：使用 模板指导
        self._progress_indicator.emit(
            "search_process", search_type=self._i18n_manager.t("search.process_ai_template")
        )
        template_result, success = self._try_template_guided_search(
            standardized_instruction, original_instruction, search_params
        )
        if success:
            return template_result

        # 第四层：使用 get_free_form_ai_search_instruction
        self._progress_indicator.emit(
            "search_process", search_type=self._i18n_manager.t("search.process_ai_free")
        )
        freeform_result, success = self._try_free_form_search(
            standardized_instruction, original_instruction, search_params
        )
        if success:
            return freeform_result

        self._progress_indicator.emit(
            "search_process", search_type=self._i18n_manager.t("search.process_system_default")
        )

        # 所有层级都失败，系统搜索成功率较低
        return {
            "data": [],
            "status": "error",
            "summary": self._i18n_manager.t("search.all_strategies_failed"),
            "metadata": {
                "timestamp": time.time(),
                "task_type": "data_fetch",
                "execution_type": "multi_level_search_failed",
                "search_levels_attempted": [
                    "direct_search_web",
                    "cached_search",
                    "template_guided",
                    "free_form",
                ],
            },
        }

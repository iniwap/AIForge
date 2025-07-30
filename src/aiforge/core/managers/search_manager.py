from typing import Dict, Any, Optional
import time
from ..helpers.cache_helper import CacheHelper
from ...templates.search_template import ENGINE_CONFIGS


class SearchManager:
    """搜索管理器 - 负责多层级搜索策略和search_template集成"""

    def __init__(self, components: Dict[str, Any]):
        self.components = components

    def is_search_task(self, standardized_instruction: Dict[str, Any]) -> bool:
        """判断是否为搜索类任务"""
        task_type = standardized_instruction.get("task_type", "")
        action = standardized_instruction.get("action", "")

        # 检查任务类型和动作
        search_indicators = [
            task_type == "data_fetch",
            action in ["search", "fetch", "get"],
            "search" in standardized_instruction.get("target", "").lower(),
        ]

        # 检查参数中是否包含搜索相关字段
        parameters = standardized_instruction.get("required_parameters", {})
        search_params = any(
            param_name in ["search_query", "query", "keyword"] for param_name in parameters.keys()
        )

        return any(search_indicators) or search_params

    def execute_multi_level_search(
        self, standardized_instruction: Dict[str, Any], original_instruction: str
    ) -> Optional[Dict[str, Any]]:
        """执行多层级搜索策略"""
        print("[DEBUG] 开始多层级搜索策略")

        # 第一层：直接调用 search_web
        print("[DEBUG] 第一层：尝试直接调用 search_web")
        direct_result = self._try_direct_search_web(standardized_instruction, original_instruction)
        if direct_result and self._validate_search_result_quality(direct_result):
            print("[DEBUG] 第一层搜索成功，直接返回")
            return direct_result

        # 第二层：使用缓存中的搜索函数
        print("[DEBUG] 第二层：尝试使用缓存搜索")
        cache_result = self._try_cached_search(standardized_instruction, original_instruction)
        if cache_result and self._validate_search_result_quality(cache_result):
            print("[DEBUG] 第二层缓存搜索成功，直接返回")
            return cache_result

        # 第三层：使用 get_template_guided_search_instruction
        print("[DEBUG] 第三层：尝试模板引导搜索")
        template_result = self._try_template_guided_search(
            standardized_instruction, original_instruction
        )
        if template_result and self._validate_search_result_quality(template_result):
            print("[DEBUG] 第三层模板搜索成功，返回结果")
            return template_result

        # 第四层：使用 get_free_form_ai_search_instruction
        print("[DEBUG] 第四层：尝试自由形式搜索")
        freeform_result = self._try_free_form_search(standardized_instruction, original_instruction)
        if freeform_result and self._validate_search_result_quality(freeform_result):
            print("[DEBUG] 第四层自由形式搜索成功，返回结果")
            return freeform_result

        # 所有层级都失败
        print("[DEBUG] 所有搜索层级都失败")
        return {
            "data": [],
            "status": "error",
            "summary": "所有搜索策略都失败",
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

    def _try_direct_search_web(
        self, standardized_instruction: Dict[str, Any], original_instruction: str
    ) -> Optional[Dict[str, Any]]:
        """第一层：直接调用 search_web 函数"""
        try:
            # 提取搜索参数
            search_params = self._extract_search_params(
                standardized_instruction, original_instruction
            )

            if not search_params["search_query"]:
                return None

            print(
                f"[DEBUG] 直接调用search_web: query={search_params['search_query']}, max_results={search_params['max_results']}"  # noqa 501
            )

            # 动态更新ENGINE_CONFIGS
            self._update_engine_configs(search_params)

            # 直接调用
            template_manager = self.components.get("template_manager")
            if template_manager:
                search_result = template_manager.get_template(
                    "search_direct",
                    search_params["search_query"],
                    search_params["max_results"],
                    search_params["min_results"],
                )
            else:
                return None

            if search_result:
                # 转换为AIForge标准格式
                return self._convert_search_result_to_aiforge_format(
                    search_result, "direct_search_web"
                )

            return None

        except Exception as e:
            print(f"[DEBUG] 直接搜索调用失败: {e}")
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
                print(f"[DEBUG] 找到 {len(cached_modules)} 个搜索缓存模块")

                cache_result = self._try_execute_cached_modules(
                    cached_modules, standardized_instruction
                )
                if cache_result:
                    cache_result["metadata"]["execution_type"] = "cached_search"
                    return cache_result

            return None

        except Exception as e:
            print(f"[DEBUG] 缓存搜索失败: {e}")
            return None

    def _try_template_guided_search(
        self, standardized_instruction: Dict[str, Any], original_instruction: str
    ) -> Optional[Dict[str, Any]]:
        """第三层：使用 get_template_guided_search_instruction"""
        try:
            # 提取搜索参数
            search_params = self._extract_search_params(
                standardized_instruction, original_instruction
            )

            if not search_params["search_query"]:
                search_params["search_query"] = original_instruction

            print(
                f"[DEBUG] 模板引导搜索: query={search_params['search_query']}, max_results={search_params['max_results']}"  # noqa 501
            )

            # 动态更新ENGINE_CONFIGS
            self._update_engine_configs(search_params)

            # 生成搜索指令
            template_manager = self.components.get("template_manager")
            if template_manager:
                search_instruction = template_manager.get_template(
                    "search_guided",
                    search_query=search_params["search_query"],
                    max_results=search_params["max_results"],
                )
            else:
                return None

            # 执行代码生成流程
            result, code, success = self._generate_and_execute_with_code(
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
                print("[DEBUG] 模板引导搜索代码已缓存")

                # 标记执行类型
                result["metadata"]["execution_type"] = "template_guided_search"
                return result

            return None

        except Exception as e:
            print(f"[DEBUG] 模板引导搜索失败: {e}")
            return None

    def _try_free_form_search(
        self, standardized_instruction: Dict[str, Any], original_instruction: str
    ) -> Optional[Dict[str, Any]]:
        """第四层：使用 get_free_form_ai_search_instruction"""
        try:
            # 提取搜索参数
            search_params = self._extract_search_params(
                standardized_instruction, original_instruction
            )

            if not search_params["search_query"]:
                search_params["search_query"] = original_instruction

            print(
                f"[DEBUG] 自由形式搜索: query={search_params['search_query']}, max_results={search_params['max_results']}"  # noqa 501
            )

            # 动态更新ENGINE_CONFIGS
            self._update_engine_configs(search_params)

            # 生成搜索指令
            template_manager = self.components.get("template_manager")
            if template_manager:
                search_instruction = template_manager.get_template(
                    "search_free_form", search_params["search_query"], search_params["max_results"]
                )
            else:
                return None

            # 执行代码生成流程
            result, code, success = self._generate_and_execute_with_code(
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
                print("[DEBUG] 自由形式搜索代码已缓存")

                # 标记执行类型
                result["metadata"]["execution_type"] = "free_form_search"
                return result

            return None

        except Exception as e:
            print(f"[DEBUG] 自由形式搜索失败: {e}")
            return None

    def _extract_search_params(
        self, standardized_instruction: Dict[str, Any], original_instruction: str
    ) -> Dict[str, Any]:
        """提取搜索参数"""
        # 默认参数
        default_params = {
            "search_query": "",
            "max_results": 10,
            "min_results": 1,
            "MIN_ABSTRACT_LENGTH": ENGINE_CONFIGS.get("MIN_ABSTRACT_LENGTH", 300),
            "MAX_ABSTRACT_LENGTH": ENGINE_CONFIGS.get("MAX_ABSTRACT_LENGTH", 500),
        }

        parameters = standardized_instruction.get("required_parameters", {})

        # 提取搜索查询
        search_query = self._extract_search_query(standardized_instruction, original_instruction)
        default_params["search_query"] = search_query

        # 提取其他参数
        for param_name in ["max_results", "count", "limit"]:
            if param_name in parameters:
                try:
                    value = (
                        parameters[param_name].get("value", 10)
                        if isinstance(parameters[param_name], dict)
                        else parameters[param_name]
                    )
                    default_params["max_results"] = max(1, min(int(value), 50))
                    break
                except (ValueError, TypeError, AttributeError):
                    continue

        for param_name in ["min_results", "min_count"]:
            if param_name in parameters:
                try:
                    value = (
                        parameters[param_name].get("value", 1)
                        if isinstance(parameters[param_name], dict)
                        else parameters[param_name]
                    )
                    default_params["min_results"] = max(
                        1, min(int(value), default_params["max_results"])
                    )
                    break
                except (ValueError, TypeError, AttributeError):
                    continue

        return default_params

    def _extract_search_query(
        self, standardized_instruction: Dict[str, Any], original_instruction: str
    ) -> str:
        """提取搜索查询"""
        parameters = standardized_instruction.get("required_parameters", {})

        # 尝试从参数中提取
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

        # 使用原始指令
        return original_instruction

    def _update_engine_configs(self, search_params: Dict[str, Any]) -> None:
        """动态更新ENGINE_CONFIGS"""
        try:
            # 更新全局配置
            ENGINE_CONFIGS["MIN_ABSTRACT_LENGTH"] = search_params["MIN_ABSTRACT_LENGTH"]
            ENGINE_CONFIGS["MAX_ABSTRACT_LENGTH"] = search_params["MAX_ABSTRACT_LENGTH"]

            print(
                f"[DEBUG] 已更新ENGINE_CONFIGS: MIN_ABSTRACT_LENGTH={search_params['MIN_ABSTRACT_LENGTH']}, MAX_ABSTRACT_LENGTH={search_params['MAX_ABSTRACT_LENGTH']}"  # noqa 501
            )

        except Exception as e:
            print(f"[DEBUG] 更新ENGINE_CONFIGS失败: {e}")

    def _convert_search_result_to_aiforge_format(
        self,
        search_result: Dict[str, Any],
        standardized_instruction: Dict[str, Any],
        execution_type: str,
    ) -> Dict[str, Any]:
        """将search_web结果转换为AIForge标准格式"""
        import time

        # 提取搜索结果数据
        results = search_result.get("results", [])
        success = search_result.get("success", False)
        error = search_result.get("error")

        # 转换为AIForge标准格式
        aiforge_result = {
            "data": results,
            "status": "success" if success and results else "error",
            "summary": f"搜索完成，找到 {len(results)} 条结果" if success else f"搜索失败: {error}",
            "metadata": {
                "timestamp": time.time(),
                "task_type": "data_fetch",
                "execution_type": execution_type,
                "search_query": search_result.get("search_query", ""),
                "original_result_format": "search_template",
            },
        }

        return aiforge_result

    def _validate_search_result_quality(self, search_result: Dict[str, Any]) -> bool:
        """验证搜索结果质量"""
        if not search_result:
            return False

        status = search_result.get("status", "")
        data = search_result.get("data", [])

        # 基本验证：状态为成功且有数据
        if status != "success" or not data:
            return False

        # 质量验证：检查数据完整性
        valid_results = 0
        for item in data:
            if isinstance(item, dict):
                title = item.get("title", "")
                url = item.get("url", "")
                abstract = item.get("abstract", "")

                # 基本字段完整性检查
                if title and url and len(abstract) > 50:
                    valid_results += 1

        # 至少要有一个有效结果
        return valid_results > 0

    def _execute_multi_level_search(
        self, standardized_instruction: Dict[str, Any], original_instruction: str
    ) -> Optional[Dict[str, Any]]:
        """执行多层级搜索策略"""
        print("[DEBUG] 开始多层级搜索策略")

        # 第一层：直接调用 search_web
        print("[DEBUG] 第一层：尝试直接调用 search_web")
        direct_result = self._try_direct_search_web(standardized_instruction, original_instruction)
        if direct_result and self._validate_search_result_quality(direct_result):
            print("[DEBUG] 第一层搜索成功，直接返回")
            return direct_result

        # 第二层：使用缓存中的搜索函数
        print("[DEBUG] 第二层：尝试使用缓存搜索")
        cache_result = self._try_cached_search(standardized_instruction, original_instruction)
        if cache_result and self._validate_search_result_quality(cache_result):
            print("[DEBUG] 第二层缓存搜索成功，直接返回")
            return cache_result

        # 第三层：使用 get_template_guided_search_instruction
        print("[DEBUG] 第三层：尝试模板引导搜索")
        template_result = self._try_template_guided_search(
            standardized_instruction, original_instruction
        )
        if template_result and self._validate_search_result_quality(template_result):
            print("[DEBUG] 第三层模板搜索成功，返回结果")
            return template_result

        # 第四层：使用 get_free_form_ai_search_instruction
        print("[DEBUG] 第四层：尝试自由形式搜索")
        freeform_result = self._try_free_form_search(standardized_instruction, original_instruction)
        if freeform_result and self._validate_search_result_quality(freeform_result):
            print("[DEBUG] 第四层自由形式搜索成功，返回结果")
            return freeform_result

        # 所有层级都失败
        print("[DEBUG] 所有搜索层级都失败")
        return {
            "data": [],
            "status": "error",
            "summary": "所有搜索策略都失败",
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

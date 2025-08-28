from typing import Dict, Any, Optional, List, Tuple
import time

from ..prompt import AIForgePrompt
from ...adapters.input.input_adapter_manager import InputSource
from ..helpers.cache_helper import CacheHelper


class AIForgeExecutionManager:
    """执行管理器 - 负责所有执行策略和流程"""

    def __init__(self):
        self.components: Dict[str, Any] = {}
        self.config = None
        self._initialized = False
        self._i18n_manager = None
        self._ai_forgePrompt = None
        self._progress_indicator = None

    def initialize(self, components: Dict[str, Any], config):
        """初始化执行管理器"""
        self.components = components
        self.config = config
        self._initialized = True
        self._i18n_manager = components.get("i18n_manager")
        self._ai_forgePrompt = AIForgePrompt(self.components)
        self._progress_indicator = components.get("progress_indicator")

    def execute_instruction(self, instruction: str) -> Optional[Dict[str, Any]]:
        """统一执行入口"""
        if not instruction:
            return None

        return self._run_with_standardized_instruction(instruction)

    def _run_with_standardized_instruction(self, instruction: str) -> Optional[Dict[str, Any]]:
        """基于标准化指令的统一执行流程"""
        if not self.components.get("instruction_analyzer"):
            result, _, _ = self.generate_and_execute_with_code(instruction, None, None)
            return result

        # 使用统一的指令分析入口
        standardized_instruction = self._get_final_standardized_instruction(instruction)

        task_type = standardized_instruction.get("task_type", "")
        execution_mode = standardized_instruction.get("execution_mode", "code_generation")
        confidence = standardized_instruction.get("confidence", 0)

        # 检查是否是对话延续或对话类型
        is_conversation = execution_mode == "direct_ai_response" and (
            standardized_instruction.get("action") == "chat_ai"
        )

        # 对话类型直接进入直接响应模式
        if is_conversation and confidence >= 0.6:
            return self._handle_direct_response(standardized_instruction, instruction)
        elif execution_mode == "direct_ai_response" and confidence >= 0.6:
            return self._handle_direct_response(standardized_instruction, instruction)

        # 内容生成任务委托给专门的管理器
        if task_type == "content_generation":
            content_generation_manager = self.components.get("content_generation_manager")
            if (
                content_generation_manager
                and content_generation_manager.can_handle_content_generation(
                    standardized_instruction
                )
            ):
                return content_generation_manager.execute_content_generation(
                    standardized_instruction, instruction
                )

        # 数据获取任务委托给搜索管理器
        if task_type == "data_fetch":
            search_manager = self.components.get("search_manager")
            if search_manager and search_manager.is_search_task(standardized_instruction):
                result = search_manager.execute_multi_level_search(
                    standardized_instruction, instruction
                )
                if result["status"] != "error" and len(result["data"]) != 0:
                    return result

        # 其他类型按原有逻辑处理
        code_cache = self.components.get("code_cache")
        if code_cache:
            return self._execute_with_cache_first(standardized_instruction, instruction)
        else:
            return self._execute_with_ai(standardized_instruction, instruction)

    def _execute_with_cache_first(
        self, standardized_instruction: Dict[str, Any], original_instruction: str
    ) -> Optional[Dict[str, Any]]:
        """使用通用验证的缓存优先执行策略"""
        self._progress_indicator.emit("cache_lookup")

        code_cache = self.components["code_cache"]
        cached_modules = code_cache.get_cached_modules_by_standardized_instruction(
            standardized_instruction
        )

        if cached_modules:
            self._progress_indicator.emit("cache_found", count=len(cached_modules))

            validated_modules = self._final_validation_before_execution(
                cached_modules, standardized_instruction
            )

            if validated_modules:
                self._progress_indicator.emit("cache_execution")
                cache_result = self.try_execute_cached_modules(
                    validated_modules, standardized_instruction
                )
                if cache_result is not None:
                    return cache_result
        # 缓存失败或验证不通过，走AI生成路径

        return self._execute_with_ai(standardized_instruction, original_instruction, True)

    def _final_validation_before_execution(
        self, cached_modules: List[Any], standardized_instruction: Dict[str, Any]
    ) -> List[Any]:
        """执行前的通用最终验证"""
        validated_modules = []

        for module_data in cached_modules:

            # 检查模块代码内容
            try:
                module_code = self._get_module_code(module_data[1])

                # 通用意图匹配验证
                if self._code_matches_intent(module_code, standardized_instruction):
                    # 通用参数使用验证
                    if self._validate_parameter_usage_with_dataflow(
                        module_code, standardized_instruction
                    ):
                        validated_modules.append(module_data)

            except Exception:
                pass

        return validated_modules

    def _execute_with_ai(
        self, standardized_instruction: Dict[str, Any], original_instruction: str, save_cache=False
    ) -> Optional[Dict[str, Any]]:
        """使用通用验证的AI生成"""
        confidence = standardized_instruction.get("confidence", 0)
        # 使用通用增强的标准化指令生成代码
        if confidence < 0.6:
            # 处理低置信度情况
            basic_expected_output = {
                "required_fields": ["result"],
                "validation_rules": {"non_empty_fields": ["result"]},
            }
            temp_instruction = {
                "task_type": "general",
                "expected_output": basic_expected_output,
                "required_parameters": {
                    "instruction": {"value": original_instruction, "type": "str", "required": True}
                },
            }
            enhanced_prompt = self._ai_forgePrompt.get_enhanced_system_prompt(
                temp_instruction,
                self.config.get_optimization_config().get("optimize_tokens", True),
            )
            result, code, success = self.generate_and_execute_with_code(
                None, enhanced_prompt, "general", basic_expected_output
            )
        else:
            enhanced_prompt = self._ai_forgePrompt.get_enhanced_system_prompt(
                standardized_instruction,
                self.config.get_optimization_config().get("optimize_tokens", True),
            )
            result, code, success = self.generate_and_execute_with_code(
                None,
                enhanced_prompt,
                standardized_instruction.get("task_type"),
                standardized_instruction.get("expected_output"),
            )

        if save_cache and success and result and code:
            # 只进行标准化层级的验证，信任 TaskManager 的基础验证结果
            if self._should_cache_standardized_code(code, standardized_instruction):
                CacheHelper.save_standardized_module(
                    self.components, standardized_instruction, code
                )

        return result

    def _should_cache_standardized_code(
        self, code: str, standardized_instruction: Dict[str, Any]
    ) -> bool:
        """标准化层级的缓存价值判断"""

        # 跳过基础验证，直接进行标准化相关验证
        if not standardized_instruction:
            return True  # 如果没有标准化指令，直接允许缓存

        # 核心：只进行参数使用的数据流分析验证
        if not self._validate_parameter_usage_with_dataflow(code, standardized_instruction):
            return False

        # 可以添加其他标准化相关的验证

        return True

    def _get_final_standardized_instruction(self, instruction: str) -> Dict[str, Any]:
        """获取最终的标准化指令"""

        instruction_analyzer = self.components["instruction_analyzer"]

        # 第一步：本地分析（已包含输出格式）
        local_analysis = instruction_analyzer.local_analyze_instruction(instruction)

        # 第二步：如果置信度低，尝试AI分析
        confidence = local_analysis.get("confidence", 0)
        final_analysis = local_analysis

        if confidence < 0.6:
            ai_analysis = self._try_ai_standardization(instruction)
            if ai_analysis and ai_analysis.get("confidence", 0) > confidence:
                final_analysis = ai_analysis

        return final_analysis

    def _try_ai_standardization(self, instruction: str) -> Optional[Dict[str, Any]]:
        """尝试AI标准化指令"""
        instruction_analyzer = self.components.get("instruction_analyzer")
        if not instruction_analyzer:
            return None

        try:
            # 使用自适应分析提示词
            analysis_prompt = instruction_analyzer.get_adaptive_analysis_prompt()
            user_instruction_label = self._i18n_manager.t("analyzer.user_instruction_label")
            response = instruction_analyzer.llm_client.generate_code(
                f"{analysis_prompt}\n\n{user_instruction_label}{instruction}", ""
            )

            ai_analysis = instruction_analyzer.parse_standardized_instruction(response)

            if instruction_analyzer.is_ai_analysis_valid(ai_analysis):
                # 检查是否有数量相关的参数，并确保 expected_output 正确设置
                required_parameters = ai_analysis.get("required_parameters", {})
                expected_output = ai_analysis.get("expected_output", {})

                # 如果 AI 分析中包含数量要求，确保验证规则得到更新
                for param_name, param_info in required_parameters.items():
                    if param_name in ["required_count", "count", "limit", "num_items"]:
                        if isinstance(param_info, dict) and "value" in param_info:
                            try:
                                quantity = int(param_info["value"])
                                if "validation_rules" not in expected_output:
                                    expected_output["validation_rules"] = {}
                                expected_output["validation_rules"]["min_items"] = max(
                                    1, min(quantity, 50)
                                )
                            except (ValueError, TypeError):
                                continue

                ai_analysis["expected_output"] = expected_output
                ai_analysis["source"] = "ai_analysis"
                ai_analysis["confidence"] = 0.9

                return ai_analysis

        except Exception:
            pass

        return None

    def try_execute_cached_modules(
        self, cached_modules: List[Any], standardized_instruction: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """尝试执行缓存模块，包含结果验证"""
        code_cache = self.components["code_cache"]
        execution_engine = self.components.get("execution_engine")

        for module_id, file_path, success_count, failure_count in cached_modules:
            try:
                module = code_cache.load_module(module_id)
                if module:
                    result = self._execute_cached_module(
                        module,
                        standardized_instruction.get("target", ""),
                        standardized_instruction=standardized_instruction,
                    )
                    if result:
                        expected_output = standardized_instruction.get("expected_output")
                        if expected_output and expected_output.get("required_fields"):
                            from ...strategies.semantic_field_strategy import SemanticFieldStrategy

                            processor = SemanticFieldStrategy()
                            data = result.get("data", [])
                            if isinstance(data, list):
                                processed_data = processor.process_fields(
                                    data, expected_output["required_fields"]
                                )
                                result["data"] = processed_data

                        # 完全通过执行引擎进行结果验证
                        if execution_engine:
                            is_valid = execution_engine.validate_cached_result(
                                result, standardized_instruction
                            )
                        else:
                            # 如果执行引擎不可用，使用基本验证作为回退
                            is_valid = result.get("status") == "success" and result.get("data")

                        if is_valid:
                            code_cache.update_module_stats(module_id, True)
                            return result
                        else:
                            code_cache.update_module_stats(module_id, False)
                    else:
                        code_cache.update_module_stats(module_id, False)
            except Exception:
                code_cache.update_module_stats(module_id, False)

        return None

    def _code_matches_intent(self, code: str, standardized_instruction: Dict[str, Any]) -> bool:
        """通用版代码意图匹配验证"""
        required_params = standardized_instruction.get("required_parameters", {})

        # 通用参数化程度检查
        if not self._validate_parameterization_level(code, required_params):
            return False

        # 通用功能一致性检查
        if not self._validate_functionality_consistency(code, standardized_instruction):
            return False

        return True

    def _validate_parameterization_level(self, code: str, required_params: Dict[str, Any]) -> bool:
        """通用参数化程度验证"""
        if not required_params:
            return True

        import re

        # 检查函数定义
        func_match = re.search(r"def\s+execute_task\s*\(([^)]*)\)", code)
        if not func_match:
            return False

        # 解析函数参数
        func_params_str = func_match.group(1)
        func_params = [
            p.strip().split("=")[0].strip() for p in func_params_str.split(",") if p.strip()
        ]

        # 参数覆盖率检查：至少要有60%的必需参数被定义
        expected_param_count = len(required_params)
        actual_param_count = len(func_params)
        coverage_ratio = (
            actual_param_count / expected_param_count if expected_param_count > 0 else 1
        )

        return coverage_ratio >= 0.6

    def _validate_functionality_consistency(
        self, code: str, standardized_instruction: Dict[str, Any]
    ) -> bool:
        """通用功能一致性验证"""
        action = standardized_instruction.get("action", "")

        # 基于动作类型的通用验证
        action_lower = action.lower()
        code_lower = code.lower()

        # 获取类动作验证
        if any(word in action_lower for word in ["get", "fetch", "retrieve", "获取", "查询"]):
            # 应该包含数据获取相关的代码
            if not any(
                pattern in code_lower
                for pattern in ["requests", "urllib", "http", "api", "get", "fetch"]
            ):
                return False

        # 处理类动作验证
        elif any(
            word in action_lower
            for word in ["process", "analyze", "calculate", "处理", "分析", "计算"]
        ):
            # 应该包含数据处理相关的代码
            if not any(
                pattern in code_lower
                for pattern in ["for", "while", "if", "process", "analyze", "calculate"]
            ):
                return False

        # 生成类动作验证
        elif any(
            word in action_lower for word in ["generate", "create", "make", "生成", "创建", "制作"]
        ):
            # 应该包含生成或创建相关的代码
            if not any(
                pattern in code_lower
                for pattern in ["generate", "create", "make", "write", "build"]
            ):
                return False

        return True

    def _validate_parameter_usage_with_dataflow(
        self, code: str, standardized_instruction: Dict[str, Any]
    ) -> bool:
        """通过执行引擎进行参数验证"""

        execution_engine = self.components.get("execution_engine")
        if execution_engine:
            return execution_engine.validate_parameter_usage_with_dataflow(
                code, standardized_instruction
            )

        # 如果执行引擎不可用，返回默认值
        return True

    def generate_and_execute_with_code(
        self,
        instruction: str,
        system_prompt: str | None = None,
        task_type: str = None,
        expected_output: Dict[str, Any] = None,
    ) -> Tuple[Optional[Dict[str, Any]], str | None]:
        """生成并执行代码，同时返回结果和代码"""
        llm_manager = self.components["llm_manager"]
        task_manager = self.components["task_manager"]

        client = llm_manager.get_client()
        if not client:
            return None, None, False

        task = None
        try:
            task = task_manager.new_task(instruction, client)
            result, code, success = task.run(instruction, system_prompt, task_type, expected_output)

            if success and result:
                return result, code or "", success
            else:
                return None, None, False
        finally:
            if task:
                task.done()

    def _execute_cached_module(self, module, instruction: str, **kwargs) -> Any:
        """执行缓存模块"""
        module_executors = self.components["module_executors"]
        for executor in module_executors:
            if executor.can_handle(module):
                try:
                    result = executor.execute(module, instruction, **kwargs)
                    if result is not None:
                        return result
                except Exception:
                    continue
        return None

    def _get_module_code(self, file_path: str) -> str:
        """获取模块代码"""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception:
            return ""

    def _handle_direct_response(
        self, standardized_instruction: Dict[str, Any], original_instruction: str
    ) -> Optional[Dict[str, Any]]:
        """处理直接响应任务，支持自动会话管理"""
        llm_manager = self.components["llm_manager"]
        client = llm_manager.get_client()
        if not client:
            return None

        action = standardized_instruction.get("action", "respond")
        is_conversational = action == "chat_ai"

        # 使用统一的提示词生成器实例方法
        system_prompt = self._ai_forgePrompt.get_direct_response_prompt(
            action, standardized_instruction
        )

        try:
            response = client.generate_code(
                original_instruction, system_prompt, use_history=is_conversational
            )

            # 使用 i18n 的消息模板
            summary = self._i18n_manager.t(
                "execution.direct_response_success",
                action=action,
                instruction=original_instruction[:50],
            )

            return {
                "data": {
                    "content": response,
                    "response_type": action,
                    "direct_response": True,
                    "is_conversational": is_conversational,
                    "conversation_active": is_conversational,
                },
                "status": "success",
                "summary": summary,
                "metadata": {
                    "timestamp": time.time(),
                    "task_type": "direct_response",
                    "execution_type": "direct_ai_response",
                    "action": action,
                    "no_code_generation": True,
                    "conversation_mode": is_conversational,
                },
            }
        except Exception as e:
            error_summary = self._i18n_manager.t("execution.direct_response_error", error=str(e))

            return {
                "data": None,
                "status": "error",
                "summary": error_summary,
                "metadata": {
                    "timestamp": time.time(),
                    "task_type": "direct_response",
                    "error": str(e),
                },
            }

    def process_input(
        self, raw_input_x: Any, source: str, context_data: Optional[Dict[str, Any]] = None
    ) -> str:
        """处理多端输入并返回标准化指令"""
        input_adapter_manager = self.components["input_adapter_manager"]

        try:
            # 转换输入源
            input_source = InputSource(source)

            # 适配输入
            standardized_input = input_adapter_manager.adapt_input(
                raw_input_x, input_source, context_data
            )

            # 返回标准化指令
            return standardized_input.instruction

        except Exception:
            # 输入适配失败时的回退处理
            if isinstance(raw_input_x, str):
                return raw_input_x
            elif isinstance(raw_input_x, dict):
                return raw_input_x.get("instruction", raw_input_x.get("text", str(raw_input_x)))
            else:
                return str(raw_input_x)

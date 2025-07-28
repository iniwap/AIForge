from typing import Dict, Any, Optional, List, Tuple
import ast
import time

from ...prompts.enhanced_prompts import (
    get_enhanced_system_prompt,
    get_direct_response_prompt,
)
from ...validation.code_validator import CodeValidator
from ..data_flow_analyzer import DataFlowAnalyzer
from ...adapters.input.input_adapter_manager import InputSource
from ..result_manager import AIForgeResult


class ExecutionManager:
    """执行管理器 - 负责所有执行策略和流程"""

    def __init__(self):
        self.components: Dict[str, Any] = {}
        self.config = None
        self._initialized = False

    def initialize(self, components: Dict[str, Any], config):
        """初始化执行管理器"""
        self.components = components
        self.config = config
        self._initialized = True

    def execute_instruction(self, instruction: str) -> Optional[Dict[str, Any]]:
        """统一执行入口"""
        if not instruction:
            return None

        return self._run_with_standardized_instruction(instruction)

    def _run_with_standardized_instruction(self, instruction: str) -> Optional[Dict[str, Any]]:
        """基于标准化指令的统一执行流程"""
        instruction_analyzer = self.components.get("instruction_analyzer")

        # 第一步：本地标准化指令分析
        if not instruction_analyzer:
            result, _ = self._generate_and_execute_with_code(instruction, None, None)
            return result

        # 使用统一的指令分析入口
        standardized_instruction = self._get_final_standardized_instruction(instruction)
        execution_mode = standardized_instruction.get("execution_mode", "code_generation")
        confidence = standardized_instruction.get("confidence", 0)

        # 检查是否是对话延续或对话类型
        is_conversation = execution_mode == "direct_ai_response" and (
            standardized_instruction.get("conversation_context") == "continuation"
            or standardized_instruction.get("action")
            in ["emotional_support_chat", "casual_chat", "consultation", "chat"]
        )

        # 对话类型直接进入直接响应模式
        if is_conversation and confidence >= 0.6:
            return self._handle_direct_response(standardized_instruction, instruction)
        elif execution_mode == "direct_ai_response" and confidence >= 0.6:
            return self._handle_direct_response(standardized_instruction, instruction)

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
        print("[DEBUG] 进入通用验证缓存优先执行策略")

        code_cache = self.components["code_cache"]
        cached_modules = code_cache.get_cached_modules_by_standardized_instruction(
            standardized_instruction
        )

        if cached_modules:
            print(f"[DEBUG] 找到 {len(cached_modules)} 个缓存模块，进行验证和执行")

            validated_modules = self._final_validation_before_execution(
                cached_modules, standardized_instruction
            )

            if validated_modules:
                cache_result = self._try_execute_cached_modules(
                    validated_modules, standardized_instruction
                )
                if cache_result is not None:
                    print("[DEBUG] 缓存执行成功且验证通过")
                    return cache_result
                else:
                    print("[DEBUG] 缓存执行失败或验证不通过，回退到AI生成")
            else:
                print("[DEBUG] 所有缓存模块验证失败，走AI生成路径")
        else:
            print("[DEBUG] 未找到缓存模块")

        # 缓存失败或验证不通过，走AI生成路径
        print("[DEBUG] 回退到AI生成路径")
        return self._execute_with_ai(standardized_instruction, original_instruction, True)

    def _final_validation_before_execution(
        self, cached_modules: List[Any], standardized_instruction: Dict[str, Any]
    ) -> List[Any]:
        """执行前的通用最终验证"""
        validated_modules = []

        for module_data in cached_modules:
            module_id = module_data[0]

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
                        print(f"[DEBUG] 模块 {module_id} 通过通用验证")
                    else:
                        print(f"[DEBUG] 模块 {module_id} 参数使用验证失败")
                else:
                    print(f"[DEBUG] 模块 {module_id} 意图匹配验证失败")

            except Exception as e:
                print(f"[DEBUG] 验证模块 {module_id} 时出错: {e}")

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
                "expected_result_type": "dict",
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
            enhanced_prompt = get_enhanced_system_prompt(
                temp_instruction,
                self.config.get_optimization_config().get("optimize_tokens", True),
            )
            result, code = self._generate_and_execute_with_code(
                None, enhanced_prompt, "general", basic_expected_output
            )
        else:
            enhanced_prompt = get_enhanced_system_prompt(
                standardized_instruction,
                self.config.get_optimization_config().get("optimize_tokens", True),
            )
            result, code = self._generate_and_execute_with_code(
                None,
                enhanced_prompt,
                standardized_instruction.get("task_type"),
                standardized_instruction.get("expected_output"),
            )

        if save_cache:
            # 使用通用验证保存成功的代码到缓存
            if result and code:
                if self._is_code_worth_caching(code, result, standardized_instruction):
                    self._save_standardized_module(standardized_instruction, code)

        return result

    def _get_final_standardized_instruction(self, instruction: str) -> Dict[str, Any]:
        """获取最终的标准化指令"""
        print(f"[DEBUG] 输入指令: {instruction}")

        instruction_analyzer = self.components["instruction_analyzer"]

        # 第一步：本地分析（已包含输出格式）
        local_analysis = instruction_analyzer.local_analyze_instruction(instruction)
        print(
            f"[DEBUG] 本地分析结果: task_type={local_analysis.get('task_type')}, confidence={local_analysis.get('confidence')}"  # noqa 501
        )

        # 第二步：如果置信度低，尝试AI分析
        confidence = local_analysis.get("confidence", 0)
        final_analysis = local_analysis

        if confidence < 0.6:
            print(f"[DEBUG] 置信度低({confidence})，尝试AI分析...")
            ai_analysis = self._try_ai_standardization(instruction)
            if ai_analysis and ai_analysis.get("confidence", 0) > confidence:
                final_analysis = ai_analysis
                print(f"[DEBUG] AI分析成功: task_type={ai_analysis.get('task_type')}")

        print(f"[DEBUG] 最终标准化指令（含输出格式）: {final_analysis}")

        return final_analysis

    def _try_ai_standardization(self, instruction: str) -> Optional[Dict[str, Any]]:
        """尝试AI标准化指令"""
        instruction_analyzer = self.components.get("instruction_analyzer")
        if not instruction_analyzer:
            return None

        print(f"[DEBUG] 开始AI标准化分析: {instruction}")

        try:
            # 使用自适应分析提示词
            analysis_prompt = instruction_analyzer.get_adaptive_analysis_prompt()
            response = instruction_analyzer.llm_client.generate_code(
                f"{analysis_prompt}\n\n用户指令: {instruction}", ""
            )

            ai_analysis = instruction_analyzer.parse_standardized_instruction(response)
            print(f"[DEBUG] AI分析原始结果: {ai_analysis}")

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
            else:
                print("[DEBUG] AI分析验证失败")
        except Exception as e:
            print(f"[DEBUG] AI分析异常: {e}")
            pass

        return None

    def _try_execute_cached_modules(
        self, cached_modules: List[Any], standardized_instruction: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """尝试执行缓存模块，包含结果验证"""
        code_cache = self.components["code_cache"]

        for module_id, file_path, success_count, failure_count in cached_modules:
            try:
                print(f"[DEBUG] 尝试加载模块: {module_id}")
                module = code_cache.load_module(module_id)
                if module:
                    print("[DEBUG] 模块加载成功，开始执行")
                    result = self._execute_cached_module(
                        module,
                        standardized_instruction.get("target", ""),
                        standardized_instruction=standardized_instruction,
                    )
                    if result:
                        # 对缓存执行结果进行严格验证
                        is_valid = AIForgeResult.validate_cached_result(
                            result, standardized_instruction
                        )
                        if is_valid:
                            print("[DEBUG] 缓存模块执行成功且验证通过")
                            code_cache.update_module_stats(module_id, True)
                            return result
                        else:
                            print("[DEBUG] 缓存模块执行结果验证失败")
                            code_cache.update_module_stats(module_id, False)
                    else:
                        print("[DEBUG] 模块执行返回None")
                        code_cache.update_module_stats(module_id, False)
                else:
                    print("[DEBUG] 模块加载失败")
            except Exception as e:
                print(f"[DEBUG] 模块执行异常: {e}")
                code_cache.update_module_stats(module_id, False)

        return None

    def _code_matches_intent(self, code: str, standardized_instruction: Dict[str, Any]) -> bool:
        """通用版代码意图匹配验证"""
        required_params = standardized_instruction.get("required_parameters", {})

        # 通用参数化程度检查
        if not self._validate_parameterization_level(code, required_params):
            print("[DEBUG] 代码参数化程度不足")
            return False

        # 通用功能一致性检查
        if not self._validate_functionality_consistency(code, standardized_instruction):
            print("[DEBUG] 代码功能一致性验证失败")
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
        """使用增强数据流分析的参数验证"""
        try:
            tree = ast.parse(code)

            function_def = None
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef) and node.name == "execute_task":
                    function_def = node
                    break

            if not function_def:
                print("[DEBUG] 未找到execute_task函数")
                return False

            func_params = [arg.arg for arg in function_def.args.args]
            required_params = standardized_instruction.get("required_parameters", {})

            # 创建增强的数据流分析器
            analyzer = DataFlowAnalyzer(func_params)
            analyzer.visit(function_def)

            # 检查API密钥相关冲突
            if analyzer.has_parameter_conflicts():
                conflicts = analyzer.get_conflict_details()
                for conflict in conflicts:
                    if conflict["type"] == "api_key_usage":
                        print(f"[DEBUG] 发现API密钥使用冲突: {conflict}")
                        return False

            # 检查参数冲突
            if analyzer.has_parameter_conflicts():
                conflicts = analyzer.get_conflict_details()
                for conflict in conflicts:
                    print(f"[DEBUG] 发现参数冲突: {conflict}")
                    if (
                        conflict["type"] == "hardcoded_coordinates"
                        and conflict["parameter"] == "location"
                    ):
                        print("[DEBUG] 检测到硬编码坐标与location参数冲突，拒绝缓存")
                        return False

            # 原有的参数使用验证
            meaningful_param_count = 0
            for param_name in func_params:
                if param_name in required_params:
                    if param_name in analyzer.meaningful_uses:
                        meaningful_param_count += 1
                        usage_contexts = analyzer.usages.get(param_name, [])
                        print(f"[DEBUG] 参数 {param_name} 有意义使用: {usage_contexts}")
                    else:
                        print(f"[DEBUG] 参数 {param_name} 未被有意义使用")

            total_required = len([p for p in func_params if p in required_params])
            if total_required == 0:
                return True

            usage_ratio = meaningful_param_count / total_required
            print(
                f"[DEBUG] 参数有意义使用比例: {usage_ratio:.2f} ({meaningful_param_count}/{total_required})"
            )

            return usage_ratio >= 0.5

        except Exception as e:
            print(f"[DEBUG] 数据流分析失败: {e}")
            return False

    def _is_code_worth_caching(
        self, code: str, result: Any, standardized_instruction: Dict[str, Any] = None
    ) -> bool:
        """代码缓存价值判断"""
        # 基础验证
        if not CodeValidator.validate_code(code):
            print("[DEBUG] 代码未通过基础验证")
            return False

        if not AIForgeResult.validate_result_format(result):
            print("[DEBUG] 结果格式验证失败")
            return False

        if isinstance(result, dict):
            status = result.get("status")
            if status == "error":
                print("[DEBUG] 结果状态为错误，不予缓存")
                return False
            if status is not None and status != "success":
                print("[DEBUG] 结果状态非成功，不予缓存")
                return False

        # 只进行参数使用验证，不做复杂的硬编码检测
        if standardized_instruction:
            if not self._validate_parameter_usage_with_dataflow(code, standardized_instruction):
                print("[DEBUG] 代码未通过数据流参数使用验证，不予缓存")
                return False

        return True

    def _save_standardized_module(
        self, standardized_instruction: Dict[str, Any], code: str
    ) -> str | None:
        """保存基于参数化标准化指令的模块"""
        code_cache = self.components.get("code_cache")
        if not code_cache:
            return None

        # 如果有动态任务类型管理器，注册新的任务类型和动作
        task_type = standardized_instruction.get("task_type", "general")
        action = standardized_instruction.get("action", "")
        task_type_manager = self.components.get("task_type_manager")

        if task_type_manager:
            task_type_manager.register_task_type(task_type, standardized_instruction)

            # 如果是AI分析来源，注册动态动作
            if standardized_instruction.get("source") == "ai_analysis" and action:
                task_type_manager.register_dynamic_action(
                    action, task_type, standardized_instruction
                )
                # 增加使用计数
                task_type_manager.increment_action_usage(action)

        try:
            # 提取参数化信息用于元数据
            required_params = standardized_instruction.get("required_parameters", {})
            execution_logic = standardized_instruction.get("execution_logic", "")

            metadata = {
                "task_type": task_type,
                "is_standardized": True,
                "is_parameterized": bool(required_params),
                "parameter_count": len(required_params),
                "execution_logic": execution_logic,
                "validation_level": "universal",  # 标记使用了通用验证
                "parameter_usage_validated": True,  # 标记参数使用已验证
            }

            # 直接调用缓存的保存方法
            result = code_cache.save_standardized_module(standardized_instruction, code, metadata)
            return result
        except Exception:
            return None

    def _generate_and_execute_with_code(
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
            return None, None

        task = None
        try:
            task = task_manager.new_task(instruction, client)
            task.run(instruction, system_prompt, task_type, expected_output)

            # 查找最有价值的成功执行代码
            best_entry = self._find_best_successful_code(task.executor.history)
            if best_entry:
                result = best_entry["result"]["__result__"]
                code = best_entry.get("code", "")
                return result, code

            return None, None
        finally:
            if task:
                task.done()

    def _find_best_successful_code(self, history: List[Dict]) -> Optional[Dict]:
        """找到最有价值的成功执行代码"""
        successful_entries = []

        # 收集所有成功的执行记录
        for entry in history:
            if entry.get("success") and entry.get("result", {}).get("__result__"):
                successful_entries.append(entry)

        if not successful_entries:
            return None

        # 按代码质量排序，优先选择功能代码
        def code_quality_score(entry):
            code = entry.get("code", "")

            # 如果只是简单的 __result__ 赋值，得分很低
            lines = code.strip().split("\n")
            if len(lines) <= 3 and all(
                "__result__" in line or line.strip() == "" for line in lines
            ):
                return 1

            # 包含函数定义、导入语句等的代码得分更高
            score = 10
            if "def " in code:
                score += 50
            if "import " in code or "from " in code:
                score += 30
            if "class " in code:
                score += 40
            if len(lines) > 10:
                score += 20

            return score

        # 返回质量得分最高的代码
        return max(successful_entries, key=code_quality_score)

    def _execute_cached_module(self, module, instruction: str, **kwargs) -> Any:
        """执行缓存模块"""
        module_executors = self.components["module_executors"]

        for executor in module_executors:
            if executor.can_handle(module):
                try:
                    result = executor.execute(module, instruction, **kwargs)
                    if result is not None:
                        return result
                except Exception as e:
                    print(f"[DEBUG] 执行器执行失败: {e}")
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

        # 检查是否是对话类型任务
        is_conversational = action in [
            "emotional_support_chat",
            "casual_chat",
            "consultation",
            "chat",
        ]

        # 构建直接响应提示词
        system_prompt = get_direct_response_prompt(action, standardized_instruction)
        try:
            # 对话类型自动启用历史记录
            use_history = is_conversational
            response = client.generate_code(
                original_instruction, system_prompt, use_history=use_history
            )

            # 添加时间戳以符合标准格式
            return {
                "data": {
                    "content": response,
                    "response_type": action,
                    "direct_response": True,
                    "is_conversational": is_conversational,
                    "conversation_active": use_history,  # 标记会话状态
                },
                "status": "success",
                "summary": f"直接响应: {action} - {original_instruction[:50]}...",
                "metadata": {
                    "timestamp": time.time(),
                    "task_type": "direct_response",
                    "execution_type": "direct_ai_response",
                    "action": action,
                    "no_code_generation": True,
                    "conversation_mode": use_history,
                },
            }
        except Exception as e:

            return {
                "data": None,
                "status": "error",
                "summary": f"直接响应失败: {str(e)}",
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

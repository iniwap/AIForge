import re
from typing import Optional, Dict, Any, Tuple, List
from pathlib import Path


from ..config.config import AIForgeConfig
from ..llm.llm_manager import AIForgeLLMManager
from .task_manager import AIForgeManager
from ..cache.standardized_cache import StandardizedCodeCache
from .runner import AIForgeRunner
from ..instruction.analyzer import InstructionAnalyzer
from ..extensions.template_extension import DomainTemplateExtension
from ..adapters.output.enhanced_hybrid_adapter import EnhancedHybridUIAdapter
from ..adapters.input.input_adapter_manager import InputAdapterManager, InputSource
from ..prompts.enhanced_prompts import get_enhanced_aiforge_prompt
from ..execution.unified_executor import UnifiedParameterizedExecutor
from ..execution.executor_interface import CachedModuleExecutor
from ..execution.similarity_parameter_executor import SimilarityParameterExecutor
from .dynamic_task_type_manager import DynamicTaskTypeManager


class AIForgeCore:
    """AIForge核心接口 - 完全基于标准化指令的架构"""

    def __init__(
        self,
        config_file: str | None = None,
        api_key: str | None = None,
        provider: str = "openrouter",
        **kwargs,
    ):
        """
        初始化AIForge核心

        Args:
            config_file: 配置文件路径（可选）
            api_key: API密钥（快速启动模式）
            provider: LLM提供商名称
            **kwargs: 其他配置参数（max_rounds, workdir等）
        """
        # 初始化配置
        self.config = self._init_config(config_file, api_key, provider, **kwargs)
        # 初始化核心组件
        self.llm_manager = AIForgeLLMManager(self.config)
        self.task_manager = AIForgeManager(self.llm_manager)
        self.runner = AIForgeRunner(str(self.config.get_workdir()))

        # 初始化指令分析器
        default_client = self.llm_manager.get_client()
        self.instruction_analyzer = InstructionAnalyzer(default_client) if default_client else None
        # 初始化缓存（如果启用）
        self._init_cache()
        # 初始化执行器
        self._init_executors()
        # 初始化增强的UI适配器
        self.ui_adapter = None
        # 初始化输入适配管理器
        self.input_adapter_manager = InputAdapterManager()

    def _init_cache(self):
        """初始化缓存"""
        cache_config = self.config.get_cache_config("code")
        if cache_config.get("enabled", True):
            cache_dir = Path(self.config.get_workdir()) / "cache"
            self.code_cache = StandardizedCodeCache(cache_dir, cache_config)

            # 初始化动态任务类型管理器
            self.task_type_manager = DynamicTaskTypeManager(cache_dir)
            self.code_cache.task_type_manager = self.task_type_manager

            # 将管理器传递给指令分析器
            if self.instruction_analyzer:
                self.instruction_analyzer.task_type_manager = self.task_type_manager
        else:
            self.code_cache = None

    def _init_ui_adapter(self):
        """初始化增强的UI适配器"""
        if self.ui_adapter is None:
            default_client = self.llm_manager.get_client()
            if default_client:
                self.ui_adapter = EnhancedHybridUIAdapter(default_client)

    def adapt_result_for_ui(
        self, result: Dict[str, Any], ui_type: str = None, context: str = "web"
    ) -> Dict[str, Any]:
        """智能适配结果为UI格式"""
        self._init_ui_adapter()
        if self.ui_adapter:
            return self.ui_adapter.adapt_data(result, ui_type, context)
        return result

    def recommend_ui_types(
        self, result: Dict[str, Any], context: str = "web"
    ) -> List[Tuple[str, float]]:
        """推荐最适合的UI类型"""
        self._init_ui_adapter()
        if self.ui_adapter:
            return self.ui_adapter.recommend_ui_types(result, context)
        return [("web_card", 5.0)]

    def get_ui_adaptation_stats(self) -> Dict[str, Any]:
        """获取UI适配统计信息"""
        if self.ui_adapter:
            return self.ui_adapter.get_adaptation_stats()
        return {}

    def get_supported_ui_combinations(self) -> Dict[str, List[str]]:
        """获取支持的UI组合"""
        if self.ui_adapter:
            return self.ui_adapter.get_supported_combinations()
        return {}

    def process_input(
        self, raw_input_x: Any, source: str, context_data: Optional[Dict[str, Any]] = None
    ) -> str:
        """处理多端输入并返回标准化指令"""
        try:
            # 转换输入源
            input_source = InputSource(source)

            # 适配输入
            standardized_input = self.input_adapter_manager.adapt_input(
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

    def run_with_input_adaptation(
        self, raw_input_x: Any, source: str, context_data: Optional[Dict[str, Any]] = None
    ) -> Any:
        """带输入适配的运行方法"""
        # 适配输入
        instruction = self.process_input(raw_input_x, source, context_data)

        # 执行任务
        return self.run(instruction)

    def _validate_code_quality(self, code: str) -> bool:
        """验证代码质量 - 确保是真正的功能代码而非数据赋值"""
        if not code or not isinstance(code, str):
            return False

        # 检查语法
        try:
            compile(code, "<string>", "exec")
        except SyntaxError:
            return False

        # 拒绝只是简单数据赋值的代码
        lines = [line.strip() for line in code.strip().split("\n") if line.strip()]

        # 如果只有1-3行且都是简单赋值，认为不是有用的代码
        if len(lines) <= 3:
            assignment_lines = sum(
                1 for line in lines if "=" in line and not line.startswith("def ")
            )
            if assignment_lines == len(lines):
                return False

        # 必须包含一些实际的编程结构
        has_structure = any(
            keyword in code
            for keyword in ["def ", "class ", "import ", "from ", "if ", "for ", "while ", "try:"]
        )

        return has_structure

    def _validate_result_format(self, result: Any) -> bool:
        """验证结果是否符合标准格式"""
        if not isinstance(result, dict):
            return False

        # 检查必要字段
        required_fields = ["data", "status", "summary", "metadata"]
        if not all(field in result for field in required_fields):
            return False

        # 检查metadata格式
        metadata = result.get("metadata", {})
        if not isinstance(metadata, dict):
            return False

        required_metadata = ["timestamp", "task_type"]
        if not all(field in metadata for field in required_metadata):
            return False

        return True

    def _is_code_worth_caching(self, code: str, result: Any) -> bool:
        """判断代码是否值得缓存"""
        # 代码必须通过质量验证
        if not self._validate_code_quality(code):
            return False

        # 结果必须是标准化格式
        if not self._validate_result_format(result):
            return False

        # 结果必须表示成功状态
        if isinstance(result, dict):
            status = result.get("status")
            if status == "error":
                return False
            if status is not None and status != "success":
                return False

        return True

    def _save_standardized_module(
        self, standardized_instruction: Dict[str, Any], code: str
    ) -> str | None:
        """保存基于参数化标准化指令的模块"""
        if not self.code_cache:
            return None

        # 如果有动态任务类型管理器，注册新的任务类型
        task_type = standardized_instruction.get("task_type", "general")
        if hasattr(self, "task_type_manager"):
            self.task_type_manager.register_task_type(task_type, standardized_instruction)

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
            }

            # 直接调用缓存的保存方法
            result = self.code_cache.save_standardized_module(
                standardized_instruction, code, metadata
            )
            return result
        except Exception:
            return None

    def _build_enhanced_system_prompt(
        self, standardized_instruction: Dict[str, Any], original_prompt: str = None
    ) -> str:
        """基于标准化指令构建增强的系统提示词"""
        task_type = standardized_instruction.get("task_type", "general")

        # 使用AI分析的参数（如果存在）
        parameters = standardized_instruction.get("required_parameters", {})

        # 如果没有智能分析的参数，回退到基础参数
        if not parameters:
            parameters = standardized_instruction.get("parameters", {})

        # 最后的回退：确保有基本的指令参数
        if not parameters:
            parameters = {
                "instruction": {
                    "value": standardized_instruction.get("target", ""),
                    "type": "str",
                    "description": "用户输入的指令内容",
                    "required": True,
                }
            }

        enhanced_prompt = get_enhanced_aiforge_prompt(
            optimize_tokens=self.config.get_optimization_config().get("optimize_tokens", True),
            task_type=task_type,
            parameters=parameters,
        )

        if original_prompt:
            enhanced_prompt += f"\n\n# 原始指令补充\n{original_prompt}"

        return enhanced_prompt

    def _init_config(
        self, config_file: str | None, api_key: str | None, provider: str, **kwargs
    ) -> AIForgeConfig:
        """初始化配置"""

        # 情况3：传入配置文件，以此文件为准（忽略key和provider）
        if config_file:
            return AIForgeConfig(config_file)

        # 情况2：传入key+provider，以此创建（provider必须在默认配置中存在）
        if api_key and provider != "openrouter":
            default_config = AIForgeConfig.get_builtin_default_config()
            if provider not in default_config.get("llm", {}):
                raise ValueError(f"Provider '{provider}' not found in default configuration")
            return AIForgeConfig.from_api_key(api_key, provider, **kwargs)

        # 情况1：只传apikey，使用默认配置创建openrouter
        if api_key:
            return AIForgeConfig.from_api_key(api_key, "openrouter", **kwargs)

        # 其他情况都失败
        raise ValueError(
            "Must provide either: 1) api_key only, 2) api_key + provider, or 3) config_file"
        )

    def _init_executors(self):
        """初始化内置执行器"""
        self.module_executors = [
            SimilarityParameterExecutor(),  # 唯一的统一执行器
        ]

    def generate_and_execute(
        self, instruction: str, system_prompt: str | None = None
    ) -> Tuple[Optional[Dict[str, Any]], str | None]:
        """入口1: 直接生成代码并返回结果，不使用缓存，为一次性操作"""
        if not instruction:
            return None, None

        # 直接调用AI生成代码，不经过标准化指令和缓存
        return self._generate_and_execute_with_code(instruction, system_prompt, None)

    def run(self, instruction: str) -> Optional[Dict[str, Any]]:
        """入口2: 基于标准化指令的统一执行入口"""
        if not instruction:
            return None

        return self._run_with_standardized_instruction(instruction)

    def _run_with_standardized_instruction(self, instruction: str) -> Optional[Dict[str, Any]]:
        """基于标准化指令的统一执行流程"""
        # 第一步：本地标准化指令分析
        if not self.instruction_analyzer:
            result, _ = self._generate_and_execute_with_code(instruction, None, None)
            return result

        # 使用统一的指令分析入口
        standardized_instruction = self._get_final_standardized_instruction(instruction)

        # 根据缓存配置决定执行路径
        if self.code_cache:
            return self._execute_with_cache_first(standardized_instruction, instruction)
        else:
            return self._execute_with_ai_enhanced(standardized_instruction, instruction)

    def _get_final_standardized_instruction(self, instruction: str) -> Dict[str, Any]:
        """获取最终的标准化指令，确保一致性"""
        print(f"[DEBUG] 输入指令: {instruction}")
        # 第一步：本地分析
        local_analysis = self.instruction_analyzer.local_analyze_instruction(instruction)
        print(
            f"[DEBUG] 本地分析结果: task_type={local_analysis.get('task_type')}, confidence={local_analysis.get('confidence')}, cache_key={local_analysis.get('cache_key')}"
        )

        # 第二步：如果置信度低，尝试AI分析
        confidence = local_analysis.get("confidence", 0)
        if confidence < 0.6:
            print(f"[DEBUG] 置信度低({confidence})，尝试AI分析...")
            ai_analysis = self._try_ai_standardization(instruction)
            if ai_analysis and ai_analysis.get("confidence", 0) > confidence:
                # AI分析成功，使用AI结果
                print(
                    f"[DEBUG] AI分析成功: task_type={ai_analysis.get('task_type')}, confidence={ai_analysis.get('confidence')}, cache_key={ai_analysis.get('cache_key')}"
                )

                return ai_analysis
            else:
                print(f"[DEBUG] AI分析失败或置信度不够，使用本地分析结果")

        # 返回本地分析结果
        return local_analysis

    def _execute_with_cache_first(
        self, standardized_instruction: Dict[str, Any], original_instruction: str
    ) -> Optional[Dict[str, Any]]:
        """缓存优先执行策略"""
        # 自动清理检查
        if self.code_cache.should_cleanup():
            self.code_cache.cleanup()

        print(f"[DEBUG] 进入缓存优先执行策略")
        # 使用统一分析结果查找缓存
        cached_modules = self.code_cache.get_cached_modules_by_standardized_instruction(
            standardized_instruction
        )

        if cached_modules:
            print(f"[DEBUG] 找到 {len(cached_modules)} 个缓存模块，尝试执行")

            cache_result = self._try_execute_cached_modules(
                cached_modules, standardized_instruction
            )
            if cache_result is not None:
                print(f"[DEBUG] 缓存执行成功")

                return cache_result
            else:
                print(f"[DEBUG] 缓存执行失败")
        else:
            print(f"[DEBUG] 未找到缓存模块")

        # 缓存失败，走AI生成路径
        print(f"[DEBUG] 缓存未命中，走AI生成路径")
        return self._execute_with_ai_and_cache(standardized_instruction, original_instruction)

    def _execute_with_ai_enhanced(
        self, standardized_instruction: Dict[str, Any], original_instruction: str
    ) -> Optional[Dict[str, Any]]:
        """AI增强执行（无缓存模式）"""
        confidence = standardized_instruction.get("confidence", 0)

        # 使用标准化指令生成代码
        if confidence < 0.6:
            result, _ = self._generate_and_execute_with_code(original_instruction, None, None)
        else:
            enhanced_prompt = self._build_enhanced_system_prompt(standardized_instruction)
            result, _ = self._generate_and_execute_with_code(
                None, enhanced_prompt, standardized_instruction.get("task_type")
            )

        return result

    def _execute_with_ai_and_cache(
        self, standardized_instruction: Dict[str, Any], original_instruction: str
    ) -> Optional[Dict[str, Any]]:
        """AI生成并缓存结果"""
        confidence = standardized_instruction.get("confidence", 0)

        # 使用最终的标准化指令生成代码
        if confidence < 0.6:
            result, code = self._generate_and_execute_with_code(original_instruction, None, None)
        else:
            enhanced_prompt = self._build_enhanced_system_prompt(standardized_instruction)
            result, code = self._generate_and_execute_with_code(
                None, enhanced_prompt, standardized_instruction.get("task_type")
            )

        # 保存成功的代码到缓存
        if result and code and self._is_code_worth_caching(code, result):
            self._save_standardized_module(standardized_instruction, code)

        return result

    def _try_ai_standardization(self, instruction: str) -> Optional[Dict[str, Any]]:
        """尝试AI标准化指令"""
        if not self.instruction_analyzer:
            return None

        print(f"[DEBUG] 开始AI标准化分析: {instruction}")

        try:
            analysis_prompt = self.instruction_analyzer.get_analysis_prompt()
            response = self.instruction_analyzer.llm_client.generate_code(
                f"{analysis_prompt}\n\n用户指令: {instruction}", ""
            )
            ai_analysis = self.instruction_analyzer._parse_standardized_instruction(response)
            print(f"[DEBUG] AI分析原始结果: {ai_analysis}")

            if self.instruction_analyzer._is_ai_analysis_valid(ai_analysis):
                ai_analysis["source"] = "ai_analysis"
                ai_analysis["confidence"] = 0.9
                print(f"[DEBUG] AI分析验证通过: {ai_analysis}")

                return ai_analysis
            else:
                print(f"[DEBUG] AI分析验证失败")
        except Exception as e:
            print(f"[DEBUG] AI分析异常: {e}")
            pass

        return None

    def _try_execute_cached_modules(
        self, cached_modules: List[Any], standardized_instruction: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """尝试执行缓存模块"""
        for module_id, file_path, success_count, failure_count in cached_modules:
            try:
                print(f"[DEBUG] 尝试加载模块: {module_id}")
                module = self.code_cache.load_module(module_id)
                if module:
                    print(f"[DEBUG] 模块加载成功，开始执行")
                    # 正确传递标准化指令
                    result = self._execute_cached_module(
                        module,
                        standardized_instruction.get("target", ""),
                        standardized_instruction=standardized_instruction,
                    )
                    if result:
                        print(f"[DEBUG] 模块执行成功")
                        self.code_cache.update_module_stats(module_id, True)
                        return result
                    else:
                        print(f"[DEBUG] 模块执行返回None")
                        self.code_cache.update_module_stats(module_id, False)
                else:
                    print(f"[DEBUG] 模块加载失败")
            except Exception as e:
                print(f"[DEBUG] 模块执行异常: {e}")
                self.code_cache.update_module_stats(module_id, False)

        return None

    def __call__(self, instruction: str) -> Optional[Dict[str, Any]]:
        """支持直接调用"""
        return self.run(instruction)

    def _generate_and_execute_with_code(
        self,
        instruction: str,
        system_prompt: str | None = None,
        task_type: str = None,
    ) -> Tuple[Optional[Dict[str, Any]], str | None]:
        """生成并执行代码，同时返回结果和代码"""
        client = self.llm_manager.get_client()
        if not client:
            return None, None

        task = None
        try:
            task = self.task_manager.new_task(instruction, client)
            task.run(instruction, system_prompt, task_type)

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

    def _execute_cached_module(self, module, instruction: str, **kwargs):
        """执行缓存的模块 - 支持参数化执行"""
        standardized_instruction = kwargs.get("standardized_instruction", {})

        for executor in self.module_executors:
            if executor.can_handle(module):
                # 传递完整的标准化指令和参数信息
                result = executor.execute(
                    module, instruction, standardized_instruction=standardized_instruction, **kwargs
                )
                if result is not None:
                    return result
        return None

    def _get_module_code(self, file_path: str) -> str:
        """获取模块代码"""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception:
            return ""

    def add_module_executor(self, executor: CachedModuleExecutor):
        """添加自定义模块执行器"""
        self.module_executors.insert(0, executor)

    def switch_provider(self, provider_name: str) -> bool:
        """切换LLM提供商"""
        success = self.llm_manager.switch_client(provider_name)
        if success and self.instruction_analyzer:
            # 同时更新指令分析器的客户端
            new_client = self.llm_manager.get_client()
            if new_client:
                self.instruction_analyzer.llm_client = new_client
        return success

    def list_providers(self) -> Dict[str, str]:
        """列出所有可用的提供商"""
        return {name: client.model for name, client in self.llm_manager.clients.items()}

    def execute_with_runner(self, code: str) -> Dict[str, Any]:
        """使用runner执行代码"""
        return self.runner.execute_code(code)

    # -- 扩展注册接口 - 支持动态加载和配置
    # 目前仅提供接口，后续将完善具体的扩展加载和管理
    # 计划分阶段实现：
    # 1. 扩展注册接口和配置支持
    # 2. 扩展加载和管理逻辑
    # 3. 插件市场和远程配置支持
    def register_extension(self, extension_config: Dict[str, Any]) -> bool:
        """注册扩展组件"""
        extension_type = extension_config.get("type")

        if extension_type == "executor":
            return self._register_executor_extension(extension_config)
        elif extension_type == "template":
            return self._register_template_extension(extension_config)
        elif extension_type == "analyzer":
            return self._register_analyzer_extension(extension_config)

        return False

    def _register_executor_extension(self, executor_config: Dict[str, Any]) -> bool:
        """注册自定义执行器"""
        try:
            # 支持多种注册方式
            if "class" in executor_config:
                # 直接注册执行器类
                executor_instance = executor_config["class"]()
                self.add_module_executor(executor_instance)
                return True
            elif "module_path" in executor_config:
                # 从模块路径动态加载
                import importlib

                module = importlib.import_module(executor_config["module_path"])
                executor_class = getattr(module, executor_config["class_name"])
                executor_instance = executor_class()
                self.add_module_executor(executor_instance)
                return True

            return False
        except Exception:
            return False

    def _register_template_extension(self, config: Dict) -> bool:
        """注册模板扩展"""
        try:
            if not self.code_cache:
                return False

            # 支持多种扩展注册方式
            if "class" in config:
                # 直接注册扩展类
                return self.code_cache.register_template_extension(config)
            elif "config_file" in config:
                # 从配置文件加载扩展
                return self._load_extension_from_config(config["config_file"])
            elif "domain_templates" in config:
                # 直接注册领域模板
                return self._register_domain_templates(config["domain_templates"])

            return False
        except Exception:
            return False

    def _load_extension_from_config(self, config_file: str) -> bool:
        """从配置文件加载扩展"""
        try:
            import tomlkit

            with open(config_file, "r", encoding="utf-8") as f:
                extension_config = tomlkit.load(f)

            # 动态加载扩展类
            module_path = extension_config.get("module")
            class_name = extension_config.get("class")

            import importlib

            module = importlib.import_module(module_path)
            extension_class = getattr(module, class_name)

            extension_config["class"] = extension_class
            return self.code_cache.register_template_extension(extension_config)
        except Exception:
            return False

    def _register_domain_templates(self, domain_templates: Dict) -> bool:
        """注册领域模板"""
        try:
            # 创建简单的模板扩展
            class SimpleDomainExtension(DomainTemplateExtension):
                def __init__(self, domain_name: str, templates: Dict):
                    self.domain_name = domain_name
                    self.templates = templates
                    self.config = {"priority": 10}

                def can_handle(self, standardized_instruction: Dict[str, Any]) -> bool:
                    target = standardized_instruction.get("target", "").lower()
                    return any(
                        keyword in target
                        for template in self.templates.values()
                        for keyword in template.get("keywords", [])
                    )

                def get_template_match(
                    self, standardized_instruction: Dict[str, Any]
                ) -> Optional[Dict]:
                    target = standardized_instruction.get("target", "")
                    for template_name, template_config in self.templates.items():
                        pattern = template_config.get("pattern", "")
                        if pattern and re.search(pattern, target, re.IGNORECASE):
                            return {
                                "template_name": template_name,
                                "template_config": template_config,
                                "domain": self.domain_name,
                            }
                    return None

                def load_templates(self):
                    pass  # 模板已在初始化时设置

            # 为每个领域创建扩展
            for domain_name, templates in domain_templates.items():
                extension = SimpleDomainExtension(domain_name, templates)
                if not self.code_cache.extension_manager.register_template_extension(extension):
                    return False

            return True
        except Exception:
            return False

    def _register_analyzer_extension(self, config: Dict) -> bool:
        """注册分析器扩展"""
        # 扩展指令分析能力
        pass

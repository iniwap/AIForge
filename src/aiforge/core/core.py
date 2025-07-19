from typing import Optional, Dict, Any, Tuple, List
from pathlib import Path
import importlib.resources

from ..config.config import AIForgeConfig
from ..llm.llm_manager import AIForgeLLMManager
from .task_manager import AIForgeManager
from ..cache.template_cache import TemplateBasedCodeCache
from ..execution.executor_interface import (
    DefaultModuleExecutor,
    FunctionBasedExecutor,
    CachedModuleExecutor,
    DataProcessingExecutor,
    WebRequestExecutor,
    FileOperationExecutor,
    APICallExecutor,
)
from .runner import AIForgeRunner
from ..instruction.analyzer import InstructionAnalyzer


class AIForgeCore:
    """AIForge核心接口 - 支持多种初始化方式"""

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

        # 初始化缓存（如果启用）
        self._init_cache()

        # 初始化执行器
        self._init_executors()

        self.instruction_analyzer = None

    def _init_cache(self):
        """初始化缓存 - 默认使用继承了增强功能的模板缓存"""
        cache_config = self.config.get_cache_config("code")
        if cache_config.get("enabled", True):
            cache_dir = Path(self.config.get_workdir()) / "cache"
            self.code_cache = TemplateBasedCodeCache(cache_dir, cache_config)
        else:
            self.code_cache = None

    def _get_instruction_analyzer(self):
        """获取指令分析器"""
        if self.instruction_analyzer is None:
            default_client = self.llm_manager.get_client()
            self.instruction_analyzer = InstructionAnalyzer(default_client)
        return self.instruction_analyzer

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
        lines = [line.strip() for line in code.strip().split("\\n") if line.strip()]

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

    def _is_code_worth_caching(self, code: str, result: Any) -> bool:
        """判断代码是否值得缓存"""
        # 代码必须通过质量验证
        if not self._validate_code_quality(code):
            return False

        # 结果必须表示成功状态
        if isinstance(result, dict):
            status = result.get("status")
            # 只要不是明确的错误状态就认为可能有价值
            if status == "error":
                return False
            # 如果有status字段，必须是success
            if status is not None and status != "success":
                return False

        return True

    def generate_and_execute_with_cache(self, instruction: str, **kwargs) -> tuple:
        """统一的缓存执行入口 - 智能选择最佳缓存策略"""
        # 自动清理检查
        if self.code_cache and self.code_cache.should_cleanup():
            self.code_cache.cleanup()

        if not isinstance(self.code_cache, TemplateBasedCodeCache):
            return self._fallback_cache_execution(instruction, **kwargs)

        # 优先尝试标准化指令缓存
        try:
            analyzer = self._get_instruction_analyzer()
            standardized_instruction = analyzer.analyze_instruction(instruction)

            cached_modules = self.code_cache.get_cached_modules_by_standardized_instruction(
                standardized_instruction
            )

            if cached_modules:
                return self._execute_cached_modules(
                    cached_modules, standardized_instruction, **kwargs
                )
        except Exception:
            pass  # 回退到模板缓存

        # 回退到模板缓存
        return self._execute_template_cache(instruction, **kwargs)

    def _execute_cached_modules(self, cached_modules, standardized_instruction, **kwargs):
        """执行缓存的标准化模块"""
        for module_id, file_path, success_count, failure_count, _ in cached_modules:
            try:
                result = self.code_cache.execute_template_module(
                    module_id, standardized_instruction.get("parameters", {})
                )
                if result:
                    self.code_cache.update_module_stats(module_id, True)
                    return result, self._get_module_code(file_path)
            except Exception:
                self.code_cache.update_module_stats(module_id, False)

        # 如果所有缓存模块都失败，生成新代码
        return self._generate_new_code_with_standardized_instruction(
            standardized_instruction, **kwargs
        )

    def _execute_template_cache(self, instruction: str, **kwargs):
        """执行模板缓存逻辑"""
        cached_modules = self.code_cache.get_cached_modules_by_template(instruction)

        if cached_modules:
            template_info = self.code_cache._extract_template_info(instruction)
            current_params = template_info["parameters"]

            for (
                module_id,
                file_path,
                success_count,
                failure_count,
                original_params,
            ) in cached_modules:
                try:
                    result = self.code_cache.execute_template_module(module_id, current_params)
                    if result:
                        self.code_cache.update_module_stats(module_id, True)
                        return result, self._get_module_code(file_path)
                    else:
                        self.code_cache.update_module_stats(module_id, False)
                except Exception:
                    self.code_cache.update_module_stats(module_id, False)

        # 缓存未命中，生成新代码
        return self._generate_new_code_with_template(instruction, **kwargs)

    def _fallback_cache_execution(self, instruction: str, **kwargs):
        """回退到基础缓存执行"""
        if self.code_cache:
            cached_modules = self.code_cache.get_cached_modules(instruction)
            for module_id, file_path, success_count, failure_count in cached_modules:
                module = self.code_cache.load_module(module_id)
                if module:
                    try:
                        result = self._execute_cached_module(module, instruction, **kwargs)
                        if result:
                            self.code_cache.update_module_stats(module_id, True)
                            return result, self._get_module_code(file_path)
                        else:
                            self.code_cache.update_module_stats(module_id, False)
                    except Exception:
                        self.code_cache.update_module_stats(module_id, False)

        # 缓存未命中，使用AI生成
        result, code = self.generate_and_execute_with_code(
            instruction, kwargs.get("system_prompt", None), kwargs.get("provider", None)
        )

        # 保存成功的代码到缓存
        if self.code_cache and result and code and self._is_code_worth_caching(code, result):
            self.code_cache.save_code_module(instruction, code)

        return result, code

    def _generate_new_code_with_standardized_instruction(self, standardized_instruction, **kwargs):
        """使用标准化指令生成新代码"""
        enhanced_system_prompt = self._build_enhanced_system_prompt(
            standardized_instruction, kwargs.get("system_prompt")
        )

        # 从标准化指令中提取原始指令
        original_instruction = standardized_instruction.get("target", "")

        result, code = self.generate_and_execute_with_code(
            original_instruction, enhanced_system_prompt, kwargs.get("provider")
        )

        # 保存成功的代码到缓存
        if self.code_cache and result and code and self._is_code_worth_caching(code, result):
            self.code_cache.save_module(standardized_instruction, code)

        return result, code

    def _generate_new_code_with_template(self, instruction: str, **kwargs):
        """使用模板生成新代码"""
        result, code = self.generate_and_execute_with_code(
            instruction, kwargs.get("system_prompt", None), kwargs.get("provider", None)
        )

        # 只保存真正成功且有用的代码到缓存
        if self.code_cache and result and code and self._is_code_worth_caching(code, result):
            self.code_cache.save_module(instruction, code)

        return result, code

    def _build_enhanced_system_prompt(
        self, standardized_instruction: Dict[str, Any], original_prompt: str = None
    ) -> str:
        """基于标准化指令构建增强的系统提示词"""
        task_type = standardized_instruction.get("task_type", "general")
        action = standardized_instruction.get("action", "process")
        target = standardized_instruction.get("target", "")

        base_prompt = f"""
# 任务类型: {task_type}
# 操作动作: {action}
# 操作目标: {target}

# 代码生成规则
- 生成针对 {task_type} 任务的专用代码
- 重点处理 {action} 操作
- 目标对象: {target}
- 将最终结果赋值给 __result__ 变量
- 确保结果格式为: {standardized_instruction.get("output_format", "general")}
"""

        if original_prompt:
            return f"{base_prompt}\\n\\n# 原始指令\\n{original_prompt}"

        return base_prompt

    def _init_config(
        self, config_file: str | None, api_key: str | None, provider: str, **kwargs
    ) -> AIForgeConfig:
        """初始化配置"""
        if api_key:
            return self._create_quick_config(api_key, provider, **kwargs)
        elif config_file:
            return AIForgeConfig(config_file)
        else:
            return self._create_default_config(**kwargs)

    def _create_quick_config(self, api_key: str, provider: str, **kwargs) -> AIForgeConfig:
        """创建快速启动配置"""
        default_config = self._get_default_config()

        if provider in default_config.get("llm", {}):
            default_config["llm"][provider]["api_key"] = api_key
            default_config["default_llm_provider"] = provider

        for key, value in kwargs.items():
            if key in ["max_rounds", "max_tokens", "workdir"]:
                default_config[key] = value

        return AIForgeConfig.from_dict(default_config)

    def _create_default_config(self, **kwargs) -> AIForgeConfig:
        """创建默认配置"""
        default_config = self._get_default_config()

        for key, value in kwargs.items():
            if key in default_config:
                default_config[key] = value

        return AIForgeConfig.from_dict(default_config)

    def _get_default_config(self) -> Dict:
        """获取内置默认配置"""
        try:
            with importlib.resources.files("aiforge.config").joinpath("default.toml").open() as f:
                import tomlkit

                return tomlkit.load(f)
        except Exception:
            return {
                "workdir": "aiforge_work",
                "max_tokens": 4096,
                "max_rounds": 5,
                "default_llm_provider": "openrouter",
                "llm": {
                    "openrouter": {
                        "type": "openai",
                        "model": "deepseek/deepseek-chat-v3-0324:free",
                        "api_key": "",
                        "base_url": "https://openrouter.ai/api/v1",
                        "timeout": 30,
                        "max_tokens": 8192,
                        "enable": True,
                    }
                },
                "cache": {
                    "code": {
                        "enabled": True,
                        "max_modules": 20,
                        "failure_threshold": 0.8,
                        "max_age_days": 30,
                        "cleanup_interval": 10,
                    }
                },
            }

    def _init_executors(self):
        """初始化内置执行器"""
        self.module_executors = [
            DefaultModuleExecutor(),
            FunctionBasedExecutor("search_web"),
            DataProcessingExecutor(),
            WebRequestExecutor(),
            FileOperationExecutor(),
            APICallExecutor(),
            FunctionBasedExecutor("main"),
            FunctionBasedExecutor("run"),
        ]

    def run(
        self, instruction: str, system_prompt: str | None = None, provider: str | None = None
    ) -> Optional[Dict[str, Any]]:
        """执行任务 - 统一入口"""
        return self.run_task(instruction, system_prompt, provider)

    def __call__(self, instruction: str, **kwargs) -> Optional[Dict[str, Any]]:
        """支持直接调用"""
        return self.run(instruction, **kwargs)

    def run_task(
        self, instruction: str, system_prompt: str | None = None, provider: str | None = None
    ) -> Optional[Dict[str, Any]]:
        """任务执行入口 - 使用统一缓存策略"""
        if self.code_cache:
            result, _ = self.generate_and_execute_with_cache(
                instruction, system_prompt=system_prompt, provider=provider
            )
        else:
            result, _ = self.generate_and_execute_with_code(instruction, system_prompt, provider)
        return result

    def generate_and_execute_with_code(
        self, instruction: str, system_prompt: str | None = None, provider: str | None = None
    ) -> Tuple[Optional[Dict[str, Any]], str | None]:
        """生成并执行代码，同时返回结果和代码"""
        client = self.llm_manager.get_client(provider)
        if not client:
            return None, None

        task = None
        try:
            task = self.task_manager.new_task(instruction, client)
            task.run(instruction, system_prompt)

            # 查找最有价值的成功执行代码（优先选择功能代码而非数据赋值）
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
            lines = code.strip().split("\\n")
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
        """执行缓存的模块 - 使用策略模式"""
        for executor in self.module_executors:
            if executor.can_handle(module):
                result = executor.execute(module, instruction, **kwargs)
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
        return self.llm_manager.switch_client(provider_name)

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

    def _register_executor_extension(self, config: Dict) -> bool:
        """注册执行器扩展"""
        # 基于配置动态创建执行器
        pass

    def _register_template_extension(self, config: Dict) -> bool:
        """注册模板扩展"""
        # 向缓存系统添加新模板
        pass

    def _register_analyzer_extension(self, config: Dict) -> bool:
        """注册分析器扩展"""
        # 扩展指令分析能力
        pass

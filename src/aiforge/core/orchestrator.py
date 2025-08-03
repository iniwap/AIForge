import re
from typing import Dict, Any, Optional
from pathlib import Path
import importlib

from ..config.config import AIForgeConfig
from ..llm.llm_manager import AIForgeLLMManager
from .task.manager import AIForgeTaskManager
from .managers.search_manager import AIForgeSearchManager
from .managers.execution_manager import AIForgeExecutionManager
from .runner import AIForgeRunner
from ..instruction.analyzer import AIForgeInstructionAnalyzer
from ..cache.semantic_cache import EnhancedStandardizedCache
from ..cache.dynamic_task_type_manager import DynamicTaskTypeManager
from ..adapters.output.enhanced_hybrid_adapter import EnhancedHybridUIAdapter
from ..adapters.input.input_adapter_manager import InputAdapterManager
from ..extensions.template_extension import DomainTemplateExtension
from ..templates.template_manager import TemplateManager
from .managers.config_manager import AIForgeConfigManager
from ..strategies.parameter_mapping_service import ParameterMappingService
from ..execution.engine import AIForgeExecutionEngine
from .managers.content_generation_manager import AIForgeContentGenerationManager


class AIForgeOrchestrator:
    """系统组件编排器"""

    def __init__(self):
        self.components: Dict[str, Any] = {}
        self.config: Optional[AIForgeConfig] = None
        self._initialized = False

    def initialize_components(self, config_file, api_key, provider, **kwargs) -> Dict[str, Any]:
        """初始化所有组件"""

        # 1. 基础配置和核心服务
        self._init_config_manager(config_file, api_key, provider, **kwargs)
        self._init_cache()
        self._init_llm_manager()

        # 2. 参数映射服务（必须在依赖它的组件之前初始化）
        self._init_parameter_mapping_service()

        # 3. 执行相关组件（依赖参数映射服务）
        self._init_execution_engine()
        self._init_task_manager()
        self._init_runner()

        # 4. 分析
        self._init_instruction_analyzer()

        # 5. 适配器
        self._init_adapters()

        # 6. 管理器组件（依赖参数映射服务）
        self._init_execution_manager()
        self._init_template_manager()
        self._init_search_manager()
        self._init_content_generation_manager()

        self._initialized = True

    def _init_config_manager(self, config_file, api_key, provider, **kwargs):
        self.components["config_manager"] = AIForgeConfigManager()
        self.config = self.components["config_manager"].initialize_config(
            config_file, api_key, provider, **kwargs
        )

    def _init_llm_manager(self):
        """初始化LLM管理器"""
        self.components["llm_manager"] = AIForgeLLMManager(self.config)

    def _init_task_manager(self):
        """初始化任务管理器"""
        llm_manager = self.components["llm_manager"]
        self.components["task_manager"] = AIForgeTaskManager(llm_manager, self.components)

    def _init_execution_manager(self):
        self.components["execution_manager"] = AIForgeExecutionManager()
        self.components["execution_manager"].initialize(self.components, self.config)

    def _init_search_manager(self):
        self.components["search_manager"] = AIForgeSearchManager(self.components)

    def _init_template_manager(self):
        """初始化模板管理器"""
        parameter_mapping_service = self.components.get("parameter_mapping_service")
        template_manager = TemplateManager(parameter_mapping_service)
        template_manager.initialize()
        self.components["template_manager"] = template_manager

    def _init_runner(self):
        """初始化代码执行器"""
        workdir = str(self.config.get_workdir())
        self.components["runner"] = AIForgeRunner(workdir)

    def _init_instruction_analyzer(self):
        """初始化指令分析器"""
        llm_manager = self.components["llm_manager"]
        default_client = llm_manager.get_client()
        self.components["instruction_analyzer"] = (
            AIForgeInstructionAnalyzer(default_client) if default_client else None
        )

    def _init_cache(self):
        """初始化缓存系统"""
        cache_config = self.config.get_cache_config("code")
        if cache_config.get("enabled", True):
            cache_dir = Path(self.config.get_workdir()) / "cache"
            code_cache = EnhancedStandardizedCache(cache_dir, cache_config)

            # 初始化动态任务类型管理器
            task_type_manager = DynamicTaskTypeManager(cache_dir)
            code_cache.task_type_manager = task_type_manager

            # 将管理器传递给指令分析器
            instruction_analyzer = self.components.get("instruction_analyzer")
            if instruction_analyzer:
                instruction_analyzer.task_type_manager = task_type_manager

            self.components["code_cache"] = code_cache
            self.components["task_type_manager"] = task_type_manager
        else:
            self.components["code_cache"] = None
            self.components["task_type_manager"] = None

    def _init_parameter_mapping_service(self):
        """初始化参数映射服务"""
        cache_dir = self.config.get_workdir() / "cache" if self.config else None
        self.components["parameter_mapping_service"] = ParameterMappingService(cache_dir)

    def _init_execution_engine(self):
        """初始化执行引擎"""

        execution_engine = AIForgeExecutionEngine(self.components)
        self.components["execution_engine"] = execution_engine

    def _init_content_generation_manager(self):
        """初始化内容生成管理器"""
        self.components["content_generation_manager"] = AIForgeContentGenerationManager(
            self.components
        )

    def _init_adapters(self):
        """初始化适配器"""
        self.components["ui_adapter"] = None  # 延迟初始化
        self.components["input_adapter_manager"] = InputAdapterManager()

    def get_component(self, component_name: str) -> Any:
        """获取组件"""
        if not self._initialized:
            raise RuntimeError("Components not initialized")
        return self.components.get(component_name)

    def init_ui_adapter(self):
        """延迟初始化UI适配器"""
        if self.components["ui_adapter"] is None:
            llm_manager = self.components["llm_manager"]
            default_client = llm_manager.get_client()
            if default_client:
                self.components["ui_adapter"] = EnhancedHybridUIAdapter(default_client)

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
            if "class" in executor_config:
                executor_instance = executor_config["class"]()
                self.components["module_executors"].insert(0, executor_instance)
                return True
            elif "module_path" in executor_config:
                module = importlib.import_module(executor_config["module_path"])
                executor_class = getattr(module, executor_config["class_name"])
                executor_instance = executor_class()
                self.components["module_executors"].insert(0, executor_instance)
                return True
            return False
        except Exception:
            return False

    def _register_template_extension(self, config: Dict) -> bool:
        """注册模板扩展"""
        try:
            code_cache = self.components.get("code_cache")
            if not code_cache:
                return False

            if "class" in config:
                return code_cache.register_template_extension(config)
            elif "config_file" in config:
                return self._load_extension_from_config(config["config_file"])
            elif "domain_templates" in config:
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
            code_cache = self.components.get("code_cache")
            return code_cache.register_template_extension(extension_config)
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
            code_cache = self.components.get("code_cache")
            for domain_name, templates in domain_templates.items():
                extension = SimpleDomainExtension(domain_name, templates)
                if not code_cache.extension_manager.register_template_extension(extension):
                    return False

            return True
        except Exception:
            return False

    def _register_analyzer_extension(self, config: Dict) -> bool:
        """注册分析器扩展"""
        # 扩展指令分析能力
        pass

    def switch_provider(self, provider_name: str) -> bool:
        """切换LLM提供商"""
        llm_manager = self.components["llm_manager"]
        success = llm_manager.switch_client(provider_name)

        if success:
            instruction_analyzer = self.components.get("instruction_analyzer")
            if instruction_analyzer:
                new_client = llm_manager.get_client()
                if new_client:
                    instruction_analyzer.llm_client = new_client

        return success

    def cleanup_components(self):
        """清理组件资源"""
        for component_name, component in self.components.items():
            if hasattr(component, "cleanup"):
                try:
                    component.cleanup()
                except Exception as e:
                    print(f"[WARNING] 清理组件 {component_name} 时出错: {e}")

        self.components.clear()
        self._initialized = False

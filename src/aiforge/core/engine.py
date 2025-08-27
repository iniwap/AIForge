from typing import Dict, Any, Optional, List, Tuple

from .orchestrator import AIForgeOrchestrator
from .result import convert_to_aiforge_result, AIForgeResult


class AIForgeEngine:
    """AIForge核心引擎"""

    def __init__(
        self,
        config_file: str | None = None,
        api_key: str | None = None,
        provider: str = "openrouter",
        **kwargs,
    ):
        """
        初始化AIForge核心引擎

        Args:
            config_file: 配置文件路径（可选）
            api_key: API密钥（快速启动模式）
            provider: LLM提供商名称
            **kwargs: 其他配置参数（max_rounds, workdir等）
        """
        # 初始化组件管理器
        self.component_manager = AIForgeOrchestrator()
        self.component_manager.initialize_components(config_file, api_key, provider, **kwargs)

    def run(self, instruction: str) -> Optional[AIForgeResult]:
        """入口：基于标准化指令的统一执行入口"""
        execution_manager = self.component_manager.get_component("execution_manager")
        if not execution_manager:
            return None

        internal_result = execution_manager.execute_instruction(instruction)
        return convert_to_aiforge_result(internal_result, None)

    def generate_and_execute(
        self, instruction: str, system_prompt: str | None = None
    ) -> Tuple[Optional[AIForgeResult], str | None]:
        """入口：直接生成代码并返回结果，不使用缓存"""
        if not instruction:
            return None, None

        execution_manager = self.component_manager.get_component("execution_manager")
        if not execution_manager:
            return None, None

        result, code, success = execution_manager.generate_and_execute_with_code(
            instruction, system_prompt, None, None
        )
        if not success:
            return None, None
        else:
            converted_result = convert_to_aiforge_result(result, None)
            return converted_result, code

    def process_input(
        self, raw_input_x: Any, source: str, context_data: Optional[Dict[str, Any]] = None
    ) -> str:
        """处理多端输入并返回标准化指令"""
        execution_manager = self.component_manager.get_component("execution_manager")
        if not execution_manager:
            return None

        return execution_manager.process_input(raw_input_x, source, context_data)

    def run_with_input_adaptation(
        self, raw_input_x: Any, source: str, context_data: Optional[Dict[str, Any]] = None
    ) -> Optional[AIForgeResult]:
        """带输入适配的运行方法"""
        # 适配输入
        instruction = self.process_input(raw_input_x, source, context_data)

        # 执行任务
        return self.run(instruction)

    def adapt_result_for_ui(
        self, result: AIForgeResult, ui_type: str = None, context: str = "web"
    ) -> Dict[str, Any]:
        """智能适配结果为UI格式"""
        self.component_manager.init_ui_adapter()
        ui_adapter = self.component_manager.get_component("ui_adapter")
        if ui_adapter:
            return ui_adapter.adapt_data(result, ui_type, context)
        return result

    def get_ui_adaptation_stats(self) -> Dict[str, Any]:
        """获取UI适配统计信息"""
        ui_adapter = self.component_manager.get_component("ui_adapter")
        if ui_adapter:
            return ui_adapter.get_adaptation_stats()
        return {}

    def get_supported_ui_combinations(self) -> Dict[str, List[str]]:
        """获取支持的UI组合"""
        ui_adapter = self.component_manager.get_component("ui_adapter")
        if ui_adapter:
            return ui_adapter.get_supported_combinations()
        return {}

    def switch_provider(self, provider_name: str) -> bool:
        """切换LLM提供商"""
        return self.component_manager.switch_provider(provider_name)

    def list_providers(self) -> Dict[str, str]:
        """列出所有可用的提供商"""
        llm_manager = self.component_manager.get_component("llm_manager")
        return {name: client.model for name, client in llm_manager.clients.items()}

    def get_system_info(self) -> Dict[str, Any]:
        """获取系统信息"""
        instruction_analyzer = self.component_manager.get_component("instruction_analyzer")
        if instruction_analyzer:
            return {
                "task_types": instruction_analyzer._get_task_type_recommendations(),
                "usage_stats": instruction_analyzer.get_task_type_usage_stats(),
                "optimizations": instruction_analyzer.recommend_task_type_optimizations(),
            }
        return {}

    def register_extension(self, extension_config: Dict[str, Any]) -> bool:
        """注册扩展组件"""
        return self.component_manager.register_extension(extension_config)

    def add_module_executor(self, executor):
        """添加自定义模块执行器"""
        self.component_manager.add_module_executor(executor)

    def __call__(self, instruction: str) -> Optional[Dict[str, Any]]:
        """支持直接调用"""
        return self.run(instruction)

    def shutdown(self):
        """清理资源"""
        self.component_manager.shutdown()

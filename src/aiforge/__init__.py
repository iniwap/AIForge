# 核心模块导入
from .core.engine import AIForgeEngine
from .core.task.manager import AIForgeTaskManager
from .core.task.task import AIForgeTask
from .execution.result_processor import AIForgeResultProcessor

# LLM模块导入
from .llm.llm_client import AIForgeLLMClient, AIForgeOllamaClient
from .llm.llm_manager import AIForgeLLMManager

# 执行引擎导入
from .execution.engine import AIForgeExecutionEngine

# 配置管理导入
from .config.config import AIForgeConfig

# 数据获取相关导入
from .templates.template_manager import TemplateManager
from .strategies.search_template_strategy import (
    StandardTemplateStrategy,
    TemplateGenerationStrategy,
)
from .strategies.semantic_field_strategy import SemanticFieldStrategy, FieldProcessorManager

# 其他相关导入
from .execution.result_formatter import AIForgeResultFormatter
from .execution.code_blocks import CodeBlockManager, CodeBlock
from .core.prompt import AIForgePrompt
from .cli.wizard import create_config_wizard
from .cache.semantic_cache import EnhancedStandardizedCache

# 指令分析导入
from .instruction.analyzer import AIForgeInstructionAnalyzer
from .core.managers import AIForgeExecutionManager
from .i18n.manager import AIForgeI18nManager, GlobalI18nManager
from .core.managers.streaming_execution_manager import AIForgeStreamingExecutionManager
from .core.result import AIForgeResult
from .core.managers.shutdown_manager import AIForgeShutdownManager
from .core.path_manager import AIForgePathManager

from .utils.progress_indicator import ProgressEventBus, StreamingProgressEventHandler


__all__ = [
    # 核心组件
    "AIForgeEngine",
    "AIForgeTaskManager",
    "AIForgeTask",
    "AIForgeResultProcessor",
    "AIForgeConfig",
    "AIForgePathManager",
    # LLM组件
    "AIForgeLLMClient",
    "AIForgeOllamaClient",
    "AIForgeLLMManager",
    # 执行组件
    "AIForgeExecutionEngine",
    "EnhancedStandardizedCache",
    # 数据获取组件
    "TemplateManager",
    "StandardTemplateStrategy",
    "TemplateGenerationStrategy",
    "SemanticFieldStrategy",
    "FieldProcessorManager",
    "AIForgeInstructionAnalyzer",
    # 工具组件
    "create_config_wizard",
    "AIForgeResultFormatter",
    "CodeBlockManager",
    "CodeBlock",
    "AIForgePrompt",
    "AIForgeExecutionManager",
    "AIForgeI18nManager",
    "GlobalI18nManager",
    "AIForgeStreamingExecutionManager",
    "AIForgeResult",
    "AIForgeShutdownManager",
    # 流式进度显示
    "ProgressEventBus",
    "StreamingProgressEventHandler",
]

__version__ = "0.0.15"

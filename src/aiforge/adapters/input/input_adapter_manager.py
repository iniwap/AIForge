from typing import List, Dict, Any, Optional
from .input_adapter import InputAdapter, InputSource, InputContext, StandardizedInput
from .cli_input_adapter import CLIInputAdapter
from .gui_input_adapter import GUIInputAdapter
from .web_input_adapter import WebInputAdapter
from .mobile_input_adapter import MobileInputAdapter
from .voice_input_adapter import VoiceInputAdapter


class InputAdapterManager:
    """输入适配管理器"""

    def __init__(self):
        self.adapters: List[InputAdapter] = [
            CLIInputAdapter(),
            GUIInputAdapter(),
            WebInputAdapter(),
            MobileInputAdapter(),
            VoiceInputAdapter(),
        ]

        # 输入预处理器
        self.preprocessors = []

        # 输入后处理器
        self.postprocessors = []

    def register_adapter(self, adapter: InputAdapter):
        """注册自定义适配器"""
        self.adapters.append(adapter)

    def adapt_input(
        self, raw_input: Any, source: InputSource, context_data: Optional[Dict[str, Any]] = None
    ) -> StandardizedInput:
        """适配输入"""
        # 创建输入上下文
        context = self._create_context(source, context_data or {})

        # 预处理
        processed_input = self._preprocess(raw_input, context)

        # 找到合适的适配器
        adapter = self._find_adapter(processed_input, source)
        if not adapter:
            raise ValueError(f"No adapter found for source: {source}")

        # 执行适配
        standardized_input = adapter.adapt(processed_input, context)

        # 验证
        if not adapter.validate(standardized_input):
            raise ValueError("Input validation failed")

        # 后处理
        final_input = self._postprocess(standardized_input)

        return final_input

    def _create_context(self, source: InputSource, context_data: Dict[str, Any]) -> InputContext:
        """创建输入上下文"""
        return InputContext(
            source=source,
            user_id=context_data.get("user_id"),
            session_id=context_data.get("session_id"),
            device_info=context_data.get("device_info", {}),
            preferences=context_data.get("preferences", {}),
        )

    def _find_adapter(self, raw_input: Any, source: InputSource) -> Optional[InputAdapter]:
        """找到合适的适配器"""
        for adapter in self.adapters:
            if adapter.can_handle(raw_input, source):
                return adapter
        return None

    def _preprocess(self, raw_input: Any, context: InputContext) -> Any:
        """预处理输入"""
        processed = raw_input
        for preprocessor in self.preprocessors:
            processed = preprocessor.process(processed, context)
        return processed

    def _postprocess(self, standardized_input: StandardizedInput) -> StandardizedInput:
        """后处理标准化输入"""
        processed = standardized_input
        for postprocessor in self.postprocessors:
            processed = postprocessor.process(processed)
        return processed

    def get_supported_sources(self) -> List[InputSource]:
        """获取支持的输入源"""
        return list(InputSource)

    def get_adapter_stats(self) -> Dict[str, Any]:
        """获取适配器统计信息"""
        return {
            "total_adapters": len(self.adapters),
            "supported_sources": [source.value for source in self.get_supported_sources()],
            "preprocessors": len(self.preprocessors),
            "postprocessors": len(self.postprocessors),
        }

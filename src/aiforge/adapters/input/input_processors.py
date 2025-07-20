from abc import ABC, abstractmethod
from typing import Any
from .input_adapter import InputContext, StandardizedInput


class InputPreprocessor(ABC):
    """输入预处理器基类"""

    @abstractmethod
    def process(self, raw_input: Any, context: InputContext) -> Any:
        pass


class InputPostprocessor(ABC):
    """输入后处理器基类"""

    @abstractmethod
    def process(self, standardized_input: StandardizedInput) -> StandardizedInput:
        pass


class TextCleanupPreprocessor(InputPreprocessor):
    """文本清理预处理器"""

    def process(self, raw_input: Any, context: InputContext) -> Any:
        if isinstance(raw_input, str):
            # 清理多余空白字符
            return raw_input.strip()
        elif isinstance(raw_input, dict) and "text" in raw_input:
            raw_input["text"] = raw_input["text"].strip()
        return raw_input


class SecurityValidationPostprocessor(InputPostprocessor):
    """安全验证后处理器"""

    def process(self, standardized_input: StandardizedInput) -> StandardizedInput:
        # 检查指令长度
        if len(standardized_input.instruction) > 100000:
            raise ValueError("Instruction too long")

        # 检查恶意内容（简单示例）
        dangerous_patterns = ["rm -rf", "del /", "format c:"]
        for pattern in dangerous_patterns:
            if pattern.lower() in standardized_input.instruction.lower():
                raise ValueError(f"Potentially dangerous instruction detected: {pattern}")

        return standardized_input

from typing import Any
from .input_adapter import InputAdapter, InputSource, InputContext, StandardizedInput


class CLIInputAdapter(InputAdapter):
    """CLI输入适配器"""

    def can_handle(self, raw_input: Any, source: InputSource) -> bool:
        return source == InputSource.CLI and isinstance(raw_input, (str, dict))

    def adapt(self, raw_input: Any, context: InputContext) -> StandardizedInput:
        """适配CLI输入"""
        if isinstance(raw_input, str):
            # 简单字符串指令
            instruction = raw_input
            metadata = {"input_type": "simple_command"}
        elif isinstance(raw_input, dict):
            # 结构化CLI参数
            instruction = raw_input.get("instruction", "")
            metadata = {
                "input_type": "structured_command",
                "args": raw_input.get("args", {}),
                "flags": raw_input.get("flags", {}),
                "options": raw_input.get("options", {}),
            }
        else:
            raise ValueError(f"Unsupported CLI input type: {type(raw_input)}")

        # CLI特定的元数据
        metadata.update(
            {
                "terminal_width": context.device_info.get("terminal_width", 80),
                "supports_color": context.device_info.get("supports_color", True),
                "shell_type": context.device_info.get("shell", "bash"),
            }
        )

        return StandardizedInput(instruction=instruction, context=context, metadata=metadata)

    def validate(self, standardized_input: StandardizedInput) -> bool:
        """验证CLI输入"""
        return (
            bool(standardized_input.instruction.strip())
            and len(standardized_input.instruction) <= 10000  # CLI输入长度限制
        )

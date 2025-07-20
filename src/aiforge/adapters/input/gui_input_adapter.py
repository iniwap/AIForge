from typing import Any

from .input_adapter import InputAdapter, InputSource, InputContext, StandardizedInput


class GUIInputAdapter(InputAdapter):
    """GUI输入适配器"""

    def can_handle(self, raw_input: Any, source: InputSource) -> bool:
        return source == InputSource.GUI and isinstance(raw_input, dict)

    def adapt(self, raw_input: Any, context: InputContext) -> StandardizedInput:
        """适配GUI输入"""
        instruction = raw_input.get("text", "")

        # GUI特定的元数据
        metadata = {
            "input_type": "gui_text",
            "widget_id": raw_input.get("widget_id"),
            "cursor_position": raw_input.get("cursor_position", 0),
            "selection": raw_input.get("selection", {}),
            "input_method": raw_input.get("input_method", "keyboard"),
            "screen_size": context.device_info.get("screen_size", {}),
            "theme": context.preferences.get("theme", "default"),
        }

        # 处理附件（如果有）
        attachments = {}
        if "files" in raw_input:
            attachments["files"] = raw_input["files"]
        if "images" in raw_input:
            attachments["images"] = raw_input["images"]

        return StandardizedInput(
            instruction=instruction, context=context, metadata=metadata, attachments=attachments
        )

    def validate(self, standardized_input: StandardizedInput) -> bool:
        """验证GUI输入"""
        return bool(standardized_input.instruction.strip())

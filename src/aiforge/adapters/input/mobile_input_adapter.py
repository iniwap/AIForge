from typing import Any

from .input_adapter import InputAdapter, InputSource, InputContext, StandardizedInput


class MobileInputAdapter(InputAdapter):
    """移动端输入适配器"""

    def can_handle(self, raw_input: Any, source: InputSource) -> bool:
        return source == InputSource.MOBILE and isinstance(raw_input, dict)

    def adapt(self, raw_input: Any, context: InputContext) -> StandardizedInput:
        """适配移动端输入"""
        instruction = raw_input.get("text", "")

        # 移动端特定的元数据
        metadata = {
            "input_type": "mobile_input",
            "input_method": raw_input.get("input_method", "touch"),  # touch, voice, gesture
            "orientation": context.device_info.get("orientation", "portrait"),
            "device_type": context.device_info.get("device_type", "phone"),  # phone, tablet
            "os": context.device_info.get("os", "unknown"),
            "app_version": context.device_info.get("app_version", ""),
            "network_type": context.device_info.get("network", "wifi"),
            "battery_level": context.device_info.get("battery", 100),
            "location": raw_input.get("location", {}) if raw_input.get("location_enabled") else {},
        }

        # 处理移动端特有的输入
        attachments = {}
        if "photos" in raw_input:
            attachments["photos"] = raw_input["photos"]
        if "voice_recording" in raw_input:
            attachments["voice"] = raw_input["voice_recording"]
        if "camera_capture" in raw_input:
            attachments["camera"] = raw_input["camera_capture"]

        return StandardizedInput(
            instruction=instruction, context=context, metadata=metadata, attachments=attachments
        )

    def validate(self, standardized_input: StandardizedInput) -> bool:
        """验证移动端输入"""
        # 移动端输入可能更简短
        return (
            bool(standardized_input.instruction.strip())
            and len(standardized_input.instruction) <= 5000
        )

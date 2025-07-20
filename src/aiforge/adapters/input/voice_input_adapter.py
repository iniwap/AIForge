from typing import Any

from .input_adapter import InputAdapter, InputSource, InputContext, StandardizedInput


class VoiceInputAdapter(InputAdapter):
    """语音输入适配器"""

    def can_handle(self, raw_input: Any, source: InputSource) -> bool:
        return source == InputSource.VOICE and isinstance(raw_input, dict)

    def adapt(self, raw_input: Any, context: InputContext) -> StandardizedInput:
        """适配语音输入"""
        # 语音转文字后的指令
        instruction = raw_input.get("transcribed_text", "")

        # 语音特定的元数据
        metadata = {
            "input_type": "voice_input",
            "audio_format": raw_input.get("audio_format", "wav"),
            "sample_rate": raw_input.get("sample_rate", 16000),
            "duration": raw_input.get("duration", 0),
            "confidence_score": raw_input.get("confidence", 0.0),
            "language": raw_input.get("detected_language", "zh-CN"),
            "speaker_id": raw_input.get("speaker_id"),
            "noise_level": raw_input.get("noise_level", "low"),
            "transcription_engine": raw_input.get("engine", "default"),
        }

        # 保存原始音频数据
        attachments = {}
        if "audio_data" in raw_input:
            attachments["audio"] = raw_input["audio_data"]

        return StandardizedInput(
            instruction=instruction, context=context, metadata=metadata, attachments=attachments
        )

    def validate(self, standardized_input: StandardizedInput) -> bool:
        """验证语音输入"""
        confidence = standardized_input.metadata.get("confidence_score", 0.0)
        return (
            bool(standardized_input.instruction.strip()) and confidence >= 0.6  # 语音识别置信度阈值
        )

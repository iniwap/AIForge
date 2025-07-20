from typing import Any

from .input_adapter import InputAdapter, InputSource, InputContext, StandardizedInput


class WebInputAdapter(InputAdapter):
    """Web输入适配器"""

    def can_handle(self, raw_input: Any, source: InputSource) -> bool:
        return source == InputSource.WEB and isinstance(raw_input, dict)

    def adapt(self, raw_input: Any, context: InputContext) -> StandardizedInput:
        """适配Web输入"""
        instruction = raw_input.get("instruction", "")

        # Web特定的元数据
        metadata = {
            "input_type": "web_request",
            "http_method": raw_input.get("method", "POST"),
            "user_agent": raw_input.get("user_agent", ""),
            "ip_address": raw_input.get("ip_address", ""),
            "referrer": raw_input.get("referrer", ""),
            "browser_info": context.device_info.get("browser", {}),
            "viewport": context.device_info.get("viewport", {}),
            "request_id": raw_input.get("request_id"),
        }

        # 处理Web特有的参数
        if "form_data" in raw_input:
            metadata["form_data"] = raw_input["form_data"]
        if "query_params" in raw_input:
            metadata["query_params"] = raw_input["query_params"]

        # 处理文件上传
        attachments = {}
        if "uploaded_files" in raw_input:
            attachments["files"] = raw_input["uploaded_files"]

        return StandardizedInput(
            instruction=instruction, context=context, metadata=metadata, attachments=attachments
        )

    def validate(self, standardized_input: StandardizedInput) -> bool:
        """验证Web输入"""
        return (
            bool(standardized_input.instruction.strip())
            and len(standardized_input.instruction) <= 50000  # Web输入可以更长
        )

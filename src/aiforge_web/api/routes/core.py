import json
import time
from fastapi import APIRouter, Request, Depends
from fastapi.responses import StreamingResponse
from typing import Dict, Any

from aiforge.core.managers.streaming_execution_manager import StreamingExecutionManager
from ..dependencies import get_forge_engine, get_forge_components

router = APIRouter(prefix="/api/v1/core", tags=["core"])


def convert_to_web_ui_types(result_data):
    """将基础 UI 类型转换为 Web 特定类型"""
    if isinstance(result_data, dict) and "display_items" in result_data:
        for item in result_data["display_items"]:
            if "type" in item:
                base_type = item["type"]
                if (
                    not base_type.startswith("web_")
                    and not base_type.startswith("mobile_")
                    and not base_type.startswith("terminal_")
                ):
                    item["type"] = f"web_{base_type}"
    return result_data


@router.post("/execute")
async def execute_instruction(request: Request, forge: Any = Depends(get_forge_engine)):
    """通用指令执行接口 - 同步版本"""
    data = await request.json()

    raw_input = {
        "instruction": data.get("instruction", ""),
        "method": request.method,
        "user_agent": request.headers.get("user-agent", ""),
        "ip_address": request.client.host,
        "request_id": data.get("request_id"),
    }

    context_data = {
        "user_id": data.get("user_id"),
        "session_id": data.get("session_id"),
        "task_type": data.get("task_type"),
        "device_info": {
            "browser": data.get("browser_info", {}),
            "viewport": data.get("viewport", {}),
        },
    }

    try:
        result = forge.run_with_input_adaptation(raw_input, "web", context_data)

        # 使用基础类型，让 Web 应用层进行类型转换
        ui_result = forge.adapt_result_for_ui(result, "card", "web")

        # 转换为 Web 特定类型
        ui_result = convert_to_web_ui_types(ui_result)

        return {
            "success": True,
            "result": ui_result,
            "metadata": {"source": "web", "processed_at": time.time()},
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "metadata": {"source": "web", "processed_at": time.time()},
        }


@router.post("/execute/stream")
async def execute_instruction_stream(
    request: Request, components: Dict[str, Any] = Depends(get_forge_components)
):
    """通用指令执行接口 - 流式版本"""
    data = await request.json()

    # 获取组件
    streaming_manager = StreamingExecutionManager(components)

    # 准备上下文数据
    context_data = {
        "user_id": data.get("user_id"),
        "session_id": data.get("session_id"),
        "task_type": data.get("task_type"),
        "device_info": {
            "browser": data.get("browser_info", {}),
            "viewport": data.get("viewport", {}),
        },
    }

    async def generate():
        try:
            async for chunk in streaming_manager.execute_with_streaming(
                data.get("instruction", ""), "web", context_data
            ):
                # 检查客户端是否断开连接
                if await request.is_disconnected():
                    streaming_manager._client_disconnected = True
                    break

                # 处理结果数据，转换 UI 类型
                if chunk.startswith("data: "):
                    try:
                        chunk_data = json.loads(chunk[6:])

                        # 如果是结果类型的消息，转换 UI 类型
                        if chunk_data.get("type") == "result" and "data" in chunk_data:
                            if (
                                isinstance(chunk_data["data"], dict)
                                and "result" in chunk_data["data"]
                            ):
                                chunk_data["data"]["result"] = convert_to_web_ui_types(
                                    chunk_data["data"]["result"]
                                )
                            else:
                                chunk_data["data"] = convert_to_web_ui_types(chunk_data["data"])

                            # 重新序列化
                            chunk = f"data: {json.dumps(chunk_data, ensure_ascii=False)}\n\n"
                    except (json.JSONDecodeError, KeyError):
                        # 如果解析失败，使用原始 chunk
                        pass

                yield chunk
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': f'服务器错误: {str(e)}'}, ensure_ascii=False)}\n\n"  # noqa: E501

    return StreamingResponse(
        generate(),
        media_type="text/plain",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/capabilities")
async def get_capabilities():
    """获取引擎能力信息"""
    return {
        "task_types": [
            "data_fetch",
            "data_analysis",
            "content_generation",
            "code_generation",
            "search",
            "direct_response",
        ],
        "ui_types": [
            "card",
            "table",
            "dashboard",
            "timeline",
            "progress",
            "editor",
            "map",
            "chart",
            "gallery",
            "calendar",
            "list",
            "text",
        ],
        "providers": ["openrouter", "deepseek", "ollama"],
        "features": {"streaming": True, "ui_adaptation": True, "multi_provider": True},
    }

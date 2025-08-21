import json
import time
from fastapi import APIRouter, Request, Depends
from fastapi.responses import StreamingResponse

from ..dependencies import get_forge_engine, get_session_id
from aiforge import AIForgeEngine
from ...core.session_manager import UserSessionManager
from ...core.config import get_default_engine_config
from aiforge import AIForgeStreamingExecutionManager


router = APIRouter(prefix="/api/v1/core", tags=["core"])


@router.post("/stop/{session_id}")
async def stop_session_execution(session_id: str):
    """停止指定会话的执行"""
    session_manager = UserSessionManager.get_instance()
    session_manager.initiate_session_shutdown(session_id)
    return {"success": True, "message": f"会话 {session_id} 停止信号已发送"}


@router.post("/stop")
async def stop_current_execution(request: Request):
    """停止当前请求会话的执行"""
    session_id = get_session_id(request)
    session_manager = UserSessionManager.get_instance()
    session_manager.initiate_session_shutdown(session_id)
    return {"success": True, "message": "当前会话停止信号已发送"}


@router.post("/execute")
async def execute_instruction(request: Request, forge: AIForgeEngine = Depends(get_forge_engine)):
    """通用指令执行接口"""
    data = await request.json()
    session_id = get_session_id(request)

    # 准备输入数据
    raw_input = {
        "instruction": data.get("instruction", ""),
        "method": "POST",
        "user_agent": request.headers.get("user-agent", "AIForge-Web"),
        "ip_address": request.client.host,
        "request_id": session_id,
    }

    # 准备上下文数据
    context_data = {
        "user_id": data.get("user_id"),
        "session_id": session_id,
        "task_type": data.get("task_type"),
        "device_info": {
            "browser": data.get("browser_info", {}),
            "viewport": data.get("viewport", {}),
        },
    }

    try:
        # 使用用户专属的引擎实例执行
        result = forge.run_with_input_adaptation(raw_input, "web", context_data)

        if result:
            ui_result = forge.adapt_result_for_ui(
                result,
                "editor" if result.task_type == "content_generation" else None,
                "web",
            )

            return {
                "success": True,
                "result": ui_result,
                "metadata": {
                    "source": "web",
                    "session_id": session_id,
                    "processed_at": time.time(),
                },
            }
        else:
            return {"success": False, "error": "执行失败：未获得结果"}

    except Exception as e:
        return {"success": False, "error": f"执行错误: {str(e)}"}


@router.post("/execute/stream")
async def execute_instruction_stream(request: Request):
    """流式执行接口"""
    data = await request.json()
    session_id = get_session_id(request)

    # 获取用户专属引擎
    session_manager = UserSessionManager.get_instance()
    default_engine_config = get_default_engine_config()
    forge = session_manager.get_or_create_engine(session_id, **default_engine_config)
    session_shutdown = session_manager.get_session_shutdown_manager(session_id)
    components = forge.component_manager.components
    components["shutdown_manager"] = session_shutdown

    # 使用会话隔离的流式管理器

    streaming_manager = AIForgeStreamingExecutionManager(components, forge)

    # 准备上下文数据
    context_data = {
        "user_id": data.get("user_id"),
        "session_id": session_id,
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
                # 检查会话级停止信号
                if session_shutdown and session_shutdown.is_shutting_down():
                    yield f"data: {json.dumps({'type': 'stopped', 'message': '执行已被停止'}, ensure_ascii=False)}\\n\\n"  # noqa 501
                    break

                if await request.is_disconnected():
                    streaming_manager._client_disconnected = True
                    session_manager.initiate_session_shutdown(session_id)
                    break
                yield chunk
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': f'服务器错误: {str(e)}'}, ensure_ascii=False)}\\n\\n"  # noqa 501

    return StreamingResponse(
        generate(),
        media_type="text/plain",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/session/cleanup/{session_id}")
async def cleanup_session(session_id: str):
    """清理指定会话"""
    UserSessionManager.get_instance().cleanup_session(session_id)
    return {"success": True, "message": f"会话 {session_id} 已清理"}


@router.get("/session/stats")
async def get_session_stats():
    """获取会话统计信息"""
    return {
        "active_sessions": UserSessionManager.get_instance().get_active_sessions_count(),
        "timestamp": time.time(),
    }


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

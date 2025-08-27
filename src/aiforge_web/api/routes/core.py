import json
import time
from fastapi import APIRouter, Request, Depends
from fastapi.responses import StreamingResponse

from aiforge import AIForgeStreamingExecutionManager

from ..dependencies import (
    get_session_id,
    get_session_manager,
    get_session_aware_engine,
)
from aiforge import AIForgeEngine


router = APIRouter(prefix="/api/v1/core", tags=["core"])


@router.get("/resources/stats")
async def get_resource_stats():
    """获取资源使用统计"""
    from ...main import resource_monitor

    if resource_monitor:
        return resource_monitor.get_resource_stats()
    return {"error": "资源监控器未启动"}


@router.post("/resources/cleanup")
async def trigger_manual_cleanup(session_manager=Depends(get_session_manager)):
    """手动触发资源清理"""
    from ...main import resource_monitor

    if resource_monitor:
        resource_monitor._trigger_aggressive_cleanup()
        return {"success": True, "message": "手动清理已触发"}
    return {"error": "资源监控器未启动"}


@router.get("/resources/monitor/status")
async def get_monitor_status():
    """获取监控器状态"""
    from ...main import resource_monitor

    if resource_monitor:
        return {
            "monitoring": resource_monitor.monitoring,
            "cleanup_callbacks": list(resource_monitor.cleanup_callbacks.keys()),
            "thresholds": {
                "memory": resource_monitor.memory_threshold,
                "session": resource_monitor.session_threshold,
                "cleanup_interval": resource_monitor.cleanup_interval,
            },
        }
    return {"error": "资源监控器未启动"}


@router.post("/stop/{session_id}")
async def stop_session_execution(session_id: str, session_manager=Depends(get_session_manager)):
    """停止指定会话的执行"""
    context = session_manager.get_session(session_id)
    if context and "shutdown_manager" in context.components:
        context.components["shutdown_manager"].shutdown()
    return {"success": True, "message": f"会话 {session_id} 停止信号已发送"}


@router.post("/stop")
async def stop_current_execution(request: Request, session_manager=Depends(get_session_manager)):
    """停止当前请求会话的执行"""
    session_id = get_session_id(request)
    context = session_manager.get_session(session_id)
    if context and "shutdown_manager" in context.components:
        context.components["shutdown_manager"].shutdown()
    return {"success": True, "message": "当前会话停止信号已发送"}


@router.post("/execute")
async def execute_instruction(
    request: Request, engine: AIForgeEngine = Depends(get_session_aware_engine)
):
    """通用指令执行接口"""
    data = await request.json()

    # 准备输入数据
    raw_input = {
        "instruction": data.get("instruction", ""),
        "method": "POST",
        "user_agent": request.headers.get("user-agent", "AIForge-Web"),
        "ip_address": request.client.host,
        "request_id": engine._session_context.session_id,
    }

    # 准备上下文数据
    context_data = {
        "user_id": engine._session_context.user_id,
        "session_id": engine._session_context.session_id,
        "task_type": data.get("task_type"),
        "device_info": {
            "browser": data.get("browser_info", {}),
            "viewport": data.get("viewport", {}),
        },
    }

    try:
        # 直接使用注入的会话感知引擎
        result = engine.run_with_input_adaptation(raw_input, "web", context_data)

        if result:
            ui_result = engine.adapt_result_for_ui(
                result,
                (
                    "editor"
                    if hasattr(result, "task_type") and result.task_type == "content_generation"
                    else None
                ),
                "web",
            )

            return {
                "success": True,
                "result": ui_result,
                "metadata": {
                    "source": "web",
                    "session_id": engine._session_context.session_id,
                    "processed_at": time.time(),
                },
            }
        else:
            return {"success": False, "error": "执行失败：未获得结果"}

    except Exception as e:
        return {"success": False, "error": f"执行错误: {str(e)}"}


@router.post("/execute/stream")
async def execute_instruction_stream(
    request: Request, engine: AIForgeEngine = Depends(get_session_aware_engine)
):
    """流式执行接口"""
    data = await request.json()

    # 获取会话上下文
    session_context = engine._session_context

    # 获取或创建会话级关闭管理器
    shutdown_manager = session_context.get_component("shutdown_manager")

    # 创建流式管理器
    streaming_manager = AIForgeStreamingExecutionManager(session_context.components, engine)

    # 准备上下文数据
    context_data = {
        "user_id": session_context.user_id,
        "session_id": session_context.session_id,
        "task_type": data.get("task_type"),
        "progress_level": data.get("progress_level", "detailed"),
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
                if shutdown_manager and shutdown_manager.is_shutting_down():
                    yield f"data: {json.dumps({'type': 'stopped', 'message': '执行已被停止'}, ensure_ascii=False)}\n\n"  # noqa 501
                    break

                if await request.is_disconnected():
                    streaming_manager._client_disconnected = True
                    if shutdown_manager:
                        shutdown_manager.shutdown()
                    break
                yield chunk
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': f'服务器错误: {str(e)}'}, ensure_ascii=False)}\n\n"  # noqa 501

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
async def cleanup_session(session_id: str, session_manager=Depends(get_session_manager)):
    """清理指定会话"""
    session_manager.cleanup_session(session_id)
    return {"success": True, "message": f"会话 {session_id} 已清理"}


@router.get("/session/stats")
async def get_session_stats(session_manager=Depends(get_session_manager)):
    """获取会话统计信息"""
    return {
        "active_sessions": session_manager.get_active_sessions_count(),
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

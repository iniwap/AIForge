from fastapi import APIRouter, Request, Depends
from ..dependencies import get_session_context
from ...core.session_context import SessionContext

router = APIRouter(prefix="/api/v1/config", tags=["config"])


@router.get("/session")
async def get_session_config(context: SessionContext = Depends(get_session_context)):
    """获取当前会话配置"""
    return {
        "session_id": context.session_id,
        "provider": context.config.provider,
        "locale": context.config.locale,
        "max_rounds": context.config.max_rounds,
        "max_tokens": context.config.max_tokens,
        "has_api_key": bool(context.config.api_key),
    }


@router.post("/session")
async def update_session_config(
    request: Request, context: SessionContext = Depends(get_session_context)
):
    """更新当前会话配置"""
    data = await request.json()
    context.update_config(**data)
    return {"success": True, "message": "Session config updated"}

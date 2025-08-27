from fastapi import APIRouter, Request, Depends
from ..dependencies import get_session_context
from ...core.session_context import SessionContext

router = APIRouter(prefix="/api/v1/config", tags=["config"])


@router.get("/session")
async def get_session_config(context: SessionContext = Depends(get_session_context)):
    """获取当前会话配置"""
    import os

    # 检查会话配置中的 API 密钥
    has_session_api_key = bool(context.config.api_key)

    # 检查环境变量中的 API 密钥
    env_api_key = os.environ.get("OPENROUTER_API_KEY") or os.environ.get("AIFORGE_API_KEY")
    has_env_api_key = bool(env_api_key)

    # 确定实际使用的提供商
    effective_provider = context.config.provider
    if not effective_provider and has_env_api_key:
        effective_provider = os.environ.get("AIFORGE_PROVIDER", "openrouter")

    return {
        "session_id": context.session_id,
        "provider": effective_provider,
        "locale": context.config.locale,
        "max_rounds": context.config.max_rounds,
        "max_tokens": context.config.max_tokens,
        "has_api_key": has_session_api_key or has_env_api_key,
        "api_key_source": (
            "session" if has_session_api_key else ("environment" if has_env_api_key else "none")
        ),
    }


@router.post("/session")
async def update_session_config(
    request: Request, context: SessionContext = Depends(get_session_context)
):
    """更新当前会话配置"""
    data = await request.json()
    context.update_config(**data)
    return {"success": True, "message": "Session config updated"}

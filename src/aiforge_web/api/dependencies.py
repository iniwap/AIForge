import uuid
from typing import Dict, Any
from fastapi import Request, Header
from aiforge import AIForgeEngine
from ..core.session_manager import UserSessionManager
from ..core.config import get_default_engine_config


def get_session_id(request: Request, x_session_id: str = Header(None)) -> str:
    """获取或生成会话ID"""
    # 优先使用请求头中的会话ID
    if x_session_id:
        return x_session_id

    # 从请求体中获取会话ID（如果是POST请求）
    if hasattr(request, "_json") and request._json:
        session_id = request._json.get("session_id")
        if session_id:
            return session_id

    # 生成新的会话ID
    return str(uuid.uuid4())


async def get_forge_engine(request: Request) -> AIForgeEngine:
    """获取用户专属的 AIForge 引擎实例"""
    # 获取会话ID
    session_id = get_session_id(request)

    # 从请求中获取用户特定配置（如果有）
    engine_config = get_default_engine_config().copy()

    # 如果是POST请求，尝试从请求体获取配置
    if request.method == "POST":
        try:
            body = await request.json()
            if "api_key" in body:
                engine_config["api_key"] = body["api_key"]
            if "provider" in body:
                engine_config["provider"] = body["provider"]
        except Exception:
            pass

    # 获取或创建用户专属引擎
    return UserSessionManager.get_instance().get_or_create_engine(session_id, **engine_config)


async def get_forge_components(request: Request) -> Dict[str, Any]:
    """获取用户专属的 AIForge 组件"""
    engine = await get_forge_engine(request)
    return engine.component_manager.components if engine else {}

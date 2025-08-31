import os
import uuid
from fastapi import Request, Header, Depends, HTTPException
from ..core.session_manager import SessionManager
from ..core.session_context import SessionContext
from aiforge import AIForgeEngine


def get_session_manager() -> SessionManager:
    """获取会话管理器实例"""
    return SessionManager.get_instance()


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


async def get_session_context(
    request: Request, session_manager: SessionManager = Depends(get_session_manager)
) -> SessionContext:
    """获取或创建会话上下文"""
    session_id = get_session_id(request)

    # 从请求中提取配置
    config_updates = {}
    if request.method == "POST":
        try:
            body = await request.json()
            config_updates = {
                "api_key": body.get("api_key"),
                "provider": body.get("provider"),
                "locale": body.get("language", "zh"),
                "max_rounds": body.get("max_rounds"),
                "max_tokens": body.get("max_tokens"),
            }
            config_updates = {k: v for k, v in config_updates.items() if v is not None}
        except Exception:
            pass

    # 获取或创建会话上下文
    context = session_manager.get_session(session_id)
    if context is None:
        context = session_manager.create_session(
            session_id=session_id,
            user_id=config_updates.get("user_id"),
            language=config_updates.get("locale", "zh"),
            **config_updates,
        )
    else:
        # 更新现有会话的配置
        context.update_config(**config_updates)

    return context


async def get_session_aware_engine(
    request: Request, context: SessionContext = Depends(get_session_context)
) -> AIForgeEngine:
    """获取会话感知的AIForge引擎"""

    # 从会话配置提取用户参数
    user_params = {}
    if context.config.api_key:
        user_params["api_key"] = context.config.api_key
    if context.config.provider:
        user_params["provider"] = context.config.provider
    if context.config.locale:
        user_params["locale"] = context.config.locale
    if context.config.max_rounds:
        user_params["max_rounds"] = context.config.max_rounds
    if context.config.max_tokens:
        user_params["max_tokens"] = context.config.max_tokens

    # 如果没有用户API key，尝试环境变量
    if not user_params.get("api_key"):
        env_api_key = os.environ.get("OPENROUTER_API_KEY") or os.environ.get("AIFORGE_API_KEY")
        if env_api_key:
            user_params["api_key"] = env_api_key
            user_params["provider"] = os.environ.get("AIFORGE_PROVIDER", "openrouter")
        else:
            # 对于配置相关的端点，允许无API密钥访问
            if request.url.path.startswith("/api/v1/config") or request.url.path == "/":
                # 创建一个临时引擎用于配置操作
                user_params["api_key"] = "temp_key_for_config"
            else:
                raise HTTPException(status_code=400, detail="API密钥未配置，请先配置API密钥")

    # 创建或获取引擎实例 - 让AIForgeEngine内部处理配置合并
    if "engine" not in context.components:
        engine = AIForgeEngine(**user_params)  # 直接传递用户参数
        engine._session_context = context
        context.set_component("engine", engine)

        if hasattr(engine, "component_manager") and engine.component_manager:
            # 只暴露部分接口
            web_allowed_components = [
                "i18n_manager",
                "progress_indicator",
                "shutdown_manager",
                "ui_adapter",
                "result_processor",
            ]

            for comp_name in web_allowed_components:
                component = engine.component_manager.components.get(comp_name)
                if component:
                    context.set_component(comp_name, component)

    return context.get_component("engine")

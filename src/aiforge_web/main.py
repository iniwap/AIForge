import os
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse

from .api.routes import core, metadata, config, health
from .api.middleware.cors import setup_cors
from .api.dependencies import set_forge_instance

# 引擎初始化逻辑保持不变
from aiforge import AIForgeEngine


def initialize_aiforge_engine():
    """智能初始化 AIForge 引擎，适配多种环境和配置方式"""
    # 保持原有的初始化逻辑
    is_docker = os.path.exists("/.dockerenv") or os.environ.get("AIFORGE_DOCKER_MODE") == "true"

    if is_docker:
        docker_config_path = "/app/config/aiforge.toml"
        if os.path.exists(docker_config_path):
            return AIForgeEngine(config_file=docker_config_path)

    local_config_paths = ["aiforge.toml", "config/aiforge.toml", "../aiforge.toml"]
    for config_path in local_config_paths:
        if os.path.exists(config_path):
            return AIForgeEngine(config_file=config_path)

    api_key = (
        os.environ.get("OPENROUTER_API_KEY")
        or os.environ.get("DEEPSEEK_API_KEY")
        or os.environ.get("AIFORGE_API_KEY")
    )

    if api_key:
        if api_key.startswith("sk-or-"):
            return AIForgeEngine(api_key=api_key, provider="openrouter")
        elif "deepseek" in api_key.lower():
            return AIForgeEngine(api_key=api_key, provider="deepseek")
        else:
            return AIForgeEngine(api_key=api_key, provider="openrouter")

    aiforge_service_key = os.environ.get("AIFORGE_SERVICE_KEY")
    if aiforge_service_key:
        return initialize_with_service_key(aiforge_service_key)

    raise ValueError(
        "AIForge 需要配置才能运行。请选择以下方式之一：\n"
        "1. 设置环境变量：OPENROUTER_API_KEY 或 DEEPSEEK_API_KEY\n"
        "2. 创建配置文件：aiforge.toml\n"
        "3. 使用 AIForge 服务密钥：AIFORGE_SERVICE_KEY（即将推出）"
    )


def initialize_with_service_key(service_key: str):
    """使用 AIForge 服务密钥初始化（未来功能）"""
    return AIForgeEngine(
        config={
            "service_mode": True,
            "service_key": service_key,
            "service_endpoint": "https://api.aiforge.dev/v1",
        }
    )


# 初始化引擎
forge = None
forge_components = None

try:
    forge = initialize_aiforge_engine()
    forge_components = forge.component_manager.components if forge else None

    # 在引擎初始化成功后
    if forge:
        set_forge_instance(forge)  # 设置到依赖注入系统

    print("✅ AIForge 引擎初始化成功")
except Exception as e:
    print(f"❌ AIForge 引擎初始化失败: {e}")
    print("⚠️  Web 服务将以受限模式运行")

# 创建 FastAPI 应用
app = FastAPI(
    title="AIForge API Server", version="1.0.0", description="智能意图自适应执行引擎 API 服务"
)

# 设置 CORS
setup_cors(app)

# 注册 API 路由
app.include_router(core.router)
app.include_router(metadata.router)
app.include_router(config.router)
app.include_router(health.router)

# Web 前端路由（可选）
app.mount("/static", StaticFiles(directory="src/aiforge_web/web/static"), name="static")
templates = Jinja2Templates(directory="src/aiforge_web/web/templates")


@app.get("/", response_class=HTMLResponse)
async def web_interface(request: Request):
    """Web 界面入口（可选）"""
    return templates.TemplateResponse("index.html", {"request": request})

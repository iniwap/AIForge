import threading
import time
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse

from .api.routes import core, metadata, config, health
from .api.middleware.cors import setup_cors
from .core.session_manager import UserSessionManager


# 创建 FastAPI 应用
app = FastAPI(
    title="AIForge API Server",
    version="1.0.0",
    description="智能意图自适应执行引擎",
)

# 设置 CORS
setup_cors(app)

# 注册 API 路由
app.include_router(core.router)
app.include_router(metadata.router)
app.include_router(config.router)
app.include_router(health.router)

# Web 前端路由
app.mount("/static", StaticFiles(directory="src/aiforge_web/web/static"), name="static")
templates = Jinja2Templates(directory="src/aiforge_web/web/templates")


@app.get("/", response_class=HTMLResponse)
async def web_interface(request: Request):
    """Web 界面入口"""
    return templates.TemplateResponse("index.html", {"request": request})


# 定期清理过期会话
def cleanup_expired_sessions():
    """后台任务：定期清理过期会话"""
    while True:
        try:
            UserSessionManager.get_instance().cleanup_expired_sessions()
            time.sleep(3600)  # 每小时清理一次
        except Exception as e:
            print(f"会话清理错误: {e}")


# 启动后台清理任务
cleanup_thread = threading.Thread(target=cleanup_expired_sessions, daemon=True)
cleanup_thread.start()

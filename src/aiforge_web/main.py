import time
import atexit
import importlib.resources

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse

from .api.routers import core, metadata, config, health
from .api.middleware.cors import setup_cors
from .api.dependencies import get_session_manager
from .core.resource_monitor import ResourceMonitor

# 全局资源监控器和会话管理器
resource_monitor = None
session_manager = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    global resource_monitor, session_manager

    # 启动事件
    # 初始化会话管理器
    session_manager = get_session_manager()

    # 初始化资源监控器
    resource_monitor = ResourceMonitor(session_manager)

    # 注册自定义清理回调
    resource_monitor.register_cleanup_callback(
        "garbage_collection", lambda: __import__("gc").collect()
    )

    # 启动资源监控
    resource_monitor.start_monitoring()

    # 注册应用退出时的清理函数
    atexit.register(cleanup_on_exit)

    print("🚀 AIForge Web 服务器启动完成")

    yield  # 应用运行期间

    # 关闭事件
    print("🔄 开始关闭服务...")

    # 停止资源监控器
    if resource_monitor:
        resource_monitor.stop_monitoring()
        print("✅ 资源监控器已停止")

    # 优雅关闭所有会话
    if session_manager:
        try:
            session_manager.shutdown_all_sessions()
            print("✅ 所有会话已关闭")
        except Exception as e:
            print(f"⚠️ 会话关闭时出现错误: {e}")


# 创建 FastAPI 应用，使用 lifespan 参数
app = FastAPI(
    title="AIForge API Server",
    version="1.0.0",
    description="智能意图自适应执行引擎",
    lifespan=lifespan,
)

# 设置 CORS
setup_cors(app)

# 注册 API 路由
app.include_router(core.router)
app.include_router(metadata.router)
app.include_router(config.router)
app.include_router(health.router)

# Web 前端路由
# 获取包资源路径
try:
    with importlib.resources.path("aiforge_web.web", "static") as static_path:
        app.mount("/static", StaticFiles(directory=str(static_path)), name="static")
    with importlib.resources.path("aiforge_web.web", "templates") as templates_path:
        templates = Jinja2Templates(directory=str(templates_path))
except ImportError:
    # 回退到源码模式路径
    app.mount("/static", StaticFiles(directory="src/aiforge_web/web/static"), name="static")
    templates = Jinja2Templates(directory="src/aiforge_web/web/templates")


@app.get("/", response_class=HTMLResponse)
async def web_interface(request: Request):
    """Web 界面入口"""
    return templates.TemplateResponse("index.html", {"request": request})


def cleanup_on_exit():
    """进程退出时的清理函数"""
    global resource_monitor, session_manager

    try:
        if resource_monitor and resource_monitor.monitoring:
            resource_monitor.stop_monitoring()
    except (KeyboardInterrupt, SystemExit):
        # 忽略键盘中断，直接退出
        pass
    except Exception as e:
        print(f"退出清理错误: {e}")

    try:
        if session_manager:
            session_manager.shutdown_all_sessions()
    except (KeyboardInterrupt, SystemExit):
        # 忽略键盘中断，直接退出
        pass
    except Exception as e:
        print(f"会话清理错误: {e}")


# 健康检查端点
@app.get("/health")
async def health_check():
    """应用健康检查"""
    global resource_monitor, session_manager

    health_status = {"status": "healthy", "timestamp": time.time(), "components": {}}

    # 检查会话管理器状态
    if session_manager:
        try:
            active_sessions = len(session_manager._sessions)
            health_status["components"]["session_manager"] = {
                "status": "healthy",
                "active_sessions": active_sessions,
                "max_sessions": session_manager._max_sessions,
            }
        except Exception as e:
            health_status["components"]["session_manager"] = {"status": "error", "error": str(e)}
    else:
        health_status["components"]["session_manager"] = {"status": "not_initialized"}

    # 检查资源监控器状态
    if resource_monitor:
        try:
            health_status["components"]["resource_monitor"] = {
                "status": "healthy" if resource_monitor.monitoring else "stopped",
                "monitoring": resource_monitor.monitoring,
                "cleanup_callbacks": len(resource_monitor.cleanup_callbacks),
            }
        except Exception as e:
            health_status["components"]["resource_monitor"] = {"status": "error", "error": str(e)}
    else:
        health_status["components"]["resource_monitor"] = {"status": "not_initialized"}

    # 如果任何组件有问题，整体状态为 degraded
    component_statuses = [comp.get("status") for comp in health_status["components"].values()]
    if "error" in component_statuses:
        health_status["status"] = "unhealthy"
    elif "stopped" in component_statuses or "not_initialized" in component_statuses:
        health_status["status"] = "degraded"

    return health_status


# 系统信息端点
@app.get("/system/info")
async def system_info():
    """获取系统信息"""
    global resource_monitor

    info = {
        "application": {
            "name": "AIForge API Server",
            "version": "1.0.0",
            "description": "智能意图自适应执行引擎",
        },
        "runtime": {
            "python_version": __import__("sys").version,
            "platform": __import__("platform").platform(),
        },
    }

    # 添加资源统计信息
    if resource_monitor:
        try:
            resource_stats = resource_monitor.get_resource_stats()
            info["resources"] = resource_stats
        except Exception as e:
            info["resources"] = {"error": str(e)}

    return info


# 手动触发清理端点
@app.post("/system/cleanup")
async def manual_cleanup():
    """手动触发系统清理"""
    global resource_monitor, session_manager

    cleanup_results = {"timestamp": time.time(), "results": {}}

    # 触发会话清理
    if session_manager:
        try:
            cleaned_sessions = session_manager.cleanup_expired_sessions()
            cleanup_results["results"]["expired_sessions"] = {
                "status": "success",
                "cleaned_count": cleaned_sessions,
            }
        except Exception as e:
            cleanup_results["results"]["expired_sessions"] = {"status": "error", "error": str(e)}

    # 触发资源监控器清理
    if resource_monitor:
        try:
            resource_monitor._trigger_aggressive_cleanup()
            cleanup_results["results"]["resource_cleanup"] = {
                "status": "success",
                "message": "激进清理已触发",
            }
        except Exception as e:
            cleanup_results["results"]["resource_cleanup"] = {"status": "error", "error": str(e)}

    # 手动垃圾回收
    try:
        import gc

        collected = gc.collect()
        cleanup_results["results"]["garbage_collection"] = {
            "status": "success",
            "collected_objects": collected,
        }
    except Exception as e:
        cleanup_results["results"]["garbage_collection"] = {"status": "error", "error": str(e)}

    return cleanup_results

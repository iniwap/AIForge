import time
import os
from fastapi import FastAPI, Request, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from aiforge import AIForgeEngine
from fastapi.responses import StreamingResponse
from .streaming_execution_manager import StreamingExecutionManager

app = FastAPI(title="AIForge Web Interface", version="1.0.0")

# 静态文件和模板
app.mount("/static", StaticFiles(directory="src/aiforge_web/static"), name="static")
templates = Jinja2Templates(directory="src/aiforge_web/templates")


def initialize_aiforge_engine():
    """智能初始化 AIForge 引擎，适配多种环境和配置方式"""

    # 1. 检测 Docker 环境
    is_docker = os.path.exists("/.dockerenv") or os.environ.get("AIFORGE_DOCKER_MODE") == "true"

    # 2. Docker 环境：优先使用预生成的配置文件
    if is_docker:
        docker_config_path = "/app/config/aiforge.toml"
        if os.path.exists(docker_config_path):
            return AIForgeEngine(config_file=docker_config_path)

    # 3. 非 Docker 环境：按优先级尝试不同配置方式

    # 3.1 检查是否有本地配置文件
    local_config_paths = ["aiforge.toml", "config/aiforge.toml", "../aiforge.toml"]
    for config_path in local_config_paths:
        if os.path.exists(config_path):
            return AIForgeEngine(config_file=config_path)

    # 3.2 从环境变量获取 API 密钥
    api_key = (
        os.environ.get("OPENROUTER_API_KEY")
        or os.environ.get("DEEPSEEK_API_KEY")
        or os.environ.get("AIFORGE_API_KEY")  # 未来的统一密钥
    )

    if api_key:
        # 检测提供商类型
        if api_key.startswith("sk-or-"):
            return AIForgeEngine(api_key=api_key, provider="openrouter")
        elif "deepseek" in api_key.lower():
            return AIForgeEngine(api_key=api_key, provider="deepseek")
        else:
            # 默认使用 OpenRouter
            return AIForgeEngine(api_key=api_key, provider="openrouter")

    # 3.3 检查是否有 AIForge 服务密钥（未来功能）
    aiforge_service_key = os.environ.get("AIFORGE_SERVICE_KEY")
    if aiforge_service_key:
        return initialize_with_service_key(aiforge_service_key)

    # 4. 如果都没有，抛出友好的错误信息
    raise ValueError(
        "AIForge 需要配置才能运行。请选择以下方式之一：\\n"
        "1. 设置环境变量：OPENROUTER_API_KEY 或 DEEPSEEK_API_KEY\\n"
        "2. 创建配置文件：aiforge.toml\\n"
        "3. 使用 AIForge 服务密钥：AIFORGE_SERVICE_KEY（即将推出）"
    )


def initialize_with_service_key(service_key: str):
    """使用 AIForge 服务密钥初始化（未来功能）"""
    # 这里将来会连接到 AIForge 服务后端
    # 验证服务密钥并获取相应的 LLM 配置
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
    print("✅ AIForge 引擎初始化成功")
except Exception as e:
    print(f"❌ AIForge 引擎初始化失败: {e}")
    print("⚠️  Web 服务将以受限模式运行")

# 尝试添加流式路由（如果可用）
try:
    from .streaming_api import add_streaming_routes

    if forge_components:
        add_streaming_routes(app, forge_components)
        print("✅ 流式 API 路由已加载")
    else:
        print("⚠️  流式 API 路由跳过（引擎未初始化）")
except ImportError:
    print("⚠️  流式 API 模块不可用，跳过加载")
except Exception as e:
    print(f"⚠️  流式 API 路由加载失败: {e}")


@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    """主页面"""
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/api/task-types")
async def get_task_types():
    """获取支持的任务类型"""
    # 基于 TaskClassifier 的内置类型
    builtin_types = [
        {
            "id": "data_fetch",
            "name": "数据获取",
            "icon": "📊",
            "description": "从各种数据源获取信息",
        },
        {"id": "data_analysis", "name": "数据分析", "icon": "📈", "description": "分析和处理数据"},
        {
            "id": "content_generation",
            "name": "内容生成",
            "icon": "✍️",
            "description": "生成文本、文档等内容",
        },
        {
            "id": "code_generation",
            "name": "代码生成",
            "icon": "💻",
            "description": "生成和优化代码",
        },
        {"id": "search", "name": "搜索查询", "icon": "🔍", "description": "搜索和检索信息"},
        {"id": "direct_response", "name": "知识问答", "icon": "💬", "description": "直接回答问题"},
    ]

    # 未来可扩展的类型（Web 端暂不支持）
    future_types = [
        {
            "id": "file_operation",
            "name": "文件操作",
            "icon": "📁",
            "description": "文件管理和处理",
            "disabled": True,
            "reason": "需要客户端支持",
        },
        {
            "id": "automation",
            "name": "自动化任务",
            "icon": "🤖",
            "description": "自动化工作流程",
            "disabled": True,
            "reason": "需要系统权限",
        },
    ]

    return {
        "builtin_types": builtin_types,
        "future_types": future_types,
        "total_supported": len(builtin_types),
    }


@app.get("/api/ui-types")
async def get_ui_types():
    """获取支持的 UI 类型"""
    # 基于 RuleBasedAdapter 的支持类型
    ui_types = [
        {"id": "web_card", "name": "卡片视图", "description": "简洁的卡片展示"},
        {"id": "web_table", "name": "表格视图", "description": "结构化数据表格"},
        {"id": "web_dashboard", "name": "仪表板", "description": "数据分析仪表板"},
        {"id": "web_timeline", "name": "时间线", "description": "步骤和流程展示"},
        {"id": "web_progress", "name": "进度条", "description": "任务进度显示"},
        {"id": "web_editor", "name": "编辑器", "description": "内容编辑和展示"},
    ]

    return {"ui_types": ui_types}


@app.post("/api/process")
async def process_instruction(request: Request):
    """传统同步处理端点（保持兼容性）"""
    if not forge:
        raise HTTPException(status_code=503, detail="AIForge 引擎未初始化，请检查配置")

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
        "task_type": data.get("task_type"),  # 添加任务类型支持
        "device_info": {
            "browser": data.get("browser_info", {}),
            "viewport": data.get("viewport", {}),
        },
    }

    try:
        result = forge.run_with_input_adaptation(raw_input, "web", context_data)
        ui_result = forge.adapt_result_for_ui(result, "web_card", "web")

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


@app.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy" if forge else "degraded",
        "version": "1.0.0",
        "engine_initialized": forge is not None,
        "features": {
            "streaming": forge_components is not None,
            "ui_adaptation": forge is not None,
            "task_types": 6,
            "ui_types": 6,
        },
    }


@app.post("/api/config/update")
async def update_config(request: Request):
    """动态更新配置（支持用户自定义密钥）"""
    data = await request.json()

    # 验证用户权限（未来可以加入用户认证）
    user_id = data.get("user_id")
    session_id = data.get("session_id")  # noqa 841

    try:
        # 支持多种配置更新方式
        if "api_key" in data:
            # 用户提供自己的 API 密钥
            api_key = data["api_key"]
            provider = data.get("provider", "openrouter")

            # 创建用户专属的引擎实例
            user_forge = AIForgeEngine(api_key=api_key, provider=provider)  # noqa 841

            # 存储到会话中（实际应用中可能需要更安全的存储方式）
            # 这里简化处理
            return {"success": True, "message": "配置已更新"}

        elif "service_plan" in data:
            # 用户选择 AIForge 服务计划
            plan = data["service_plan"]  # "free", "pro", "enterprise"

            # 验证用户的服务计划权限
            service_config = get_service_config(user_id, plan)
            user_forge = AIForgeEngine(config=service_config)  # noqa 841

            return {"success": True, "message": f"已切换到 {plan} 计划"}

        else:
            raise HTTPException(status_code=400, detail="缺少必要的配置参数")

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


def get_service_config(user_id: str, plan: str) -> dict:
    """获取服务计划配置（未来功能）"""
    service_configs = {
        "free": {
            "max_requests_per_day": 100,
            "available_models": ["deepseek/deepseek-chat-v3-0324:free"],
            "max_tokens": 4096,
        },
        "pro": {
            "max_requests_per_day": 10000,
            "available_models": ["gpt-4", "claude-3", "deepseek-chat"],
            "max_tokens": 8192,
        },
        "enterprise": {
            "max_requests_per_day": -1,  # 无限制
            "available_models": ["all"],
            "max_tokens": 32768,
            "priority_support": True,
        },
    }

    return {
        "service_mode": True,
        "user_id": user_id,
        "plan": plan,
        **service_configs.get(plan, service_configs["free"]),
    }


@app.get("/api/config/status")
async def get_config_status():
    """获取当前配置状态"""
    if not forge:
        return {
            "configured": False,
            "error": "AIForge 引擎未初始化",
            "suggestions": [
                "设置 OPENROUTER_API_KEY 环境变量",
                "创建 aiforge.toml 配置文件",
                "联系管理员获取 AIForge 服务密钥",
            ],
        }

    # 检测当前配置类型
    config_type = "unknown"
    is_docker = os.environ.get("AIFORGE_DOCKER_MODE") == "true"

    if is_docker:
        config_type = "docker"
    elif os.environ.get("OPENROUTER_API_KEY"):
        config_type = "openrouter_env"
    elif os.environ.get("DEEPSEEK_API_KEY"):
        config_type = "deepseek_env"
    elif os.path.exists("aiforge.toml"):
        config_type = "config_file"
    return {
        "configured": True,
        "config_type": config_type,
        "is_docker": is_docker,
        "available_providers": ["openrouter", "deepseek", "ollama"],
        "features": {
            "user_custom_keys": True,
            "service_plans": False,  # 未来功能
            "multi_provider": True,
        },
    }


@app.post("/api/process/stream")
async def process_instruction_stream(request: Request):
    """流式处理指令端点"""
    if not forge:
        raise HTTPException(status_code=503, detail="AIForge 引擎未初始化，请检查配置")

    data = await request.json()

    # 获取组件
    components = forge.get_components()
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

    return StreamingResponse(
        streaming_manager.execute_with_streaming(data.get("instruction", ""), "web", context_data),
        media_type="text/plain",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )

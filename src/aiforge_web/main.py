import time
from fastapi import FastAPI, Request
from aiforge import AIForgeEngine

app = FastAPI()
forge = AIForgeEngine()


@app.get("/")
def read_root():
    return {"message": "欢迎使用 AIForge Web 界面！"}


def start_web():
    import uvicorn

    uvicorn.run("aiforge_web.main:app", host="127.0.0.1", port=8000, reload=True)


@app.post("/api/extensions/register")
def register_extension(extension_config: dict):
    """注册扩展组件的 API 端点"""
    # 调用 AIForgeEngine 的扩展注册方法
    pass


@app.get("/api/extensions/list")
def list_extensions():
    """列出已注册的扩展"""
    pass


@app.post("/api/process")
async def process_instruction(request: Request):
    data = await request.json()

    # 准备Web输入
    raw_input = {
        "instruction": data.get("instruction", ""),
        "method": request.method,
        "user_agent": request.headers.get("user-agent", ""),
        "ip_address": request.client.host,
        "request_id": data.get("request_id"),
    }

    # 准备Web上下文
    context_data = {
        "user_id": data.get("user_id"),
        "session_id": data.get("session_id"),
        "device_info": {
            "browser": data.get("browser_info", {}),
            "viewport": data.get("viewport", {}),
        },
    }

    # 使用输入适配运行
    result = forge.run_with_input_adaptation(raw_input, "web", context_data)

    # 适配输出结果
    ui_result = forge.adapt_result_for_ui(result, "web_card", "web")

    return {
        "success": True,
        "result": ui_result,
        "metadata": {"source": "web", "processed_at": time.time()},
    }

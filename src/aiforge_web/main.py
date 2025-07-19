from fastapi import FastAPI

app = FastAPI()


@app.get("/")
def read_root():
    return {"message": "欢迎使用 AIForge Web 界面！"}


def start_web():
    import uvicorn

    uvicorn.run("aiforge_web.main:app", host="127.0.0.1", port=8000, reload=True)


@app.post("/api/extensions/register")
def register_extension(extension_config: dict):
    """注册扩展组件的 API 端点"""
    # 调用 AIForgeCore 的扩展注册方法
    pass


@app.get("/api/extensions/list")
def list_extensions():
    """列出已注册的扩展"""
    pass

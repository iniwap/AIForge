from fastapi import FastAPI

app = FastAPI()


@app.get("/")
def read_root():
    return {"message": "欢迎使用 AIForge Web 界面！"}


def start_web():
    import uvicorn
    uvicorn.run("aiforge_web.main:app", host="127.0.0.1", port=8000, reload=True)

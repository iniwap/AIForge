import typer

app = typer.Typer()


@app.command()
def gui():
    """启动本地 GUI 界面"""
    try:
        from aiforge_gui.app import run_gui
        run_gui()
    except ImportError:
        print("请安装 GUI 所需依赖：pip install aiforge[gui]")


@app.command()
def web():
    """启动 Web 服务"""
    try:
        from aiforge_web.main import start_web
        start_web()
    except ImportError:
        print("请安装 Web 所需依赖：pip install aiforge[web]")


if __name__ == "__main__":
    app()

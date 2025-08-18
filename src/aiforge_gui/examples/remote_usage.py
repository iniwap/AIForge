# 远程使用示例
# !/usr/bin/env python3
"""远程使用示例"""

from aiforge_gui import AIForgeGUIApp


def main():
    """远程模式使用示例"""
    # 配置远程连接
    config = {"remote_url": "http://localhost:8000", "theme": "light", "debug": False}

    # 创建并启动应用
    app = AIForgeGUIApp(config)
    app.run()


if __name__ == "__main__":
    main()

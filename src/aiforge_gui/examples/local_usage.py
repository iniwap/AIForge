# 本地使用示例
# !/usr/bin/env python3
"""本地使用示例"""

import os
from aiforge_gui import AIForgeGUIApp


def main():
    """本地模式使用示例"""
    # 配置本地引擎
    config = {
        "api_key": os.environ.get("OPENROUTER_API_KEY"),
        "provider": "openrouter",
        "theme": "dark",
        "debug": True,
    }

    # 创建并启动应用
    app = AIForgeGUIApp(config)
    app.run()


if __name__ == "__main__":
    main()

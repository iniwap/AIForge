#!/usr/bin/env python3
"""AIForge CLI 主入口点"""

import sys
import os
import argparse
from typing import Optional


def main(args: Optional[list] = None) -> int:
    """CLI 主函数"""
    if args is None:
        args = sys.argv[1:]

    parser = argparse.ArgumentParser(
        description="AIForge - 智能意图自适应执行引擎",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument("instruction", nargs="?", help="要执行的自然语言指令")
    parser.add_argument("--provider", help="指定 LLM 提供商")
    parser.add_argument("--config", help="配置文件路径")
    parser.add_argument("--api-key", help="API 密钥")

    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    # Web 服务命令
    web_parser = subparsers.add_parser("web", help="启动 Web 服务")
    web_parser.add_argument("--host", default="0.0.0.0", help="服务器地址")
    web_parser.add_argument("--port", type=int, default=8000, help="服务器端口")
    web_parser.add_argument("--reload", action="store_true", help="启用热重载")
    web_parser.add_argument("--debug", action="store_true", help="启用调试模式")
    web_parser.add_argument("--provider", help="指定 LLM 提供商")
    web_parser.add_argument("--api-key", help="API 密钥")

    # CLI 命令
    cli_parser = subparsers.add_parser("cli", help="CLI 模式")
    cli_parser.add_argument("instruction", help="要执行的指令")
    cli_parser.add_argument("--provider", help="指定 LLM 提供商")
    cli_parser.add_argument("--config", help="配置文件路径")
    cli_parser.add_argument("--api-key", help="API 密钥")

    # GUI 命令
    gui_parser = subparsers.add_parser("gui", help="启动 GUI 应用")
    gui_parser.add_argument("--theme", default="dark", choices=["dark", "light"], help="界面主题")
    gui_parser.add_argument("--remote-url", help="远程服务器地址")
    gui_parser.add_argument("--config", help="配置文件路径")
    gui_parser.add_argument("--api-key", help="API 密钥")
    gui_parser.add_argument("--provider", default="openrouter", help="LLM 提供商")
    gui_parser.add_argument("--debug", action="store_true", help="启用调试模式")
    gui_parser.add_argument("--width", type=int, default=1200, help="窗口宽度")
    gui_parser.add_argument("--height", type=int, default=800, help="窗口高度")

    parsed_args = parser.parse_args(args)

    if parsed_args.command == "web":
        return start_web_server(
            parsed_args.host,
            parsed_args.port,
            getattr(parsed_args, "reload", False),
            getattr(parsed_args, "debug", False),
            getattr(parsed_args, "provider", None),
            getattr(parsed_args, "api_key", None),
        )
    elif parsed_args.command == "gui":
        return start_gui_app(parsed_args)
    elif parsed_args.command == "cli" or parsed_args.instruction:
        instruction = parsed_args.instruction or getattr(parsed_args, "instruction", None)
        if instruction:
            return execute_instruction(instruction, parsed_args)
        else:
            parser.print_help()
            return 1
    else:
        parser.print_help()
        return 0


def start_web_server(
    host: str = "0.0.0.0",
    port: int = 8000,
    reload: bool = False,
    debug: bool = False,
    provider: str = None,
    api_key: str = None,
) -> int:
    """启动 Web 服务器"""

    # 可选设置环境变量（不强制要求）
    if api_key:
        if not provider:
            os.environ["OPENROUTER_API_KEY"] = api_key
            os.environ["AIFORGE_PROVIDER"] = "openrouter"
        else:
            os.environ["AIFORGE_API_KEY"] = api_key
            os.environ["AIFORGE_PROVIDER"] = provider

    try:
        import uvicorn

        print("🚀 启动 AIForge Web 服务器")
        if host == "0.0.0.0":
            print(f"📡 本地访问: http://127.0.0.1:{port}")
            print(f"🌐 网络访问: http://{host}:{port}")
        else:
            print(f"🏠 访问地址: http://{host}:{port}")

        # 如果没有 API 密钥，显示提示信息
        if (
            not api_key
            and not os.environ.get("OPENROUTER_API_KEY")
            and not os.environ.get("AIFORGE_API_KEY")
        ):
            print("⚠️ ⚠️ ⚠️  未检测到 API 密钥，请在 Web 界面中配置")

        if reload:
            print("🔄 热重载模式已启用")
        if debug:
            print("🐛 调试模式已启用")

        # 启动服务器（保持现有逻辑）
        if reload:
            uvicorn.run(
                "aiforge_web.main:app",
                host=host,
                port=port,
                reload=True,
                reload_dirs=["src/aiforge", "src/aiforge_web"],
                log_level="debug" if debug else "info",
            )
        else:
            from aiforge_web.main import app

            uvicorn.run(app, host=host, port=port, log_level="debug" if debug else "info")
        return 0
    except ImportError:
        print("❌ Web 服务需要安装 fastapi 和 uvicorn")
        return 1
    except Exception as e:
        print(f"❌ Web 服务启动失败: {e}")
        return 1


def start_gui_app(args) -> int:
    """启动 GUI 应用"""
    try:
        # 构建完整配置
        config = {
            "theme": getattr(args, "theme", "dark"),
            "window_width": getattr(args, "width", 1200),
            "window_height": getattr(args, "height", 800),
            "debug": getattr(args, "debug", False),
            "enable_tray": True,
        }

        # API配置（可选）
        api_key = None
        provider = None
        if hasattr(args, "api_key") and args.api_key:
            config["api_key"] = args.api_key
            api_key = args.api_key
        if hasattr(args, "provider") and args.provider:
            config["provider"] = args.provider
            provider = args.provider
        if hasattr(args, "config") and args.config:
            config["config_file"] = args.config

        # 可选设置环境变量（不强制要求）
        if api_key:
            if not provider:
                os.environ["OPENROUTER_API_KEY"] = api_key
                os.environ["AIFORGE_PROVIDER"] = "openrouter"
            else:
                os.environ["AIFORGE_API_KEY"] = api_key
                os.environ["AIFORGE_PROVIDER"] = provider

        # 远程模式配置
        if hasattr(args, "remote_url") and args.remote_url:
            config["remote_url"] = args.remote_url

        from aiforge_gui import AIForgeGUIApp

        app = AIForgeGUIApp(config)
        app.run()
        return 0

    except ImportError as e:
        print("❌ GUI 服务需要安装相关依赖")
        print("   请运行: pip install aiforge-engine[gui]")
        print(f"   详细错误: {e}")
        return 1
    except Exception as e:
        print(f"❌ GUI 应用启动失败: {e}")
        return 1


def execute_instruction(instruction: str, args) -> int:
    """执行指令"""
    try:
        from aiforge import AIForgeEngine

        # 初始化引擎
        engine_kwargs = {}
        if args.api_key:
            engine_kwargs["api_key"] = args.api_key
        if args.provider:
            engine_kwargs["provider"] = args.provider
        if args.config:
            engine_kwargs["config_file"] = args.config

        engine = AIForgeEngine(**engine_kwargs)

        # 执行指令
        print(f"🤖 执行指令: {instruction}")
        result = engine(instruction)
        print(result)
        return 0

    except Exception as e:
        print(f"❌ 执行失败: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())

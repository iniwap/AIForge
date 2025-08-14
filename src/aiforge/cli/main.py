#!/usr/bin/env python3
"""AIForge CLI 主入口点"""

import sys
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

    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    # Web 服务命令 - 添加开发模式参数支持
    web_parser = subparsers.add_parser("web", help="启动 Web 服务")
    web_parser.add_argument("--host", default="0.0.0.0", help="服务器地址")
    web_parser.add_argument("--port", type=int, default=8000, help="服务器端口")
    web_parser.add_argument("--reload", action="store_true", help="启用热重载")
    web_parser.add_argument("--debug", action="store_true", help="启用调试模式")

    # CLI 命令
    cli_parser = subparsers.add_parser("cli", help="CLI 模式")
    cli_parser.add_argument("instruction", help="要执行的指令")

    parsed_args = parser.parse_args(args)

    if parsed_args.command == "web":
        return start_web_server(
            parsed_args.host,
            parsed_args.port,
            getattr(parsed_args, "reload", False),
            getattr(parsed_args, "debug", False),
        )
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
    host: str = "0.0.0.0", port: int = 8000, reload: bool = False, debug: bool = False
) -> int:
    """启动 Web 服务器"""
    try:
        import uvicorn

        print(f"🚀 启动 AIForge Web 服务器 http://{host}:{port}")
        if reload:
            print("🔄 热重载模式已启用")
        if debug:
            print("🐛 调试模式已启用")

        # 使用模块字符串而不是 app 对象以支持热重载
        if reload:
            uvicorn.run(
                "aiforge_web.main:app",  # 使用字符串路径
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


def execute_instruction(instruction: str, args) -> int:
    """执行指令"""
    try:
        from aiforge import AIForgeEngine

        # 初始化引擎
        engine_kwargs = {}
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

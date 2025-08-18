# GUI 启动命令
import argparse
import sys
from typing import Dict, Any
from ..main import AIForgeGUIApp


def add_gui_commands(subparsers):
    """添加 GUI 相关命令到 CLI"""
    gui_parser = subparsers.add_parser("gui", help="启动 GUI 界面")
    gui_parser.add_argument("--theme", default="dark", choices=["dark", "light"], help="界面主题")
    gui_parser.add_argument("--remote", help="远程服务器地址 (如: http://localhost:8000)")
    gui_parser.add_argument("--config", help="配置文件路径")
    gui_parser.add_argument("--api-key", help="API 密钥")
    gui_parser.add_argument("--provider", default="openrouter", help="LLM 提供商")
    gui_parser.add_argument("--debug", action="store_true", help="启用调试模式")
    gui_parser.add_argument("--width", type=int, default=1200, help="窗口宽度")
    gui_parser.add_argument("--height", type=int, default=800, help="窗口高度")
    gui_parser.set_defaults(func=launch_gui)


def launch_gui(args):
    """启动 GUI 应用"""
    try:
        # 构建配置
        config = _build_config_from_args(args)

        # 创建并启动应用
        app = AIForgeGUIApp(config)
        app.run()

    except KeyboardInterrupt:
        print("\n👋 AIForge GUI 已退出")
        sys.exit(0)
    except Exception as e:
        print(f"❌ GUI 启动失败: {e}")
        sys.exit(1)


def _build_config_from_args(args) -> Dict[str, Any]:
    """从命令行参数构建配置"""
    config = {}

    # 基本配置
    if args.api_key:
        config["api_key"] = args.api_key
    if args.provider:
        config["provider"] = args.provider
    if args.config:
        config["config_file"] = args.config
    if args.remote:
        config["remote_url"] = args.remote

    # GUI 特定配置
    config["debug"] = args.debug
    config["theme"] = args.theme
    config["window_width"] = args.width
    config["window_height"] = args.height

    return config


def main():
    """独立的 GUI 启动入口"""
    parser = argparse.ArgumentParser(description="AIForge GUI")
    add_gui_commands(parser._subparsers)

    args = parser.parse_args()
    if hasattr(args, "func"):
        args.func(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()

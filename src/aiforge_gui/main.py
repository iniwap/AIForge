#!/usr/bin/env python3
"""AIForge GUI webview 主入口"""

import sys
import threading
import webview as pywebview
import platform
from typing import Dict, Any
from .core.engine_manager import EngineManager
from .core.webview_bridge import WebViewBridge
from .core.api_server import LocalAPIServer
from .config.settings import GUISettings
from .utils.resource_manager import ResourceManager
import pystray
from PIL import Image


class AIForgeGUIApp:
    """AIForge webview GUI 应用"""

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.settings = GUISettings()
        self.resource_manager = ResourceManager()
        self.engine_manager = EngineManager(self.config)
        self.api_server = None
        self.bridge = None
        self.window = None
        self.tray = None

        self.icon_path = self.resource_manager.get_icon_path()

    def create_tray_icon(self):
        """创建系统托盘图标"""
        try:
            # 加载图标
            if self.icon_path.exists():
                image = Image.open(self.icon_path)
            else:
                # 创建简单的默认图标
                image = Image.new("RGBA", (64, 64), (0, 100, 200, 255))

            # 创建托盘菜单
            menu = pystray.Menu(
                pystray.MenuItem("显示 AIForge", self.show_window),
                pystray.MenuItem("隐藏", self.hide_window),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("退出", self.quit_application),
            )

            # 创建托盘图标
            self.tray = pystray.Icon("AIForge", image, "AIForge - 智能意图自适应执行引擎", menu)

        except Exception:
            self.tray = None

    def _set_window_icon_windows(self):
        """Windows 平台设置窗口图标"""
        if platform.system() != "Windows" or not self.icon_path.exists():
            return

        try:
            import win32gui
            import win32con
            import time

            # 等待窗口创建完成
            time.sleep(1.0)

            if pywebview.windows and len(pywebview.windows) > 0:
                # 获取窗口句柄
                hwnd = None
                try:
                    hwnd = pywebview.windows[0].hwnd
                except AttributeError:
                    # 如果没有 hwnd 属性，尝试通过窗口标题查找
                    def enum_windows_proc(hwnd, lParam):
                        if win32gui.IsWindowVisible(hwnd):
                            window_text = win32gui.GetWindowText(hwnd)
                            if "AIForge" in window_text:
                                lParam.append(hwnd)
                        return True

                    windows = []
                    win32gui.EnumWindows(enum_windows_proc, windows)
                    if windows:
                        hwnd = windows[0]

                if hwnd:
                    # 加载图标
                    icon = win32gui.LoadImage(
                        0,
                        str(self.icon_path),
                        win32con.IMAGE_ICON,
                        0,
                        0,
                        win32con.LR_LOADFROMFILE | win32con.LR_DEFAULTSIZE,
                    )

                    if icon:
                        # 设置窗口图标（标题栏）
                        win32gui.SendMessage(hwnd, win32con.WM_SETICON, win32con.ICON_SMALL, icon)
                        win32gui.SendMessage(hwnd, win32con.WM_SETICON, win32con.ICON_BIG, icon)

                        # 设置任务栏图标 - 新增这部分
                        try:
                            # 强制刷新任务栏图标
                            win32gui.SetWindowPos(
                                hwnd,
                                0,
                                0,
                                0,
                                0,
                                0,
                                win32con.SWP_NOMOVE
                                | win32con.SWP_NOSIZE
                                | win32con.SWP_NOZORDER
                                | win32con.SWP_FRAMECHANGED,
                            )

                            # 发送任务栏图标更新消息
                            win32gui.SendMessage(hwnd, win32con.WM_SETICON, win32con.ICON_BIG, icon)
                            win32gui.SendMessage(
                                hwnd, win32con.WM_SETICON, win32con.ICON_SMALL, icon
                            )

                            # 强制重绘窗口
                            win32gui.InvalidateRect(hwnd, None, True)
                            win32gui.UpdateWindow(hwnd)
                        except Exception:
                            pass
        except Exception:
            pass

    def initialize(self):
        """初始化应用"""
        # 验证资源文件
        self.resource_manager.setup_resources()

        # 创建 webview 桥接
        self.bridge = WebViewBridge(self.engine_manager)

        # 根据模式启动相应服务
        if self.engine_manager.is_local_mode():
            self._start_local_mode()
        else:
            self._start_remote_mode()

    def show_window(self, icon=None, item=None):
        """显示窗口"""
        if pywebview.windows and len(pywebview.windows) > 0:
            pywebview.windows[0].show()

    def hide_window(self, icon=None, item=None):
        """隐藏窗口"""
        if pywebview.windows and len(pywebview.windows) > 0:
            pywebview.windows[0].hide()

    def on_window_closed(self):
        """窗口关闭事件处理"""
        # 窗口关闭时隐藏到托盘而不是退出
        if pywebview.windows and len(pywebview.windows) > 0:
            self.hide_window()
        return False  # 阻止窗口真正关闭

    def quit_application(self, icon=None, item=None):
        """退出应用"""
        if self.tray:
            self.tray.stop()
        pywebview.destroy()

    def _start_local_mode(self):
        """启动本地模式"""
        print("🖥️ 启动本地模式...")

        # 启动内置 API 服务器
        self.api_server = LocalAPIServer(self.engine_manager)
        server_thread = threading.Thread(
            target=self.api_server.start, args=("127.0.0.1", 0), daemon=True
        )
        server_thread.start()

        # 等待服务器启动
        self.api_server.wait_for_startup()

        # 获取服务器地址
        server_url = f"http://127.0.0.1:{self.api_server.port}"
        print(f"🚀 本地 API 服务器启动: {server_url}")

        # 创建 webview 窗口
        self._create_window(server_url)

    def _start_remote_mode(self):
        """启动远程模式"""
        print("🌐 启动远程模式...")

        # 直接使用远程服务器地址
        remote_url = self.config.get("remote_url")
        if not remote_url:
            raise ValueError("远程模式需要提供 remote_url")

        # 创建 webview 窗口
        self._create_window(remote_url)

    def _create_window(self, url: str):
        """创建 webview 窗口"""
        # 创建托盘图标
        self.create_tray_icon()
        if self.tray:
            # 在单独线程中运行托盘
            tray_thread = threading.Thread(target=self.tray.run, daemon=True)
            tray_thread.start()

        # 创建 webview 窗口
        self.window = pywebview.create_window(
            title="AIForge - 智能意图自适应执行引擎",
            url=url,
            width=self.config.get("window_width", 1200),
            height=self.config.get("window_height", 800),
            resizable=True,
            shadow=True,
        )

        # 设置窗口关闭事件
        if pywebview.windows:
            pywebview.windows[0].events.closed += self.on_window_closed

    def run(self):
        """运行应用"""
        try:
            self.initialize()

            # 准备启动参数
            start_kwargs = {"debug": self.config.get("debug", False), "http_server": False}

            # 在支持的平台上设置图标
            if platform.system() == "Linux" and self.icon_path.exists():
                start_kwargs["icon"] = str(self.icon_path)
                print(f"✅ 设置 Linux 窗口图标: {self.icon_path}")

            # Windows 平台需要在启动后设置图标
            if platform.system() == "Windows":
                threading.Thread(target=self._set_window_icon_windows, daemon=True).start()

            # 启动 pywebview
            pywebview.start(**start_kwargs)

        except KeyboardInterrupt:
            print("\\n👋 AIForge GUI 已退出")
        except Exception as e:
            print(f"❌ GUI 启动失败: {e}")
            import traceback

            traceback.print_exc()
            sys.exit(1)
        finally:
            self._cleanup()

    def _cleanup(self):
        """清理资源"""
        if self.api_server:
            self.api_server.stop()
        if self.tray:
            self.tray.stop()


def main():
    """主函数"""
    app = AIForgeGUIApp()
    app.run()


if __name__ == "__main__":
    main()

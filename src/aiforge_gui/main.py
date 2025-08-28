#!/usr/bin/env python3
"""AIForge GUI webview 主入口"""

import os
import sys
import time
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
        self.window_created = False

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
            time.sleep(1.5)

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

    def _set_window_icon_macos(self):
        """macOS 平台设置窗口图标和确保窗口显示"""
        if platform.system() != "Darwin":
            return

        try:
            # 等待窗口创建完成
            time.sleep(0.5)

            if pywebview.windows and len(pywebview.windows) > 0:
                window = pywebview.windows[0]

                # 强制显示窗口
                window.show()

                # 尝试将窗口置于前台
                try:
                    # 在 macOS 上，可能需要额外的操作来确保窗口显示
                    import AppKit

                    app = AppKit.NSApplication.sharedApplication()
                    app.activateIgnoringOtherApps_(True)
                except ImportError:
                    # 如果没有 PyObjC，使用基本的显示方法
                    pass

        except Exception:
            pass

    def initialize(self):
        """初始化应用"""
        try:
            # 首先验证运行环境
            if not self.validate_environment():
                raise RuntimeError("环境验证失败，无法启动GUI应用")

            # 验证资源文件
            self.resource_manager.setup_resources()

            # 验证引擎管理器
            if not self.engine_manager:
                raise RuntimeError("引擎管理器初始化失败")

            # 创建 webview 桥接
            self.bridge = WebViewBridge(self.engine_manager)

            # 根据模式启动相应服务
            if self.engine_manager.is_local_mode():
                self._start_local_mode()
            else:
                self._start_remote_mode()

            print("✅ AIForge GUI初始化完成")

        except Exception as e:
            print(f"❌ GUI初始化失败: {e}")
            import traceback

            traceback.print_exc()
            raise

    def validate_environment(self):
        """验证运行环境"""
        warnings = []
        errors = []

        # 检查API密钥 - 改为警告
        api_key = os.environ.get("OPENROUTER_API_KEY") or os.environ.get("AIFORGE_API_KEY")
        if not api_key:
            warnings.append("未设置API密钥，请在界面中配置后使用")

        # 检查网络连接
        try:
            import requests

            requests.get("https://www.baidu.com", timeout=5)
        except Exception:
            warnings.append("网络连接异常，可能影响在线功能")

        # 检查必要的依赖 - 这些仍然是错误
        required_modules = ["webview", "requests", "fastapi"]
        for module in required_modules:
            try:
                __import__(module)
            except ImportError:
                errors.append(f"缺少必要依赖: {module}")

        # 显示警告信息
        if warnings:
            print("⚠️ 环境检查警告:")
            for warning in warnings:
                print(f"  - {warning}")

        # 显示错误信息
        if errors:
            print("❌ 环境检查发现严重问题:")
            for error in errors:
                print(f"  - {error}")
            return False

        return True

    def show_window(self, icon=None, item=None):
        """显示窗口"""
        if pywebview.windows and len(pywebview.windows) > 0:
            pywebview.windows[0].show()
            # macOS 特殊处理
            if platform.system() == "Darwin":
                try:
                    import AppKit

                    app = AppKit.NSApplication.sharedApplication()
                    app.activateIgnoringOtherApps_(True)
                except ImportError:
                    pass

    def hide_window(self, icon=None, item=None):
        """隐藏窗口"""
        if pywebview.windows and len(pywebview.windows) > 0:
            pywebview.windows[0].hide()

    def on_window_closed(self):
        """窗口关闭事件处理"""
        # 执行优雅关闭流程
        self.shutdown()

        # 只有在窗口已经正常创建并且用户选择最小化到托盘时才隐藏
        if self.window_created and self.tray and self.config.get("minimize_to_tray", False):
            if pywebview.windows and len(pywebview.windows) > 0:
                self.hide_window()
            return False  # 阻止窗口真正关闭
        else:
            # 直接退出应用
            return True

    def quit_application(self, icon=None, item=None):
        """退出应用"""
        if self.tray:
            self.tray.stop()
        pywebview.destroy()

    def _start_local_mode(self):
        """启动本地模式"""
        try:
            # 启动内置 API 服务器
            self.api_server = LocalAPIServer(self.engine_manager)

            # 将 API 服务器引用传递给 EngineManager
            self.engine_manager._api_server = self.api_server

            # 使用线程启动服务器
            server_thread = threading.Thread(
                target=self.api_server.start, args=("127.0.0.1", 0), daemon=True
            )
            server_thread.start()

            # 等待服务器启动
            startup_timeout = 30
            if not self.api_server.wait_for_startup(timeout=startup_timeout):
                raise RuntimeError(f"API服务器启动超时（{startup_timeout}秒）")

            # 获取服务器地址
            server_url = f"http://127.0.0.1:{self.api_server.port}"
            # 创建 webview 窗口
            self._create_window(server_url)

        except Exception as e:
            print(f"❌ 本地模式启动失败: {e}")
            raise

    def _start_api_server_with_retry(self, host, port, max_retries=3):
        """带重试机制的API服务器启动"""
        for attempt in range(max_retries):
            try:
                self.api_server.start(host, port)
                return
            except Exception as e:
                print(f"⚠️ API服务器启动尝试 {attempt + 1}/{max_retries} 失败: {e}")
                if attempt == max_retries - 1:
                    raise
                time.sleep(2)  # 等待2秒后重试

    def _test_api_server(self, server_url):
        """测试API服务器可用性"""
        try:
            import requests

            response = requests.get(f"{server_url}/health", timeout=5)
            return response.status_code == 200
        except Exception:
            return False

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
        # 确保桥接对象存在
        if not self.bridge:
            print("❌ WebView桥接对象未创建")
            raise RuntimeError("WebView桥接对象未创建")

        # 创建 webview 窗口并传递桥接对象
        self.window = pywebview.create_window(
            title="AIForge - 智能意图自适应执行引擎",
            url=url,
            width=self.config.get("window_width", 1200),
            height=self.config.get("window_height", 800),
            resizable=True,
            shadow=True,
            js_api=self.bridge,
        )

        # 设置窗口事件处理
        if pywebview.windows:
            window = pywebview.windows[0]
            window.events.closed += self.on_window_closed

            # 监听窗口加载完成事件
            def on_loaded():
                # 等待一小段时间确保 API 完全注入
                time.sleep(0.1)
                # 触发自定义就绪事件
                try:
                    window.evaluate_js("document.dispatchEvent(new Event('pywebviewready'))")
                    # Windows 图标设置
                    if platform.system() == "Windows":
                        threading.Thread(target=self._set_window_icon_windows, daemon=True).start()
                except Exception:
                    pass

            window.events.loaded += on_loaded

        # 标记窗口已创建
        self.window_created = True

        # 延迟创建托盘图标，确保窗口先显示
        def delayed_tray_creation():
            time.sleep(2.0)  # 等待窗口完全显示
            if self.config.get("enable_tray", True):  # 允许配置禁用托盘
                self.create_tray_icon()
                if self.tray:
                    tray_thread = threading.Thread(target=self.tray.run, daemon=True)
                    tray_thread.start()

        # 启动延迟托盘创建线程
        threading.Thread(target=delayed_tray_creation, daemon=True).start()

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
                pass
            # macOS 平台需要特殊处理窗口显示
            elif platform.system() == "Darwin":
                threading.Thread(target=self._set_window_icon_macos, daemon=True).start()

            # 启动 pywebview
            pywebview.start(**start_kwargs)

        except KeyboardInterrupt:
            print("\n👋 AIForge GUI 已退出")
        except Exception as e:
            print(f"❌ GUI 启动失败: {e}")
            import traceback

            traceback.print_exc()
            sys.exit(1)
        finally:
            self.shutdown()

    def shutdown(self):
        """统一的关闭方法"""
        # 1. 从引擎获取shutdown_manager
        shutdown_manager = None
        if self.engine_manager:
            try:
                shutdown_manager = self.engine_manager.get_shutdown_manager()
            except RuntimeError:
                # 如果引擎未初始化（如缺少API密钥），跳过引擎相关清理
                pass

        if shutdown_manager:
            shutdown_manager.shutdown()  # 使用统一的shutdown方法

        # 2. 等待当前任务完成或超时
        max_wait_time = 5.0
        start_time = time.time()

        while time.time() - start_time < max_wait_time:
            try:
                if self.engine_manager and self.engine_manager.get_engine():
                    engine = self.engine_manager.get_engine()
                    if hasattr(engine, "task_manager") and hasattr(
                        engine.task_manager, "active_tasks"
                    ):
                        if not engine.task_manager.active_tasks:
                            break
            except RuntimeError:
                # 引擎未初始化，跳出等待循环
                break
            time.sleep(0.1)

        # 3. 强制停止所有组件
        try:
            if self.engine_manager and self.engine_manager.get_engine():
                engine = self.engine_manager.get_engine()
                if hasattr(engine, "shutdown"):
                    try:
                        engine.shutdown()
                    except Exception:
                        pass
                elif hasattr(engine, "component_manager") and hasattr(
                    engine.component_manager, "shutdown"
                ):
                    try:
                        engine.component_manager.shutdown()
                    except Exception:
                        pass
        except RuntimeError:
            # 引擎未初始化，跳过引擎清理
            pass

        # 4. 停止API服务器
        if self.api_server:
            try:
                self.api_server.shutdown()  # 使用统一的shutdown方法
            except Exception:
                pass

        # 5. 停止系统托盘
        if self.tray:
            try:
                self.tray.stop()
            except Exception:
                pass


def main():
    """主函数"""
    app = AIForgeGUIApp()
    app.run()


if __name__ == "__main__":
    main()

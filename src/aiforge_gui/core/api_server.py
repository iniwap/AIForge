import threading
import socket
from pathlib import Path
from http.server import HTTPServer, SimpleHTTPRequestHandler
import json
import time


class LocalAPIServer:
    """本地模式的轻量级 API 服务器"""

    def __init__(self, engine_manager):
        self.engine_manager = engine_manager
        self.server = None
        self.port = None
        self.running = False
        self.startup_event = threading.Event()
        self.shutting_down = False

    def start(self, host: str = "127.0.0.1", port: int = 0):
        """启动服务器"""
        try:
            handler = self._create_handler()
            self.server = HTTPServer((host, port), handler)
            self.port = self.server.server_port
            self.running = True

            # 设置启动事件，通知等待线程
            self.startup_event.set()
            # 开始服务
            self.server.serve_forever()
        except Exception as e:
            print(f"❌ API服务器启动失败: {e}")
            self.running = False
            self.startup_event.set()  # 即使失败也要设置事件
            raise

    def wait_for_startup(self, timeout: int = 10):
        """等待服务器启动"""
        if self.startup_event.wait(timeout):
            if self.running and self.port:
                # 额外验证端口是否真的可用
                return self._test_port_available()
            return False
        return False

    def _test_port_available(self):
        """测试端口是否可用"""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(1)
                result = s.connect_ex(("127.0.0.1", self.port))
                return result == 0
        except Exception:
            return False

    def shutdown(self):
        """停止服务器"""
        self.shutting_down = True
        if self.server:
            self.running = False
            self.server.shutdown()
            self.server.server_close()

    def _create_handler(self):
        """创建请求处理器"""
        engine_manager = self.engine_manager

        class AIForgeHandler(SimpleHTTPRequestHandler):
            def __init__(self, *args, **kwargs):
                self.resources_dir = Path(__file__).parent.parent / "resources"
                super().__init__(*args, **kwargs)

            def translate_path(self, path):
                """重写路径转换，不改变全局工作目录"""
                # 移除查询参数
                path = path.split("?", 1)[0]
                path = path.split("#", 1)[0]

                # 如果是静态文件请求，使用 resources 目录
                if not path.startswith("/api/"):
                    return str(self.resources_dir / path.lstrip("/"))

                return super().translate_path(path)

            def do_GET(self):
                """处理 GET 请求"""
                if self.path == "/" or self.path == "/index.html":
                    self._serve_index()
                elif self.path.startswith("/api/"):
                    self._handle_api_get()
                else:
                    # 静态文件
                    super().do_GET()

            def do_POST(self):
                """处理 POST 请求"""
                if self.path.startswith("/api/"):
                    self._handle_api_post()
                else:
                    self.send_error(404)

            def _serve_index(self):
                """提供主页面"""
                try:
                    index_path = (
                        Path(__file__).parent.parent / "resources" / "templates" / "index.html"
                    )
                    with open(index_path, "r", encoding="utf-8") as f:
                        content = f.read()

                    self.send_response(200)
                    self.send_header("Content-type", "text/html; charset=utf-8")
                    self.end_headers()
                    self.wfile.write(content.encode("utf-8"))
                except (ConnectionAbortedError, BrokenPipeError, ConnectionResetError):
                    # 静默处理连接断开，避免在GUI关闭时产生错误日志
                    return
                except Exception as e:
                    try:
                        self.send_error(500, f"Error serving index: {e}")
                    except (ConnectionAbortedError, BrokenPipeError, ConnectionResetError):
                        # 连接已断开，无法发送错误响应
                        pass

            def _handle_api_get(self):
                """处理 API GET 请求"""
                if self.path == "/api/health":
                    self._send_json({"status": "ok", "mode": engine_manager.mode.value})
                elif self.path == "/api/system":
                    if engine_manager.is_local_mode():
                        engine = engine_manager.get_engine()
                        if engine:
                            info = (
                                engine.get_system_info()
                                if hasattr(engine, "get_system_info")
                                else {}
                            )
                            self._send_json(info)
                        else:
                            self._send_json({"error": "Engine not available"})
                    else:
                        self._send_json({"error": "Remote mode"})
                else:
                    self.send_error(404)

            def _handle_api_post(self):
                """处理 API POST 请求"""
                if self.path == "/api/execute":
                    try:
                        content_length = int(self.headers["Content-Length"])
                        post_data = self.rfile.read(content_length)
                        data = json.loads(post_data.decode("utf-8"))

                        instruction = data.get("instruction", "")
                        if not instruction:
                            self._send_json({"error": "No instruction provided"}, 400)
                            return

                        if engine_manager.is_local_mode():
                            engine = engine_manager.get_engine()
                            if engine:
                                result = engine.run(instruction)
                                # 确保结果正确序列化
                                if hasattr(result, "to_dict"):
                                    adapted_result = result.to_dict()
                                else:
                                    adapted_result = engine.adapt_result_for_ui(
                                        result,
                                        (
                                            "editor"
                                            if result.task_type == "content_generation"
                                            else None
                                        ),
                                        "gui",
                                    )

                                self._send_json(
                                    {
                                        "success": True,
                                        "data": adapted_result,
                                        "metadata": {"source": "local"},
                                    }
                                )
                            else:
                                self._send_json({"error": "Engine not available"}, 500)
                        else:
                            self._send_json(
                                {"error": "Remote mode not supported in local server"}, 400
                            )

                    except Exception as e:
                        self._send_json({"error": str(e)}, 500)
                elif self.path == "/api/v1/core/execute/stream":
                    # 添加流式执行支持
                    self._handle_streaming_execute()
                else:
                    self.send_error(404)

            def _handle_streaming_execute(self):
                """处理流式执行请求 - 使用优化的流式管理器"""
                try:
                    content_length = int(self.headers["Content-Length"])
                    post_data = self.rfile.read(content_length)
                    data = json.loads(post_data.decode("utf-8"))

                    instruction = data.get("instruction", "")
                    if not instruction:
                        self.send_error(400)
                        return

                    # 设置 SSE 响应头
                    self.send_response(200)
                    self.send_header("Content-Type", "text/event-stream")
                    self.send_header("Cache-Control", "no-cache")
                    self.send_header("Connection", "keep-alive")
                    self.end_headers()

                    try:
                        if engine_manager.is_local_mode():
                            streaming_manager = engine_manager.get_streaming_manager()
                            if streaming_manager:
                                # 准备上下文数据
                                context_data = {
                                    "task_type": data.get("task_type"),
                                    "session_id": data.get("session_id", str(time.time())),
                                    "progress_level": "detailed",
                                }

                                # 使用异步生成器处理流式执行
                                import asyncio

                                loop = asyncio.new_event_loop()
                                asyncio.set_event_loop(loop)

                                try:

                                    async def stream_execution():
                                        async for (
                                            sse_data
                                        ) in streaming_manager.execute_with_streaming(
                                            instruction, context_data
                                        ):
                                            if not self.wfile.closed:
                                                self.wfile.write(sse_data.encode())
                                                self.wfile.flush()
                                            else:
                                                streaming_manager._client_disconnected = True
                                                break

                                    loop.run_until_complete(stream_execution())
                                finally:
                                    loop.close()
                            else:
                                error_data = json.dumps(
                                    {
                                        "type": "error",
                                        "message": "流式管理器不可用",
                                        "timestamp": time.time(),
                                    }
                                )
                                self.wfile.write(f"data: {error_data}\n\n".encode())
                        else:
                            error_data = json.dumps(
                                {
                                    "type": "error",
                                    "message": "远程模式不支持流式执行",
                                    "timestamp": time.time(),
                                }
                            )
                            self.wfile.write(f"data: {error_data}\n\n".encode())

                    except Exception as e:
                        # 如果服务器正在关闭，静默处理错误
                        if (
                            self.server
                            and hasattr(self.server, "shutting_down")
                            and self.server.shutting_down
                        ):
                            return
                        error_data = json.dumps(
                            {
                                "type": "error",
                                "message": f"流式执行错误: {str(e)}",
                                "timestamp": time.time(),
                            }
                        )
                        # 只在连接仍然有效时发送错误消息
                        try:
                            if not self.wfile.closed:
                                error_data = json.dumps(
                                    {
                                        "type": "error",
                                        "message": f"流式执行错误: {str(e)}",
                                        "timestamp": time.time(),
                                    }
                                )
                                self.wfile.write(f"data: {error_data}\n\n".encode())
                        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                            # 静默处理所有连接相关错误
                            pass

                except Exception:
                    # 避免在连接断开或服务器关闭时调用 send_error
                    if (
                        self.server
                        and hasattr(self.server, "shutting_down")
                        and self.server.shutting_down
                    ):
                        return

                    try:
                        if not self.wfile.closed:
                            self.send_error(500)
                    except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                        # 静默处理连接断开
                        pass

            def _send_json(self, data, status=200):
                """发送 JSON 响应"""
                self.send_response(status)
                self.send_header("Content-type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps(data).encode("utf-8"))

            def log_message(self, format, *args):
                """静默日志输出"""
                # 检查是否是连接相关错误且服务器正在关闭
                if hasattr(self.server, "shutting_down") and self.server.shutting_down:
                    return
                # 其他情况保持静默（原有行为）
                pass

        return AIForgeHandler

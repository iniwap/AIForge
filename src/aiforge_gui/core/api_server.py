import time
from http.server import HTTPServer, SimpleHTTPRequestHandler
import json
import os
from pathlib import Path


class LocalAPIServer:
    """本地模式的轻量级 API 服务器"""

    def __init__(self, engine_manager):
        self.engine_manager = engine_manager
        self.server = None
        self.port = None
        self.running = False

    def start(self, host: str = "127.0.0.1", port: int = 0):
        """启动服务器"""
        handler = self._create_handler()
        self.server = HTTPServer((host, port), handler)
        self.port = self.server.server_port
        self.running = True

        self.server.serve_forever()

    def stop(self):
        """停止服务器"""
        if self.server:
            self.running = False
            self.server.shutdown()
            self.server.server_close()

    def wait_for_startup(self, timeout: int = 10):
        """等待服务器启动"""
        start_time = time.time()
        while not self.running and (time.time() - start_time) < timeout:
            time.sleep(0.1)

        if not self.running:
            raise TimeoutError(f"服务器在 {timeout} 秒内未能启动")

    def _create_handler(self):
        """创建请求处理器"""
        engine_manager = self.engine_manager

        class AIForgeHandler(SimpleHTTPRequestHandler):
            def __init__(self, *args, **kwargs):
                # 设置静态文件目录为 resources
                resources_dir = Path(__file__).parent.parent / "resources"
                os.chdir(resources_dir)
                super().__init__(*args, **kwargs)

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
                except Exception as e:
                    self.send_error(500, f"Error serving index: {e}")

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
                                adapted_result = engine.adapt_result_for_ui(
                                    result, "webview", "gui"
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
                else:
                    self.send_error(404)

            def _send_json(self, data, status=200):
                """发送 JSON 响应"""
                self.send_response(status)
                self.send_header("Content-type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps(data).encode("utf-8"))

            def log_message(self, format, *args):
                """静默日志输出"""
                pass

        return AIForgeHandler

import asyncio
import time
from typing import Dict, Any, Callable, Optional


class StreamingProgressIndicator:
    """流式进度指示器"""

    def __init__(
        self, components: Dict[str, Any] = None, stream_callback: Optional[Callable] = None
    ):
        self._show_progress = True
        self.components = components or {}
        self.stream_callback = stream_callback
        # 获取 i18n 管理器
        self._i18n_manager = components["i18n_manager"]

    def _send_progress(self, message: str, progress_type: str = "info"):
        """发送进度消息到流"""
        if self.stream_callback:
            try:
                message_data = {
                    "type": "progress",
                    "message": message,
                    "progress_type": progress_type,
                    "timestamp": time.time(),
                }

                # 使用线程安全的方式调用异步回调
                import threading

                def call_async_callback():
                    try:
                        # 在新的事件循环中运行回调
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        try:
                            loop.run_until_complete(self.stream_callback(message_data))
                        finally:
                            loop.close()
                    except Exception:
                        pass

                # 在后台线程中执行异步回调
                thread = threading.Thread(target=call_async_callback, daemon=True)
                thread.start()

            except Exception:
                pass

    # 使用国际化的进度方法
    def show_llm_request(self, provider: str = ""):
        """显示 LLM 请求进度"""
        message = self._i18n_manager.t(
            "progress.connecting_ai", provider=f"({provider})" if provider else ""
        )
        self._send_progress(message, "llm_request")
        # 同时输出到终端
        if self._show_progress:
            print(message)

    def show_llm_generating(self):
        """显示等待 LLM 响应"""
        message = self._i18n_manager.t("progress.waiting_response")
        self._send_progress(message, "llm_waiting")
        # 同时输出到终端
        if self._show_progress:
            print(message)

    def show_llm_complete(self):
        """显示收到 LLM 响应"""
        message = self._i18n_manager.t("progress.processing_response")
        self._send_progress(message, "llm_response")
        # 同时输出到终端
        if self._show_progress:
            print(message)

    def show_search_start(self, query: str):
        """显示搜索开始"""
        truncated_query = query[:50] + ("..." if len(query) > 50 else "")
        message = self._i18n_manager.t("progress.searching", query=truncated_query)
        self._send_progress(message, "search_start")
        # 同时输出到终端
        if self._show_progress:
            print(message)

    def show_search_process(self, search_type: str):
        """显示搜索过程"""
        message = self._i18n_manager.t("progress.search_process", search_type=search_type)
        self._send_progress(message, "search_process")
        # 同时输出到终端
        if self._show_progress:
            print(message)

    def show_search_complete(self, count: int):
        """显示搜索完成"""
        message = self._i18n_manager.t("progress.search_complete", count=count)
        self._send_progress(message, "search_complete")
        # 同时输出到终端
        if self._show_progress:
            print(message)

    def show_cache_lookup(self):
        """显示缓存查找"""
        message = self._i18n_manager.t("progress.cache_lookup")
        self._send_progress(message, "cache_lookup")
        # 同时输出到终端
        if self._show_progress:
            print(message)

    def show_cache_found(self, count: int):
        """显示找到缓存"""
        message = self._i18n_manager.t("progress.cache_found", count=count)
        self._send_progress(message, "cache_found")
        # 同时输出到终端
        if self._show_progress:
            print(message)

    def show_cache_execution(self):
        """显示缓存执行"""
        message = self._i18n_manager.t("progress.cache_execution")
        self._send_progress(message, "cache_execution")
        # 同时输出到终端
        if self._show_progress:
            print(message)

    def show_code_execution(self, count: int = 1):
        """显示代码执行"""
        message = self._i18n_manager.t("progress.code_execution", count=count)
        self._send_progress(message, "code_execution")
        # 同时输出到终端
        if self._show_progress:
            print(message)

    def show_round_start(self, current: int, total: int):
        """显示轮次开始"""
        message = self._i18n_manager.t("progress.round_start", current=current, total=total)
        self._send_progress(message, "round_start")
        # 同时输出到终端
        if self._show_progress:
            print(message)

    def show_round_success(self, round_num: int):
        """显示轮次成功"""
        message = self._i18n_manager.t("progress.round_success", round_num=round_num)
        self._send_progress(message, "round_success")
        # 同时输出到终端
        if self._show_progress:
            print(message)

    def show_round_retry(self, round_num: int):
        """显示轮次重试"""
        message = self._i18n_manager.t("progress.round_retry", round_num=round_num)
        self._send_progress(message, "round_retry")
        # 同时输出到终端
        if self._show_progress:
            print(message)

    def set_show_progress(self, show: bool):
        """设置是否显示进度"""
        self._show_progress = show

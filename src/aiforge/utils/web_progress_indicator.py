import asyncio
import time
from typing import Dict, Any, Callable, Optional
from aiforge.i18n.manager import AIForgeI18nManager


class WebProgressIndicator:
    """Web 流式进度指示器 - 独立实现避免单例冲突"""

    def __init__(
        self, components: Dict[str, Any] = None, stream_callback: Optional[Callable] = None
    ):
        self._show_progress = True
        self.components = components or {}
        self.stream_callback = stream_callback

        # 获取 i18n 管理器
        if components and "i18n_manager" in components:
            self._i18n_manager = components["i18n_manager"]
        else:
            self._i18n_manager = AIForgeI18nManager.get_instance()

    def _send_progress(self, message: str, progress_type: str = "info"):
        """发送进度消息到流"""
        if self.stream_callback:
            try:
                asyncio.create_task(
                    self.stream_callback(
                        {
                            "type": "progress",
                            "message": message,
                            "progress_type": progress_type,
                            "timestamp": time.time(),
                        }
                    )
                )
            except Exception as e:
                print(f"发送进度消息失败: {e}")

        # 同时输出到控制台作为备份
        print(f"[WebProgress] {message}")

    # 使用国际化的进度方法
    def show_llm_request(self, provider: str = ""):
        """显示 LLM 请求进度"""
        message = self._i18n_manager.t(
            "progress.connecting_ai", provider=f"({provider})" if provider else ""
        )
        self._send_progress(message, "llm_request")

    def show_llm_generating(self):
        """显示等待 LLM 响应"""
        message = self._i18n_manager.t("progress.waiting_response")
        self._send_progress(message, "llm_waiting")

    def show_llm_complete(self):
        """显示收到 LLM 响应"""
        message = self._i18n_manager.t("progress.processing_response")
        self._send_progress(message, "llm_response")

    def show_search_start(self, query: str):
        """显示搜索开始"""
        truncated_query = query[:50] + ("..." if len(query) > 50 else "")
        message = self._i18n_manager.t("progress.searching", query=truncated_query)
        self._send_progress(message, "search_start")

    def show_search_process(self, search_type: str):
        """显示搜索过程"""
        message = self._i18n_manager.t("progress.search_process", search_type=search_type)
        self._send_progress(message, "search_process")

    def show_search_complete(self, count: int):
        """显示搜索完成"""
        message = self._i18n_manager.t("progress.search_complete", count=count)
        self._send_progress(message, "search_complete")

    def show_cache_lookup(self):
        """显示缓存查找"""
        message = self._i18n_manager.t("progress.cache_lookup")
        self._send_progress(message, "cache_lookup")

    def show_cache_found(self, count: int):
        """显示找到缓存"""
        message = self._i18n_manager.t("progress.cache_found", count=count)
        self._send_progress(message, "cache_found")

    def show_cache_execution(self):
        """显示缓存执行"""
        message = self._i18n_manager.t("progress.cache_execution")
        self._send_progress(message, "cache_execution")

    def show_code_execution(self, count: int = 1):
        """显示代码执行"""
        message = self._i18n_manager.t("progress.code_execution", count=count)
        self._send_progress(message, "code_execution")

    def show_round_start(self, current: int, total: int):
        """显示轮次开始"""
        message = self._i18n_manager.t("progress.round_start", current=current, total=total)
        self._send_progress(message, "round_start")

    def show_round_success(self, round_num: int):
        """显示轮次成功"""
        message = self._i18n_manager.t("progress.round_success", round_num=round_num)
        self._send_progress(message, "round_success")

    def show_round_retry(self, round_num: int):
        """显示轮次重试"""
        message = self._i18n_manager.t("progress.round_retry", round_num=round_num)
        self._send_progress(message, "round_retry")

    def set_show_progress(self, show: bool):
        """设置是否显示进度"""
        self._show_progress = show

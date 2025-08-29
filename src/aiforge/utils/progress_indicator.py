import time
import inspect
import asyncio
from typing import Dict, Any, Callable, Optional


class ProgressEventBus:
    """纯事件驱动的进度总线"""

    def __init__(self):
        self._current_handler: Optional[Any] = None

    def set_handler(self, handler: Any):
        """设置当前进度处理器"""
        self._current_handler = handler

    def get_handler(self) -> Optional[Any]:
        """获取当前处理器"""
        return self._current_handler

    def emit(self, event_type: str, **kwargs):
        """发送进度事件 - 智能处理同步和异步"""
        if self._current_handler:
            method_name = f"handle_{event_type}"
            if hasattr(self._current_handler, method_name):
                method = getattr(self._current_handler, method_name)
                try:
                    if inspect.iscoroutinefunction(method):
                        # 异步方法：在当前事件循环中调度
                        try:
                            loop = asyncio.get_running_loop()
                            # 创建任务并立即调度，不等待结果
                            loop.create_task(method(**kwargs))
                        except RuntimeError:
                            # 没有运行的事件循环，创建新的
                            asyncio.run(method(**kwargs))
                    else:
                        # 同步方法直接调用
                        method(**kwargs)
                except Exception as e:
                    print(f"Progress event error: {e}")


class ProgressEventHandler:
    """标准进度事件处理器"""

    def __init__(self, components: Dict[str, Any] = None):
        self._show_progress = True
        if components:
            self.components = components
            self._i18n_manager = self.components.get("i18n_manager")
        else:
            self.components = None
            self._i18n_manager = None

    def set_show_progress(self, show: bool):
        self._show_progress = show

    def handle_llm_request(self, provider: str = ""):
        if self._show_progress and self._i18n_manager:
            message = self._i18n_manager.t(
                "progress.connecting_ai", provider=f"({provider})" if provider else ""
            )
            print(message)

    def handle_llm_generating(self):
        if self._show_progress and self._i18n_manager:
            message = self._i18n_manager.t("progress.waiting_response")
            print(message)

    def handle_llm_complete(self):
        if self._show_progress and self._i18n_manager:
            message = self._i18n_manager.t("progress.processing_response")
            print(message)

    def handle_cache_lookup(self):
        if self._show_progress and self._i18n_manager:
            message = self._i18n_manager.t("progress.cache_lookup")
            print(message)

    def handle_cache_found(self, count: int):
        if self._show_progress and self._i18n_manager:
            message = self._i18n_manager.t("progress.cache_found", count=count)
            print(message)

    def handle_cache_execution(self):
        if self._show_progress and self._i18n_manager:
            message = self._i18n_manager.t("progress.cache_execution")
            print(message)

    def handle_code_execution(self, count: int = 1):
        if self._show_progress and self._i18n_manager:
            message = self._i18n_manager.t("progress.code_execution", count=count)
            print(message)

    def handle_search_start(self, query: str):
        if self._show_progress and self._i18n_manager:
            truncated_query = query[:50] + ("..." if len(query) > 50 else "")
            message = self._i18n_manager.t("progress.searching", query=truncated_query)
            print(message)

    def handle_search_process(self, search_type):
        if self._show_progress and self._i18n_manager:
            message = self._i18n_manager.t("progress.search_process", search_type=search_type)
            print(message)

    def handle_search_complete(self, count: int):
        if self._show_progress and self._i18n_manager:
            message = self._i18n_manager.t("progress.search_complete", count=count)
            print(message)

    def handle_round_start(self, current: int, total: int):
        if self._show_progress and self._i18n_manager:
            message = self._i18n_manager.t("progress.round_start", current=current, total=total)
            print(message)

    def handle_round_success(self, round_num: int):
        if self._show_progress and self._i18n_manager:
            message = self._i18n_manager.t("progress.round_success", round_num=round_num)
            print(message)

    def handle_round_retry(self, round_num: int):
        if self._show_progress and self._i18n_manager:
            message = self._i18n_manager.t("progress.round_retry", round_num=round_num)
            print(message)


class StreamingProgressEventHandler:
    """流式进度事件处理器"""

    def __init__(self, components: Dict[str, Any], progress_callback: Callable):
        self.components = components
        self.progress_callback = progress_callback
        self._i18n_manager = components.get("i18n_manager")
        self._show_progress = True

    def set_show_progress(self, show: bool):
        self._show_progress = show

    async def handle_llm_request(self, provider: str = ""):
        message = f"🔗 连接AI服务 {f'({provider})' if provider else ''}..."
        if self._show_progress and self._i18n_manager:
            message = self._i18n_manager.t(
                "progress.connecting_ai", provider=f"({provider})" if provider else ""
            )

            await self.progress_callback(
                {
                    "type": "progress",
                    "message": message,
                    "progress_type": "llm_request",
                    "timestamp": time.time(),
                }
            )
            print(message)

    async def handle_llm_generating(self):
        message = "⏳ 等待AI响应..."
        if self._show_progress and self._i18n_manager:
            message = self._i18n_manager.t("progress.waiting_response")

            await self.progress_callback(
                {
                    "type": "progress",
                    "message": message,
                    "progress_type": "llm_generating",
                    "timestamp": time.time(),
                }
            )
            print(message)

    async def handle_llm_complete(self):
        message = "✅ 处理AI响应..."
        if self._show_progress and self._i18n_manager:
            message = self._i18n_manager.t("progress.processing_response")

            await self.progress_callback(
                {
                    "type": "progress",
                    "message": message,
                    "progress_type": "llm_complete",
                    "timestamp": time.time(),
                }
            )
            print(message)

    async def handle_cache_lookup(self):
        message = "🔍 查找缓存..."
        if self._show_progress and self._i18n_manager:
            message = self._i18n_manager.t("progress.cache_lookup")

            await self.progress_callback(
                {
                    "type": "progress",
                    "message": message,
                    "progress_type": "cache_lookup",
                    "timestamp": time.time(),
                }
            )
            print(message)

    async def handle_cache_found(self, count: int):
        message = f"📦 找到 {count} 个缓存模块"
        if self._show_progress and self._i18n_manager:
            message = self._i18n_manager.t("progress.cache_found", count=count)

            await self.progress_callback(
                {
                    "type": "progress",
                    "message": message,
                    "progress_type": "cache_found",
                    "timestamp": time.time(),
                }
            )
            print(message)

    async def handle_cache_execution(self):
        message = "⚡ 执行缓存代码..."
        if self._show_progress and self._i18n_manager:
            message = self._i18n_manager.t("progress.cache_execution")

            await self.progress_callback(
                {
                    "type": "progress",
                    "message": message,
                    "progress_type": "cache_execution",
                    "timestamp": time.time(),
                }
            )
            print(message)

    async def handle_code_execution(self, count: int = 1):
        message = f"🚀 执行代码 ({count} 个模块)..."
        if self._show_progress and self._i18n_manager:
            message = self._i18n_manager.t("progress.code_execution", count=count)

            await self.progress_callback(
                {
                    "type": "progress",
                    "message": message,
                    "progress_type": "code_execution",
                    "timestamp": time.time(),
                }
            )
            print(message)

    async def handle_search_start(self, query: str):
        truncated_query = query[:50] + ("..." if len(query) > 50 else "")
        message = f"🔍 开始搜索: {truncated_query}"
        if self._show_progress and self._i18n_manager:
            message = self._i18n_manager.t("progress.searching", query=truncated_query)

            await self.progress_callback(
                {
                    "type": "progress",
                    "message": message,
                    "progress_type": "search_start",
                    "timestamp": time.time(),
                }
            )
            print(message)

    async def handle_search_process(self, search_type: str):
        message = f"🔄 搜索进行中: {search_type}"
        if self._show_progress and self._i18n_manager:
            message = self._i18n_manager.t("progress.search_process", search_type=search_type)

            await self.progress_callback(
                {
                    "type": "progress",
                    "message": message,
                    "progress_type": "search_process",
                    "timestamp": time.time(),
                }
            )
            print(message)

    async def handle_search_complete(self, count: int):
        message = f"✅ 搜索完成，找到 {count} 个结果"
        if self._show_progress and self._i18n_manager:
            message = self._i18n_manager.t("progress.search_complete", count=count)

            await self.progress_callback(
                {
                    "type": "progress",
                    "message": message,
                    "progress_type": "search_complete",
                    "timestamp": time.time(),
                }
            )
            print(message)

    async def handle_round_start(self, current: int, total: int):
        message = f"🔄 开始第 {current}/{total} 轮处理"
        if self._show_progress and self._i18n_manager:
            message = self._i18n_manager.t("progress.round_start", current=current, total=total)

            await self.progress_callback(
                {
                    "type": "progress",
                    "message": message,
                    "progress_type": "round_start",
                    "timestamp": time.time(),
                }
            )
            print(message)

    async def handle_round_success(self, round_num: int):
        message = f"✅ 第 {round_num} 轮处理成功"
        if self._show_progress and self._i18n_manager:
            message = self._i18n_manager.t("progress.round_success", round_num=round_num)

            await self.progress_callback(
                {
                    "type": "progress",
                    "message": message,
                    "progress_type": "round_success",
                    "timestamp": time.time(),
                }
            )
            print(message)

    async def handle_round_retry(self, round_num: int):
        message = f"🔄 第 {round_num} 轮处理重试"
        if self._show_progress and self._i18n_manager:
            message = self._i18n_manager.t("progress.round_retry", round_num=round_num)

            await self.progress_callback(
                {
                    "type": "progress",
                    "message": message,
                    "progress_type": "round_retry",
                    "timestamp": time.time(),
                }
            )
            print(message)

from typing import Dict, Any


class ProgressIndicator:
    """进度指示器 - 非单例模式"""

    def __init__(self, components: Dict[str, Any] = None):
        """初始化进度指示器实例"""
        self._show_progress = True
        if components:
            self.components = components
            self._i18n_manager = self.components.get("i18n_manager")
        else:
            # 如果没有传入组件，从组件中获取i18n_manager
            self.components = None
            self._i18n_manager = None

    def set_i18n_manager(self, i18n_manager):
        """设置国际化管理器"""
        self._i18n_manager = i18n_manager

    def set_show_progress(self, show: bool):
        self._show_progress = show

    def show_llm_request(self, provider: str = ""):
        if self._show_progress and self._i18n_manager:
            message = self._i18n_manager.t(
                "progress.connecting_ai", provider=f"({provider})" if provider else ""
            )
            print(message)

    def show_llm_generating(self):
        if self._show_progress and self._i18n_manager:
            message = self._i18n_manager.t("progress.waiting_response")
            print(message)

    def show_llm_complete(self):
        if self._show_progress and self._i18n_manager:
            message = self._i18n_manager.t("progress.processing_response")
            print(message)

    def show_search_start(self, query: str):
        if self._show_progress and self._i18n_manager:
            truncated_query = query[:50] + ("..." if len(query) > 50 else "")
            message = self._i18n_manager.t("progress.searching", query=truncated_query)
            print(message)

    def show_search_process(self, search_type):
        if self._show_progress and self._i18n_manager:
            message = self._i18n_manager.t("progress.search_process", search_type=search_type)
            print(message)

    def show_search_complete(self, count: int):
        if self._show_progress and self._i18n_manager:
            message = self._i18n_manager.t("progress.search_complete", count=count)
            print(message)

    def show_cache_lookup(self):
        if self._show_progress and self._i18n_manager:
            message = self._i18n_manager.t("progress.cache_lookup")
            print(message)

    def show_cache_found(self, count: int):
        if self._show_progress and self._i18n_manager:
            message = self._i18n_manager.t("progress.cache_found", count=count)
            print(message)

    def show_cache_execution(self):
        if self._show_progress and self._i18n_manager:
            message = self._i18n_manager.t("progress.cache_execution")
            print(message)

    def show_code_execution(self, count: int = 1):
        if self._show_progress and self._i18n_manager:
            message = self._i18n_manager.t("progress.code_execution", count=count)
            print(message)

    def show_round_start(self, current: int, total: int):
        if self._show_progress and self._i18n_manager:
            message = self._i18n_manager.t("progress.round_start", current=current, total=total)
            print(message)

    def show_round_success(self, round_num: int):
        if self._show_progress and self._i18n_manager:
            message = self._i18n_manager.t("progress.round_success", round_num=round_num)
            print(message)

    def show_round_retry(self, round_num: int):
        if self._show_progress and self._i18n_manager:
            message = self._i18n_manager.t("progress.round_retry", round_num=round_num)
            print(message)

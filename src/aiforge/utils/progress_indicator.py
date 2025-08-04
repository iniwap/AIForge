class ProgressIndicator:
    _show_progress = True

    @classmethod
    def set_show_progress(cls, show: bool):
        cls._show_progress = show

    @staticmethod
    def show_llm_request(provider: str = ""):
        if ProgressIndicator._show_progress:
            print(f"🤖 [AIForge]正在连接AI服务{f'({provider})' if provider else ''}...")

    @staticmethod
    def show_llm_generating():
        if ProgressIndicator._show_progress:
            print("💭 [AIForge]正在等待AI回复...")

    @staticmethod
    def show_llm_complete():
        if ProgressIndicator._show_progress:
            print("✅ [AIForge]收到AI回复，正在处理...")

    @staticmethod
    def show_search_start(query: str):
        if ProgressIndicator._show_progress:
            print(f"🔍 [AIForge]正在搜索: {query[:50]}{'...' if len(query) > 50 else ''}")

    @staticmethod
    def show_search_process(search_type):
        if ProgressIndicator._show_progress:
            print(f"🔍 [AIForge]正在尝试{search_type}搜索...")

    @staticmethod
    def show_search_complete(count: int):
        if ProgressIndicator._show_progress:
            print(f"✅ [AIForge]搜索完成，找到 {count} 条结果")

    @staticmethod
    def show_cache_lookup():
        if ProgressIndicator._show_progress:
            print("🔍 [AIForge]正在查找缓存...")

    @staticmethod
    def show_cache_found(count: int):
        if ProgressIndicator._show_progress:
            print(f"📦 [AIForge]找到 {count} 个缓存模块，正在验证...")

    @staticmethod
    def show_cache_execution():
        if ProgressIndicator._show_progress:
            print("⚡ [AIForge]正在执行缓存代码...")

    @staticmethod
    def show_code_execution(count: int = 1):
        if ProgressIndicator._show_progress:
            print(f"⚡ [AIForge]正在执行 {count} 个代码块...")

    @staticmethod
    def show_round_start(current: int, total: int):
        if ProgressIndicator._show_progress:
            print(f"🔄 [AIForge]开始第 {current}/{total} 轮执行...")

    @staticmethod
    def show_round_success(round_num: int):
        if ProgressIndicator._show_progress:
            print(f"🎉 [AIForge]第 {round_num} 轮执行成功！")

    @staticmethod
    def show_round_retry(round_num: int):
        if ProgressIndicator._show_progress:
            print(f"⚠️[AIForge] 第 {round_num} 轮失败，准备重试...")

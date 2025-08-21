import threading
from typing import Set, Callable


class AIForgeShutdownManager:
    """全局关闭管理器 - 单例模式"""

    _instance = None
    _lock = threading.RLock()
    _initialized = False

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        # 防止重复初始化
        if self._initialized:
            return

        with self._lock:
            if not self._initialized:
                self._shutdown_event = threading.Event()
                self._cleanup_callbacks: Set[Callable] = set()
                self._callback_lock = threading.Lock()
                AIForgeShutdownManager._initialized = True

    @classmethod
    def get_instance(cls):
        """获取单例实例"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def register_cleanup_callback(self, callback: Callable):
        """注册清理回调"""
        with self._callback_lock:
            self._cleanup_callbacks.add(callback)

    def unregister_cleanup_callback(self, callback: Callable):
        """取消注册清理回调"""
        with self._callback_lock:
            self._cleanup_callbacks.discard(callback)

    def is_shutting_down(self) -> bool:
        """检查是否正在关闭"""
        return self._shutdown_event.is_set()

    def initiate_shutdown(self):
        """启动关闭流程"""
        self._shutdown_event.set()

        # 执行所有清理回调
        with self._callback_lock:
            for callback in self._cleanup_callbacks:
                try:
                    callback()
                except Exception as e:
                    print(f"清理回调执行失败: {e}")

    def reset(self):
        """重置关闭状态（主要用于测试）"""
        with self._lock:
            self._shutdown_event.clear()
            with self._callback_lock:
                self._cleanup_callbacks.clear()

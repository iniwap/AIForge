import threading
from typing import Set, Callable


class AIForgeShutdownManager:
    """关闭管理器 - 非单例模式"""

    def __init__(self):
        """初始化关闭管理器实例"""
        self._shutdown_event = threading.Event()
        self._cleanup_callbacks: Set[Callable] = set()
        self._callback_lock = threading.Lock()

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

    def shutdown(self):
        """统一的关闭方法"""
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
        self._shutdown_event.clear()
        with self._callback_lock:
            self._cleanup_callbacks.clear()

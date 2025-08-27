import threading
import time
from typing import Dict, Optional
from concurrent.futures import ThreadPoolExecutor
from .session_context import SessionContext


class SessionManager:
    """线程安全的多用户会话管理器"""

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
        if self._initialized:
            return

        with self._lock:
            if not self._initialized:
                # 使用细粒度锁替代单一锁
                self._sessions: Dict[str, SessionContext] = {}
                self._session_locks: Dict[str, threading.RLock] = {}
                self._global_lock = threading.RLock()
                self._session_timeout = 7200
                self._max_sessions = 1000

                # 添加线程池用于异步清理
                self._cleanup_executor = ThreadPoolExecutor(
                    max_workers=2, thread_name_prefix="session-cleanup"
                )
                SessionManager._initialized = True

    @classmethod
    def get_instance(cls):
        """获取单例实例"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _get_session_lock(self, session_id: str) -> threading.RLock:
        """获取会话专用锁"""
        with self._global_lock:
            if session_id not in self._session_locks:
                self._session_locks[session_id] = threading.RLock()
            return self._session_locks[session_id]

    def create_session(
        self, session_id: str, user_id: Optional[str] = None, language: str = "zh", **metadata
    ) -> SessionContext:
        """线程安全的会话创建"""
        session_lock = self._get_session_lock(session_id)

        with session_lock:
            # 双重检查锁定模式
            if session_id in self._sessions:
                existing_session = self._sessions[session_id]
                existing_session.update_activity()
                return existing_session

            # 原子性检查会话数量限制
            with self._global_lock:
                if len(self._sessions) >= self._max_sessions:
                    # 异步清理过期会话
                    self._cleanup_executor.submit(self._cleanup_expired_sessions_async)
                    if len(self._sessions) >= self._max_sessions:
                        raise RuntimeError(f"会话数量超过限制: {self._max_sessions}")

                # 原子性创建会话
                context = SessionContext(
                    session_id=session_id, user_id=user_id, language=language, metadata=metadata
                )
                self._sessions[session_id] = context

        return context

    def get_session(self, session_id: str) -> Optional[SessionContext]:
        """线程安全的会话获取"""
        session_lock = self._get_session_lock(session_id)

        with session_lock:
            context = self._sessions.get(session_id)
            if context and not context.is_expired(self._session_timeout):
                context.update_activity()
                return context
            elif context:
                # 异步清理过期会话
                self._cleanup_executor.submit(self._cleanup_session_async, session_id)
            return None

    def _cleanup_session_async(self, session_id: str):
        """异步会话清理"""
        session_lock = self._get_session_lock(session_id)

        with session_lock:
            if session_id not in self._sessions:
                return False

            context = self._sessions[session_id]

            # 并行清理组件
            cleanup_futures = []
            for component_name, component in context.components.items():
                if hasattr(component, "shutdown"):
                    future = self._cleanup_executor.submit(
                        self._safe_shutdown, component, component_name
                    )
                    cleanup_futures.append(future)

            # 等待所有清理完成
            for future in cleanup_futures:
                try:
                    future.result(timeout=5)  # 5秒超时
                except Exception as e:
                    print(f"组件清理超时或失败: {e}")

            # 原子性移除会话
            with self._global_lock:
                self._sessions.pop(session_id, None)
                self._session_locks.pop(session_id, None)

    def _safe_shutdown(self, component, component_name: str):
        """安全的组件关闭"""
        try:
            component.shutdown()
        except Exception as e:
            print(f"关闭组件 {component_name} 失败: {e}")

    def _cleanup_expired_sessions_async(self):
        """异步清理过期会话"""
        current_time = time.time()
        expired_sessions = []

        # 快速识别过期会话
        with self._global_lock:
            for session_id, context in list(self._sessions.items()):
                if current_time - context.last_activity > self._session_timeout:
                    expired_sessions.append(session_id)

        # 并行清理过期会话
        for session_id in expired_sessions:
            self._cleanup_executor.submit(self._cleanup_session_async, session_id)

    def shutdown_all_sessions(self):
        """优雅关闭所有会话"""
        with self._global_lock:
            session_ids = list(self._sessions.keys())

        # 并行关闭所有会话
        shutdown_futures = []
        for session_id in session_ids:
            future = self._cleanup_executor.submit(self._cleanup_session_async, session_id)
            shutdown_futures.append(future)

        # 等待所有关闭完成
        for future in shutdown_futures:
            try:
                future.result(timeout=10)
            except Exception as e:
                print(f"会话关闭失败: {e}")

        # 关闭线程池
        self._cleanup_executor.shutdown(wait=True)

    def get_active_sessions_count(self) -> int:
        """获取活跃会话数量"""
        with self._global_lock:
            return len(self._sessions)

    def cleanup_expired_sessions(self) -> int:
        """清理所有过期会话，返回清理的会话数量"""
        current_time = time.time()
        expired_sessions = []

        # 快速识别过期会话
        with self._global_lock:
            for session_id, context in list(self._sessions.items()):
                if current_time - context.last_activity > self._session_timeout:
                    expired_sessions.append(session_id)

        # 并行清理过期会话
        cleaned_count = 0
        for session_id in expired_sessions:
            future = self._cleanup_executor.submit(self._cleanup_session_async, session_id)
            try:
                if future.result(timeout=5):  # 等待清理完成
                    cleaned_count += 1
            except Exception as e:
                print(f"清理会话 {session_id} 失败: {e}")

        return cleaned_count

    def cleanup_session(self, session_id: str) -> bool:
        """清理指定会话"""
        session_lock = self._get_session_lock(session_id)

        with session_lock:
            if session_id not in self._sessions:
                return False

            context = self._sessions[session_id]

            # 并行清理组件
            cleanup_futures = []
            for component_name, component in context.components.items():
                if hasattr(component, "shutdown"):
                    future = self._cleanup_executor.submit(
                        self._safe_shutdown, component, component_name
                    )
                    cleanup_futures.append(future)

            # 等待所有清理完成
            for future in cleanup_futures:
                try:
                    future.result(timeout=5)  # 5秒超时
                except Exception as e:
                    print(f"组件清理超时或失败: {e}")

            # 原子性移除会话
            with self._global_lock:
                self._sessions.pop(session_id, None)
                self._session_locks.pop(session_id, None)

            return True

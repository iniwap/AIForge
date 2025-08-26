import threading
import time
from typing import Dict, Optional, List
from .session_context import SessionContext


class SessionManager:
    """多用户会话管理器"""

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
                self._sessions: Dict[str, SessionContext] = {}
                self._session_lock = threading.RLock()
                self._session_timeout = 7200
                self._max_sessions = 1000
                SessionManager._initialized = True

    @classmethod
    def get_instance(cls):
        """获取单例实例"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def create_session(
        self, session_id: str, user_id: Optional[str] = None, language: str = "zh", **metadata
    ) -> SessionContext:
        """创建新会话上下文"""
        with self._session_lock:
            # 检查会话是否已存在
            if session_id in self._sessions:
                existing_session = self._sessions[session_id]
                existing_session.update_activity()
                return existing_session

            # 检查会话数量限制
            if len(self._sessions) >= self._max_sessions:
                self._cleanup_expired_sessions()
                if len(self._sessions) >= self._max_sessions:
                    raise RuntimeError(f"会话数量超过限制: {self._max_sessions}")

            # 创建新的会话上下文
            context = SessionContext(
                session_id=session_id, user_id=user_id, language=language, metadata=metadata
            )

            self._sessions[session_id] = context
            return context

    def get_session(self, session_id: str) -> Optional[SessionContext]:
        """获取会话上下文"""
        with self._session_lock:
            context = self._sessions.get(session_id)
            if context and not context.is_expired(self._session_timeout):
                context.update_activity()
                return context
            elif context:
                # 会话已过期，清理
                self._cleanup_session_internal(session_id)
            return None

    def update_session_activity(self, session_id: str) -> bool:
        """更新会话活动时间"""
        with self._session_lock:
            context = self._sessions.get(session_id)
            if context:
                context.update_activity()
                return True
            return False

    def cleanup_session(self, session_id: str) -> bool:
        """清理指定会话"""
        with self._session_lock:
            return self._cleanup_session_internal(session_id)

    def _cleanup_session_internal(self, session_id: str) -> bool:
        """内部会话清理方法（需要在锁内调用）"""
        if session_id not in self._sessions:
            return False

        context = self._sessions[session_id]

        # 清理会话组件
        for component_name, component in context.components.items():
            if hasattr(component, "cleanup"):
                try:
                    component.cleanup()
                except Exception as e:
                    print(f"清理组件 {component_name} 失败: {e}")
            elif hasattr(component, "shutdown"):
                try:
                    component.shutdown()
                except Exception as e:
                    print(f"关闭组件 {component_name} 失败: {e}")

        # 从会话字典中移除
        del self._sessions[session_id]
        return True

    def cleanup_expired_sessions(self) -> int:
        """清理所有过期会话，返回清理的会话数量"""
        expired_sessions = []

        with self._session_lock:
            for session_id, context in self._sessions.items():
                if context.is_expired(self._session_timeout):
                    expired_sessions.append(session_id)

        # 清理过期会话
        cleaned_count = 0
        for session_id in expired_sessions:
            if self.cleanup_session(session_id):
                cleaned_count += 1

        return cleaned_count

    def get_active_sessions_count(self) -> int:
        """获取活跃会话数量"""
        with self._session_lock:
            return len(self._sessions)

    def get_session_info(self, session_id: str) -> Optional[Dict]:
        """获取会话信息"""
        with self._session_lock:
            context = self._sessions.get(session_id)
            if context:
                return {
                    "session_id": context.session_id,
                    "user_id": context.user_id,
                    "created_at": context.created_at,
                    "last_activity": context.last_activity,
                    "language": context.language,
                    "components_count": len(context.components),
                    "is_expired": context.is_expired(self._session_timeout),
                    "metadata": context.metadata,
                }
            return None

    def list_active_sessions(self) -> List[Dict]:
        """列出所有活跃会话信息"""
        sessions = []
        with self._session_lock:
            for session_id in list(self._sessions.keys()):
                session_info = self.get_session_info(session_id)
                if session_info and not session_info["is_expired"]:
                    sessions.append(session_info)
        return sessions

    def shutdown_all_sessions(self):
        """关闭所有会话"""
        with self._session_lock:
            session_ids = list(self._sessions.keys())
            for session_id in session_ids:
                self._cleanup_session_internal(session_id)

    def _cleanup_expired_sessions(self):
        """内部清理过期会话方法（需要在锁内调用）"""
        current_time = time.time()
        expired_sessions = []

        for session_id, context in self._sessions.items():
            if current_time - context.last_activity > self._session_timeout:
                expired_sessions.append(session_id)

        for session_id in expired_sessions:
            self._cleanup_session_internal(session_id)

        return len(expired_sessions)

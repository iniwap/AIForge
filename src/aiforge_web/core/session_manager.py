import threading
import time
from typing import Dict, Optional, List
from aiforge import AIForgeEngine
from aiforge.core.managers.shutdown_manager import AIForgeShutdownManager


class UserSessionManager:
    """用户会话管理器 - 单例模式"""

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
                self._sessions: Dict[str, AIForgeEngine] = {}
                self._session_lock = threading.RLock()
                self._session_timestamps: Dict[str, float] = {}
                self._session_shutdown_managers: Dict[str, AIForgeShutdownManager] = {}
                self._cleanup_interval = 3600  # 1小时清理一次
                self._session_timeout = 7200  # 2小时会话超时
                UserSessionManager._initialized = True

    @classmethod
    def get_instance(cls):
        """获取单例实例"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def get_or_create_engine(self, session_id: str, **engine_kwargs) -> AIForgeEngine:
        """获取或创建用户专属的 AIForge 引擎实例"""
        with self._session_lock:
            # 更新会话时间戳
            self._session_timestamps[session_id] = time.time()

            if session_id not in self._sessions:
                # 为每个会话创建独立的 AIForgeShutdownManager
                session_shutdown = AIForgeShutdownManager()
                self._session_shutdown_managers[session_id] = session_shutdown

                # 创建引擎实例
                engine = AIForgeEngine(**engine_kwargs)

                # 将 AIForgeShutdownManager 注入到引擎的组件中
                if hasattr(engine, "component_manager") and hasattr(
                    engine.component_manager, "components"
                ):
                    engine.component_manager.components["shutdown_manager"] = session_shutdown

                self._sessions[session_id] = engine

            return self._sessions[session_id]

    def get_session_shutdown_manager(self, session_id: str) -> Optional[AIForgeShutdownManager]:
        """获取会话的 AIForgeShutdownManager"""
        return self._session_shutdown_managers.get(session_id)

    def initiate_session_shutdown(self, session_id: str):
        """启动指定会话的关闭流程"""
        shutdown_manager = self.get_session_shutdown_manager(session_id)
        if shutdown_manager:
            shutdown_manager.initiate_shutdown()

    def cleanup_session(self, session_id: str):
        """清理指定会话"""
        with self._session_lock:
            if session_id in self._sessions:
                # 先触发关闭信号
                self.initiate_session_shutdown(session_id)

                # 清理引擎资源
                engine = self._sessions[session_id]
                if hasattr(engine, "cleanup"):
                    engine.cleanup()

                # 清理会话数据
                del self._sessions[session_id]
                self._session_timestamps.pop(session_id, None)
                self._session_shutdown_managers.pop(session_id, None)

    def cleanup_expired_sessions(self):
        """清理过期会话"""
        current_time = time.time()
        expired_sessions = []

        with self._session_lock:
            for session_id, timestamp in self._session_timestamps.items():
                if current_time - timestamp > self._session_timeout:
                    expired_sessions.append(session_id)

        for session_id in expired_sessions:
            self.cleanup_session(session_id)

    def get_active_sessions_count(self) -> int:
        """获取活跃会话数量"""
        with self._session_lock:
            return len(self._sessions)

    def get_session_info(self, session_id: str) -> Optional[Dict]:
        """获取会话信息"""
        with self._session_lock:
            if session_id in self._sessions:
                return {
                    "session_id": session_id,
                    "created_at": self._session_timestamps.get(session_id),
                    "last_activity": self._session_timestamps.get(session_id),
                    "has_shutdown_manager": session_id in self._session_shutdown_managers,
                    "is_shutting_down": (
                        self._session_shutdown_managers.get(session_id, {}).is_shutting_down()
                        if session_id in self._session_shutdown_managers
                        else False
                    ),
                }
        return None

    def list_active_sessions(self) -> List[Dict]:
        """列出所有活跃会话"""
        sessions = []
        with self._session_lock:
            for session_id in self._sessions.keys():
                session_info = self.get_session_info(session_id)
                if session_info:
                    sessions.append(session_info)
        return sessions

    def reset(self):
        """重置所有会话（主要用于测试）"""
        with self._session_lock:
            # 清理所有会话
            for session_id in list(self._sessions.keys()):
                self.cleanup_session(session_id)

            # 清空所有字典
            self._sessions.clear()
            self._session_timestamps.clear()
            self._session_shutdown_managers.clear()

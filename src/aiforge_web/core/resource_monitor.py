import threading
import time
import psutil
import gc
from typing import Dict, Any, Callable
from .session_manager import SessionManager


class ResourceMonitor:
    """资源监控和主动清理管理器"""

    def __init__(self, session_manager: SessionManager):
        self.session_manager = session_manager
        self.monitoring = False
        self.monitor_thread = None
        self.cleanup_callbacks: Dict[str, Callable] = {}

        # 资源阈值配置
        self.memory_threshold = 0.8  # 80%内存使用率
        self.session_threshold = 0.9  # 90%会话数量
        self.cleanup_interval = 300  # 5分钟检查间隔

    def start_monitoring(self):
        """启动资源监控"""
        if self.monitoring:
            return

        self.monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()

    def stop_monitoring(self):
        """停止资源监控"""
        self.monitoring = False
        if self.monitor_thread and self.monitor_thread.is_alive():
            try:
                self.monitor_thread.join(timeout=2)  # 减少超时时间
            except KeyboardInterrupt:
                # 在键盘中断时直接返回，不等待线程
                return

    def register_cleanup_callback(self, name: str, callback: Callable):
        """注册清理回调"""
        self.cleanup_callbacks[name] = callback

    def _monitor_loop(self):
        """监控循环"""
        while self.monitoring:
            try:
                self._check_resources()
                time.sleep(self.cleanup_interval)
            except Exception as e:
                print(f"资源监控错误: {e}")
                time.sleep(60)  # 错误后等待1分钟

    def _check_resources(self):
        """检查资源使用情况"""
        # 检查内存使用率
        memory_percent = psutil.virtual_memory().percent / 100
        if memory_percent > self.memory_threshold:
            print(f"内存使用率过高: {memory_percent:.1%}, 触发清理")
            self._trigger_aggressive_cleanup()

        # 检查会话数量
        active_sessions = self.session_manager.get_active_sessions_count()
        max_sessions = self.session_manager._max_sessions
        session_ratio = active_sessions / max_sessions

        if session_ratio > self.session_threshold:
            print(f"会话数量过多: {active_sessions}/{max_sessions}, 触发清理")
            self._trigger_session_cleanup()

        # 执行注册的清理回调
        for name, callback in self.cleanup_callbacks.items():
            try:
                callback()
            except Exception as e:
                print(f"清理回调 {name} 执行失败: {e}")

    def _trigger_aggressive_cleanup(self):
        """触发激进清理"""
        # 清理过期会话
        cleaned = self.session_manager.cleanup_expired_sessions()
        print(f"清理了 {cleaned} 个过期会话")

        # 强制垃圾回收
        gc.collect()

        # 清理长时间未活动的会话（降低阈值）
        self._cleanup_inactive_sessions(threshold_hours=1)

    def _trigger_session_cleanup(self):
        """触发会话清理"""
        cleaned = self.session_manager.cleanup_expired_sessions()
        print(f"清理了 {cleaned} 个过期会话")

        if cleaned < 10:  # 如果清理的会话太少，降低阈值
            self._cleanup_inactive_sessions(threshold_hours=2)

    def _cleanup_inactive_sessions(self, threshold_hours: float = 4):
        """清理长时间未活动的会话"""
        current_time = time.time()
        inactive_threshold = threshold_hours * 3600  # 转换为秒
        inactive_sessions = []

        # 识别非活跃会话
        with self.session_manager._global_lock:
            for session_id, context in list(self.session_manager._sessions.items()):
                if current_time - context.last_activity > inactive_threshold:
                    inactive_sessions.append(session_id)

        # 清理非活跃会话
        cleaned_count = 0
        for session_id in inactive_sessions:
            if self.session_manager.cleanup_session(session_id):
                cleaned_count += 1

        print(f"清理了 {cleaned_count} 个非活跃会话 (阈值: {threshold_hours}小时)")
        return cleaned_count

    def get_resource_stats(self) -> Dict[str, Any]:
        """获取资源统计信息"""
        try:
            memory = psutil.virtual_memory()
            return {
                "memory_percent": memory.percent,
                "memory_available_gb": memory.available / (1024**3),
                "active_sessions": self.session_manager.get_active_sessions_count(),
                "max_sessions": self.session_manager._max_sessions,
                "session_ratio": self.session_manager.get_active_sessions_count()
                / self.session_manager._max_sessions,
                "monitoring_active": self.monitoring,
                "timestamp": time.time(),
            }
        except Exception as e:
            return {"error": str(e), "timestamp": time.time()}

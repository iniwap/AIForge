import re
import json
from datetime import datetime
from typing import List, Dict, Any


class ConversationManager:
    """智能对话历史管理器"""

    def __init__(self, max_history: int = 8):
        self.max_history = max_history
        self.conversation_history: List[Dict[str, str]] = []
        self.error_patterns: List[str] = []

    def _manage_history(self):
        """智能历史管理"""
        if len(self.conversation_history) <= self.max_history:
            return

        # 优先保留：
        # 1. 最新的消息
        # 2. 包含错误信息的消息
        # 3. 成功执行的消息

        important_messages = []
        recent_messages = self.conversation_history[-4:]  # 保留最近4条

        for msg in self.conversation_history[:-4]:
            metadata = msg.get("metadata", {})
            if (
                metadata.get("is_error_feedback")
                or metadata.get("is_success")
                or "error" in msg["content"].lower()
            ):
                important_messages.append(msg)

        # 限制重要消息数量
        if len(important_messages) > self.max_history - 4:
            important_messages = important_messages[-(self.max_history - 4) :]  # noqa 203

        self.conversation_history = important_messages + recent_messages

    def get_context_messages(self) -> List[Dict[str, str]]:
        """获取过滤后的上下文消息，避免重复反馈"""
        context_messages = []

        # 只保留最近的关键信息，避免累积历史错误
        recent_messages = self.conversation_history[-2:]  # 只保留最近2条

        for message in recent_messages:
            if message.get("metadata", {}).get("is_error_feedback"):
                # 过滤错误反馈，只保留核心信息
                filtered_content = self._filter_error_feedback(message["content"])
                if filtered_content:
                    context_messages.append({"role": message["role"], "content": filtered_content})
            elif message["role"] == "user" and len(message["content"]) < 50:
                # 只保留非常简短的用户消息
                context_messages.append(message)

        # 避免重复的错误模式总结
        if self.error_patterns:
            # 只使用最新的错误模式，不累积
            latest_pattern = self.error_patterns[-1] if self.error_patterns else None
            if latest_pattern and not any(
                latest_pattern in msg.get("content", "") for msg in context_messages
            ):
                pattern_msg = {
                    "role": "system",
                    "content": f"避免错误: {latest_pattern}",
                }
                context_messages.insert(0, pattern_msg)

        return context_messages

    def add_message(self, role: str, content: str, metadata: Dict[str, Any] = None):
        """添加消息到历史记录，优化错误模式提取"""
        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata or {},
        }
        self.conversation_history.append(message)

        # 如果是错误反馈，提取错误模式（但不重复提取）
        if role == "user" and metadata and metadata.get("is_error_feedback"):
            self._extract_error_patterns(content)

        # 智能历史管理
        self._manage_history()

    def _extract_error_patterns(self, error_content: str):
        """提取错误模式，避免重复"""
        patterns = [
            r"(NameError|TypeError|ValueError|AttributeError|ImportError|SyntaxError)",
            r"'([^']+)' is not defined",
            r"module '([^']+)' has no attribute",
        ]

        new_patterns = []
        for pattern in patterns:
            matches = re.findall(pattern, error_content)
            if matches:
                new_patterns.extend([str(m) for m in matches])

        # 只保留新的错误模式，避免重复累积
        for pattern in new_patterns:
            if pattern not in self.error_patterns[-3:]:  # 只检查最近3个
                self.error_patterns.append(pattern)

        # 限制错误模式数量
        if len(self.error_patterns) > 5:
            self.error_patterns = self.error_patterns[-5:]

    def _filter_error_feedback(self, content: str) -> str:
        """过滤错误反馈，只保留核心信息"""
        try:
            feedback = json.loads(content)
            # 只保留最关键的信息
            core_info = {
                "type": feedback.get("error_type", "unknown"),
                "hint": feedback.get("suggestion", "")[:30],  # 极简建议
            }
            return json.dumps(core_info, ensure_ascii=False)
        except Exception:
            return ""  # 解析失败直接忽略

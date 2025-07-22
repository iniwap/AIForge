import re
from datetime import datetime
from typing import List, Dict, Any


class ConversationManager:
    """智能对话历史管理器"""

    def __init__(self, max_history: int = 8):
        self.max_history = max_history
        self.conversation_history: List[Dict[str, str]] = []
        self.error_patterns: List[str] = []

    def add_message(self, role: str, content: str, metadata: Dict[str, Any] = None):
        """添加消息到历史记录"""
        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata or {},
        }
        self.conversation_history.append(message)

        # 如果是错误反馈，提取错误模式
        if role == "user" and metadata and metadata.get("is_error_feedback"):
            self._extract_error_patterns(content)

        # 智能历史管理
        self._manage_history()

    def _extract_error_patterns(self, error_content: str):
        """提取错误模式"""
        patterns = [
            r"(NameError|TypeError|ValueError|AttributeError|ImportError|SyntaxError)",
            r"line (\d+)",
            r"'([^']+)' is not defined",
            r"module '([^']+)' has no attribute",
        ]

        for pattern in patterns:
            matches = re.findall(pattern, error_content)
            if matches:
                self.error_patterns.extend([str(m) for m in matches])

    def _manage_history(self):
        """智能历史管理 - 保留关键信息"""
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
        """获取用于 LLM 的上下文消息"""
        # 添加错误模式总结
        if self.error_patterns:
            pattern_summary = f"历史错误模式: {', '.join(set(self.error_patterns[-5:]))}"
            context_msg = {"role": "system", "content": f"注意避免以下常见错误: {pattern_summary}"}
            return [context_msg] + [
                {"role": msg["role"], "content": msg["content"]}
                for msg in self.conversation_history
            ]

        return [
            {"role": msg["role"], "content": msg["content"]} for msg in self.conversation_history
        ]

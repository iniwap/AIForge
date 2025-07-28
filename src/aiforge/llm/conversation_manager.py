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
            content = msg.get("content", "")
            if (
                metadata.get("is_error_feedback")
                or metadata.get("is_success")
                or (content and "error" in content.lower())
            ):
                important_messages.append(msg)

        # 限制重要消息数量
        if len(important_messages) > self.max_history - 4:
            important_messages = important_messages[-(self.max_history - 4) :]  # noqa 203

        self.conversation_history = important_messages + recent_messages

    def get_context_messages(self, context_type: str = "generation") -> List[Dict[str, str]]:
        """根据上下文类型获取相关消息"""
        if context_type == "generation":
            # 代码生成时，只保留最近的错误反馈，过滤掉完整代码响应
            filtered_messages = []
            for msg in self.conversation_history[-3:]:  # 只看最近3条消息
                if msg["role"] == "user":
                    # 只保留反馈消息
                    if msg.get("metadata", {}).get("is_error_feedback"):
                        # 限制反馈消息长度，避免包含大量代码
                        content = msg["content"]
                        if len(content) > 300:
                            content = content[:300] + "..."
                        filtered_messages.append({"role": msg["role"], "content": content})
                # 不包含 AI 的代码响应，避免源码循环
            return filtered_messages
        else:
            # 其他类型保持原有逻辑
            return self.conversation_history[-2:]

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

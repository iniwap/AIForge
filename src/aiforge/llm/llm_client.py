import requests
import time
from rich.console import Console
from typing import Dict, Any
from .conversation_manager import ConversationManager
from ..utils.progress_indicator import ProgressIndicator


class AIForgeLLMClient:
    """AIForge LLM 客户端"""

    def __init__(
        self,
        name: str,
        api_key: str,
        base_url: str | None = None,
        model: str = "gpt-3.5-turbo",
        timeout: int = 30,
        max_tokens: int = 8192,
        client_type: str = "openai",
    ):
        self.name = name
        self.api_key = api_key
        self.base_url = base_url or "https://api.openai.com/v1"
        self.model = model
        self.timeout = timeout
        self.max_tokens = max_tokens
        self.console = Console()
        self.client_type = client_type

        # 使用智能对话管理器
        self.conversation_manager = ConversationManager()
        self.usage_stats = {"total_tokens": 0, "rounds": 0}

    def is_usable(self) -> bool:
        """检查客户端是否可用"""
        if hasattr(self, "client_type") and self.client_type == "ollama":
            return bool(self.model and self.base_url)
        return bool(self.api_key and self.model)

    def generate_code(
        self,
        instruction: str,
        system_prompt: str | None = None,
        use_history: bool = True,
        max_retries: int = 2,
        context_type: str = "generation",
    ) -> str | None:
        """生成代码的核心方法"""

        # 添加进度指示器

        ProgressIndicator.show_llm_request(self.name)

        for attempt in range(max_retries):
            try:
                if attempt == 0:
                    ProgressIndicator.show_llm_generating()

                headers = {
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                }

                messages = []

                # 添加系统提示
                if system_prompt:
                    messages.append({"role": "system", "content": system_prompt})

                # 根据参数决定是否使用历史
                if use_history:
                    context_messages = self.conversation_manager.get_context_messages()
                    messages.extend(context_messages)

                # 添加当前指令
                if instruction:
                    messages.append({"role": "user", "content": instruction})

                payload = {
                    "model": self.model,
                    "messages": messages,
                    "temperature": 0.7,
                    "max_tokens": self.max_tokens,
                }

                response = requests.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=self.timeout,
                )

                if response.status_code == 200:
                    ProgressIndicator.show_llm_complete()
                    result = response.json()
                    assistant_response = result["choices"][0]["message"]["content"]

                    # 记录到对话历史
                    if use_history:
                        self.conversation_manager.add_message("user", instruction)
                        self.conversation_manager.add_message("assistant", assistant_response)

                    # 更新使用统计
                    if "usage" in result:
                        usage = result["usage"]
                        self.usage_stats["total_tokens"] += usage.get("total_tokens", 0)
                    self.usage_stats["rounds"] += 1

                    return assistant_response
                else:
                    # 只对网络错误进行重试
                    if response.status_code >= 500:  # 服务器错误才重试
                        wait_time = (2**attempt) * 1
                        self.console.print(
                            f"[yellow]{self.name} 服务器错误: {response.status_code}, 第 {attempt + 1} 次重试，等待 {wait_time} 秒...[/yellow]"  # noqa 501
                        )
                        time.sleep(wait_time)
                        continue
                    else:
                        # 客户端错误不重试
                        self.console.print(
                            f"[red]{self.name} 客户端错误: {response.status_code}[/red]"
                        )
                        return None

            except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
                # 只对网络异常重试
                self.console.print(
                    f"[yellow]{self.name} 网络异常: {e}, 第 {attempt + 1} 次重试[/yellow]"
                )
                if attempt < max_retries - 1:
                    time.sleep(1)
                    continue
                else:
                    return None
            except Exception as e:
                # 其他异常不重试
                self.console.print(f"[red]{self.name} 请求失败: {e}[/red]")
                return None

        return None

    def send_feedback(self, feedback: str, is_error: bool = True, metadata: Dict[str, Any] = None):
        """发送反馈信息，使用特殊的历史管理"""
        if not feedback:
            return

        if not metadata:
            metadata = {}

        metadata["is_error_feedback"] = is_error
        metadata["message_type"] = "feedback"

        # 反馈消息不参与常规的代码生成上下文
        self.conversation_manager.add_message("user", feedback, metadata)

    def get_usage_stats(self):
        """获取使用统计"""
        return self.usage_stats.copy()

    def reset_conversation(self):
        """重置对话历史"""
        self.conversation_manager = ConversationManager()

    def get_conversation_summary(self) -> Dict[str, Any]:
        """获取对话摘要"""
        return {
            "message_count": len(self.conversation_manager.conversation_history),
            "error_patterns": list(set(self.conversation_manager.error_patterns)),
            "recent_messages": self.conversation_manager.conversation_history[-3:],
        }


class AIForgeOllamaClient(AIForgeLLMClient):
    """Ollama客户端实现"""

    def __init__(
        self, name: str, base_url: str, model: str, timeout: int = 30, max_tokens: int = 8192
    ):
        super().__init__(name, "", base_url, model, timeout, max_tokens)

    def is_usable(self) -> bool:
        """Ollama不需要API key"""
        return bool(self.model and self.base_url)

    def generate_code(
        self,
        instruction: str,
        system_prompt: str | None = None,
        use_history: bool = True,
        max_retries: int = 2,
    ) -> str | None:
        """Ollama特定的实现"""
        for attempt in range(max_retries):
            try:
                messages = []

                if system_prompt:
                    messages.append({"role": "system", "content": system_prompt})

                if use_history:
                    context_messages = self.conversation_manager.get_context_messages()
                    messages.extend(context_messages)

                messages.append({"role": "user", "content": instruction})

                payload = {"model": self.model, "messages": messages, "stream": False}

                response = requests.post(
                    f"{self.base_url}/api/chat", json=payload, timeout=self.timeout
                )

                if response.status_code == 200:
                    result = response.json()
                    assistant_response = result["message"]["content"]

                    if use_history:
                        self.conversation_manager.add_message("user", instruction)
                        self.conversation_manager.add_message("assistant", assistant_response)

                    return assistant_response
                else:
                    if response.status_code >= 500:
                        wait_time = (2**attempt) * 1
                        self.console.print(
                            f"[yellow]{self.name} 服务器错误: {response.status_code}, 第 {attempt + 1} 次重试，等待 {wait_time} 秒...[/yellow]"  # noqa 501
                        )
                        time.sleep(wait_time)
                        continue
                    else:
                        self.console.print(
                            f"[red]{self.name} 客户端错误: {response.status_code}[/red]"
                        )
                        return None

            except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
                self.console.print(
                    f"[yellow]{self.name} 网络异常: {e}, 第 {attempt + 1} 次重试[/yellow]"
                )
                if attempt < max_retries - 1:
                    time.sleep(1)
                    continue
                else:
                    return None
            except Exception as e:
                self.console.print(f"[red]{self.name} 请求失败: {e}[/red]")
                return None
        return None
